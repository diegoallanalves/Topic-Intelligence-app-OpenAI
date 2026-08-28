from __future__ import annotations

from io import BytesIO
import re
import pandas as pd
from topics import TRAP_TERMS


def normalize_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = ["Mechanism", "Analytical Summary", "Title"]
    lookup = {str(c).strip().lower(): c for c in df.columns}
    mapping = {}
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
            df["Topic Confidence"].isin([50, 70])
            | (df["Classification Error"].astype(str).str.len() > 0)
            | (df["Classification Warning"].astype(str).str.len() > 0)
        ].copy()
        review.to_excel(writer, index=False, sheet_name="Human Review")
        workbook = writer.book
        header = workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#123B6D", "align": "center"})
        wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
        for sheet_name, sheet_df in [("Classified Bills", df), ("Human Review", review)]:
            ws = writer.sheets[sheet_name]
            ws.freeze_panes(1, 1)
            ws.set_row(0, 26)
            for i, col in enumerate(sheet_df.columns):
                ws.write(0, i, col, header)
                if col in {"Title", "Mechanism", "Analytical Summary", "Provision", "Model Raw Output", "Classification Error", "Classification Warning"}:
                    ws.set_column(i, i, 46, wrap)
                elif col in {"Topic", "Topic Runner-Up"}:
                    ws.set_column(i, i, 40, wrap)
                else:
                    ws.set_column(i, i, 18)
    buffer.seek(0)
    return buffer.getvalue()


def trap_audit(df: pd.DataFrame) -> pd.DataFrame:
    source = (
        df.get("Mechanism", pd.Series("", index=df.index)).fillna("").astype(str)
        + " " + df.get("Analytical Summary", pd.Series("", index=df.index)).fillna("").astype(str)
    ).str.lower()
    provisions = df["Provision"].fillna("").astype(str).str.lower()
    rows = []
    for term in TRAP_TERMS:
        if term == "transformer":
            pattern = r"\btransformers?\b"
        elif term == "tariff":
            pattern = r"\btariffs?\b"
        else:
            pattern = re.escape(term)
        source_n = int(source.str.contains(pattern, regex=True, na=False).sum())
        provision_n = int(provisions.str.contains(pattern, regex=True, na=False).sum())
        rows.append({"Term": term, "Source mentions": source_n, "Provision mentions": provision_n, "Filtered out": max(source_n - provision_n, 0)})
    return pd.DataFrame(rows)
