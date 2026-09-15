from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from openai import OpenAI

from topics import (
    ALLOWED_CONFIDENCE,
    BANNED_PROVISION_TERMS,
    LEGAL_EFFECT_VERBS,
    TOPICS,
)


POLICY_PATH = Path(__file__).with_name("classification_policy.md")


@dataclass
class ClassificationResult:
    provision: str
    topic: str
    confidence: int
    runner_up: str
    raw_output: str = ""
    validation_note: str = ""


def load_policy() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def clean_cell(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_row_input(mechanism: str, summary: str, title: str) -> str:
    # Deliberately preserves the source order required by the supplied policy:
    # Mechanism -> Analytical Summary -> Title.
    return f"""Classify this Congressional action using the supplied policy.

MECHANISM:
{mechanism or "[blank]"}

ANALYTICAL SUMMARY:
{summary or "[blank]"}

TITLE:
{title or "[blank]"}

Return exactly the four required lines and nothing else.
"""


def parse_response(text: str) -> ClassificationResult:
    if not text or not text.strip():
        raise ValueError("Model returned an empty response.")

    fields = {}
    patterns = {
        "provision": r"(?mi)^\s*PROVISION\s*:\s*(.+?)\s*$",
        "topic": r"(?mi)^\s*TOPIC\s*:\s*(.+?)\s*$",
        "confidence": r"(?mi)^\s*TOPIC_CONFIDENCE\s*:\s*(\d+)\s*$",
        "runner_up": r"(?mi)^\s*TOPIC_RUNNER_UP\s*:\s*(.+?)\s*$",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Missing required field: {name}")
        fields[name] = match.group(1).strip()

    confidence = int(fields["confidence"])
    if fields["topic"] not in TOPICS:
        raise ValueError(f"Invalid topic returned: {fields['topic']!r}")
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(f"Invalid confidence {confidence}; expected one of {sorted(ALLOWED_CONFIDENCE)}.")

    runner_base = re.sub(r"\s*\(rule\s+[^)]+\)\s*$", "", fields["runner_up"], flags=re.I).strip()
    if runner_base not in TOPICS:
        raise ValueError(f"Invalid runner-up topic returned: {fields['runner_up']!r}")
    if runner_base == fields["topic"]:
        raise ValueError("Runner-up topic cannot be the same as the assigned topic.")

    note = validate_provision(fields["provision"])

    return ClassificationResult(
        provision=fields["provision"],
        topic=fields["topic"],
        confidence=confidence,
        runner_up=fields["runner_up"],
        raw_output=text.strip(),
        validation_note=note,
    )


def validate_provision(provision: str) -> str:
    if provision.strip().upper() == "NONE STATED":
        return ""

    lower = provision.lower()
    found_banned = [term for term in BANNED_PROVISION_TERMS if re.search(rf"\b{re.escape(term)}\b", lower)]
    if found_banned:
        return "Provision warning: banned consequence term(s): " + ", ".join(sorted(found_banned))

    words = set(re.findall(r"[a-z]+", lower))
    if not (words & LEGAL_EFFECT_VERBS):
        return "Provision warning: no recognised legal-effect verb was detected."

    return ""


def classify_one(
    client: OpenAI,
    policy: str,
    model: str,
    mechanism: str,
    summary: str,
    title: str,
    max_retries: int = 2,
) -> ClassificationResult:
    row_input = build_row_input(mechanism, summary, title)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            repair = ""
            if attempt:
                repair = (
                    "\nIMPORTANT REPAIR: Your previous response could not be parsed or validated. "
                    "Follow the four-line OUTPUT contract exactly, use one verbatim topic name, "
                    "and use only confidence 95, 85, 70, or 50."
                )

            response = client.responses.create(
                model=model,
                instructions=policy + repair,
                input=row_input,
            )
            result = parse_response(response.output_text)

            # A warning is retained for human audit instead of silently rewriting the model's provision.
            return result
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"Classification failed after retries: {last_error}") from last_error


def classify_dataframe(
    df: pd.DataFrame,
    api_key: str,
    model: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    max_retries: int = 2,
) -> pd.DataFrame:
    required = ["Mechanism", "Analytical Summary", "Title"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Missing required column(s): "
            + ", ".join(missing)
            + ". The new policy requires Mechanism, Analytical Summary, and Title."
        )

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing.")

    policy = load_policy()
    client = OpenAI(api_key=api_key)
    total = len(df)

    provisions = []
    topics = []
    confidences = []
    runner_ups = []
    validation_notes = []
    model_outputs = []
    errors = []

    for pos, (_, row) in enumerate(df.iterrows(), start=1):
        mechanism = clean_cell(row["Mechanism"])
        summary = clean_cell(row["Analytical Summary"])
        title = clean_cell(row["Title"])

        if progress_callback:
            progress_callback(pos - 1, total, f"Classifying {pos:,} of {total:,}: {title[:70]}")

        try:
            result = classify_one(
                client=client,
                policy=policy,
                model=model,
                mechanism=mechanism,
                summary=summary,
                title=title,
                max_retries=max_retries,
            )
            provisions.append(result.provision)
            topics.append(result.topic)
            confidences.append(result.confidence)
            runner_ups.append(result.runner_up)
            validation_notes.append(result.validation_note)
            model_outputs.append(result.raw_output)
            errors.append("")
        except Exception as exc:
            # Preserve the row and make failures visible instead of inventing a classification.
            provisions.append("ERROR")
            topics.append("ERROR")
            confidences.append(0)
            runner_ups.append("ERROR")
            validation_notes.append("")
            model_outputs.append("")
            errors.append(str(exc))

        if progress_callback:
            progress_callback(pos, total, f"Completed {pos:,} of {total:,}")

    out = df.copy()

    # Insert requested post-processing fields at the beginning of the master dataset.
    leading = pd.DataFrame(
        {
            "Topic": topics,
            "Provision": provisions,
            "Topic Confidence": confidences,
            "Topic Runner-Up": runner_ups,
            "Classification Warning": validation_notes,
            "Classification Error": errors,
        },
        index=out.index,
    )
    out = pd.concat([leading, out], axis=1)

    # Raw model output is useful for debugging but deliberately placed at the end.
    out["Model Raw Output"] = model_outputs
    return out
