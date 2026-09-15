from __future__ import annotations

from io import BytesIO
import re

import pandas as pd

from topics import TRAP_TERMS


def normalize_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise harmless whitespace/case differences while preserving all original data.
    Only the three policy input columns are renamed when a clear case-insensitive match exists.
    """
    expected = ["Mechanism", "Analytical Summary", "Title"]
    mapping = {}
    lookup = {str(c).strip().lower(): c for c in df.columns}

    for target in expected:
        source = lookup.get(target.lower())
        if source is not None and source != target:
            mapping[source] = target

    return df.rename(columns=mapping)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Classified Bills")

        review = df[
            (df["Topic Confidence"].isin([50, 70]))
            | (df["Classification Error"].astype(str).str.len() > 0)
            | (df["Classification Warning"].astype(str).str.len() > 0)
        ].copy()
        review.to_excel(writer, index=False, sheet_name="Human Review")

        workbook = writer.book
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "font_color": "white",
                "bg_color": "#123B6D",
                "align": "center",
                "valign": "vcenter",
                "border": 0,
            }
        )
        wrap_fmt = workbook.add_format({"text_wrap": True, "valign": "top"})
        center_fmt = workbook.add_format({"align": "center", "valign": "top"})

        for sheet_name, sheet_df in [("Classified Bills", df), ("Human Review", review)]:
            ws = writer.sheets[sheet_name]
            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, max(len(sheet_df), 1), max(len(sheet_df.columns) - 1, 0))
            ws.set_row(0, 26)

            for col_idx, col_name in enumerate(sheet_df.columns):
                ws.write(0, col_idx, col_name, header_fmt)

                if col_name in {
                    "Title",
                    "Mechanism",
                    "Analytical Summary",
                    "Provision",
                    "Model Raw Output",
                    "Classification Error",
                    "Classification Warning",
                }:
                    width = 46 if col_name != "Model Raw Output" else 34
                    ws.set_column(col_idx, col_idx, width, wrap_fmt)
                elif col_name in {"Topic", "Topic Runner-Up"}:
                    ws.set_column(col_idx, col_idx, 40, wrap_fmt)
                elif col_name == "Topic Confidence":
                    ws.set_column(col_idx, col_idx, 18, center_fmt)
                else:
                    ws.set_column(col_idx, col_idx, 18)

            if "Topic Confidence" in sheet_df.columns and len(sheet_df):
                conf_col = sheet_df.columns.get_loc("Topic Confidence")
                ws.conditional_format(
                    1, conf_col, len(sheet_df), conf_col,
                    {"type": "cell", "criteria": "==", "value": 95,
                     "format": workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})}
                )
                ws.conditional_format(
                    1, conf_col, len(sheet_df), conf_col,
                    {"type": "cell", "criteria": "==", "value": 85,
                     "format": workbook.add_format({"bg_color": "#E2F0D9", "font_color": "#375623"})}
                )
                ws.conditional_format(
                    1, conf_col, len(sheet_df), conf_col,
                    {"type": "cell", "criteria": "==", "value": 70,
                     "format": workbook.add_format({"bg_color": "#FFF2CC", "font_color": "#7F6000"})}
                )
                ws.conditional_format(
                    1, conf_col, len(sheet_df), conf_col,
                    {"type": "cell", "criteria": "==", "value": 50,
                     "format": workbook.add_format({"bg_color": "#FCE4D6", "font_color": "#9C0006"})}
                )

    buffer.seek(0)
    return buffer.getvalue()


def trap_audit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare trap-term frequency in source text versus extracted PROVISION.
    This is an audit visual only; it never drives classification.
    """
    if "Provision" not in df.columns:
        return pd.DataFrame(columns=["Term", "Source mentions", "Provision mentions", "Filtered out"])

    source = (
        df.get("Mechanism", pd.Series("", index=df.index)).fillna("").astype(str)
        + " "
        + df.get("Analytical Summary", pd.Series("", index=df.index)).fillna("").astype(str)
    ).str.lower()
    provisions = df["Provision"].fillna("").astype(str).str.lower()

    rows = []
    for term in TRAP_TERMS:
        # Transformer's plural should count too.
        if term == "transformer":
            pattern = r"\btransformers?\b"
        elif term == "tariff":
            pattern = r"\btariffs?\b"
        else:
            pattern = re.escape(term)

        source_n = int(source.str.contains(pattern, regex=True, na=False).sum())
        provision_n = int(provisions.str.contains(pattern, regex=True, na=False).sum())
        rows.append(
            {
                "Term": term,
                "Source mentions": source_n,
                "Provision mentions": provision_n,
                "Filtered out": max(source_n - provision_n, 0),
            }
        )

    return pd.DataFrame(rows)
