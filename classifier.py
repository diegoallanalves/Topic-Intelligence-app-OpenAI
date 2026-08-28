from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from openai import OpenAI

from topics import ALLOWED_CONFIDENCE, BANNED_PROVISION_TERMS, LEGAL_EFFECT_VERBS, TOPICS

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
    return "" if pd.isna(value) else str(value).strip()


def build_row_input(mechanism: str, summary: str, title: str) -> str:
    return f"""Classify this Congressional action using the supplied policy.

MECHANISM:
{mechanism or '[blank]'}

ANALYTICAL SUMMARY:
{summary or '[blank]'}

TITLE:
{title or '[blank]'}

Return exactly the four required lines and nothing else.
"""


def validate_provision(provision: str) -> str:
    if provision.strip().upper() == "NONE STATED":
        return ""
    lower = provision.lower()
    banned = [t for t in BANNED_PROVISION_TERMS if re.search(rf"\b{re.escape(t)}\b", lower)]
    if banned:
        return "Provision warning: banned consequence term(s): " + ", ".join(sorted(banned))
    words = set(re.findall(r"[a-z]+", lower))
    if not (words & LEGAL_EFFECT_VERBS):
        return "Provision warning: no recognised legal-effect verb was detected."
    return ""


def parse_response(text: str) -> ClassificationResult:
    if not text or not text.strip():
        raise ValueError("Model returned an empty response.")
    patterns = {
        "provision": r"(?mi)^\s*PROVISION\s*:\s*(.+?)\s*$",
        "topic": r"(?mi)^\s*TOPIC\s*:\s*(.+?)\s*$",
        "confidence": r"(?mi)^\s*TOPIC_CONFIDENCE\s*:\s*(\d+)\s*$",
        "runner_up": r"(?mi)^\s*TOPIC_RUNNER_UP\s*:\s*(.+?)\s*$",
    }
    fields = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Missing required field: {name}")
        fields[name] = match.group(1).strip()

    confidence = int(fields["confidence"])
    if fields["topic"] not in TOPICS:
        raise ValueError(f"Invalid topic returned: {fields['topic']!r}")
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError("Confidence must be exactly 95, 85, 70 or 50.")
    runner_base = re.sub(r"\s*\(rule\s+[^)]+\)\s*$", "", fields["runner_up"], flags=re.I).strip()
    if runner_base not in TOPICS:
        raise ValueError(f"Invalid runner-up: {fields['runner_up']!r}")
    if runner_base == fields["topic"]:
        raise ValueError("Runner-up cannot equal the assigned topic.")

    return ClassificationResult(
        provision=fields["provision"],
        topic=fields["topic"],
        confidence=confidence,
        runner_up=fields["runner_up"],
        raw_output=text.strip(),
        validation_note=validate_provision(fields["provision"]),
    )


def classify_one(client: OpenAI, policy: str, model: str, mechanism: str, summary: str, title: str, max_retries: int = 2) -> ClassificationResult:
    row_input = build_row_input(mechanism, summary, title)
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            repair = "" if attempt == 0 else (
                "\nREPAIR: Follow the four-line OUTPUT contract exactly. Use one verbatim topic, "
                "a different valid runner-up, and only confidence 95, 85, 70 or 50."
            )
            response = client.responses.create(model=model, instructions=policy + repair, input=row_input)
            return parse_response(response.output_text)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Classification failed after retries: {last_error}") from last_error


def classify_dataframe(df: pd.DataFrame, api_key: str, model: str, progress_callback: Optional[Callable[[int, int, str], None]] = None, max_retries: int = 2) -> pd.DataFrame:
    required = ["Mechanism", "Analytical Summary", "Title"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)
    policy = load_policy()
    total = len(df)
    records = []

    for pos, (_, row) in enumerate(df.iterrows(), start=1):
        title = clean_cell(row["Title"])
        if progress_callback:
            progress_callback(pos - 1, total, f"Classifying {pos:,} of {total:,}: {title[:70]}")
        try:
            result = classify_one(client, policy, model, clean_cell(row["Mechanism"]), clean_cell(row["Analytical Summary"]), title, max_retries)
            records.append({
                "Topic": result.topic,
                "Provision": result.provision,
                "Topic Confidence": result.confidence,
                "Topic Runner-Up": result.runner_up,
                "Classification Warning": result.validation_note,
                "Classification Error": "",
                "Model Raw Output": result.raw_output,
            })
        except Exception as exc:
            records.append({
                "Topic": "ERROR", "Provision": "ERROR", "Topic Confidence": 0,
                "Topic Runner-Up": "ERROR", "Classification Warning": "",
                "Classification Error": str(exc), "Model Raw Output": "",
            })
        if progress_callback:
            progress_callback(pos, total, f"Completed {pos:,} of {total:,}")

    result_df = pd.DataFrame(records, index=df.index)
    raw_output = result_df.pop("Model Raw Output")
    out = pd.concat([result_df, df.copy()], axis=1)
    out["Model Raw Output"] = raw_output
    return out
