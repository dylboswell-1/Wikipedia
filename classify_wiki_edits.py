#!/usr/bin/env python3

import argparse
import csv
import json
import time
from pathlib import Path

import requests


def build_prompt(page_title: str, edit_comment: str) -> str:
    return f"""
You are classifying Wikipedia edits.

Task:
Decide whether this edit is politically related.

Use only these labels:
- political
- not_political
- uncertain

Political includes edits related to:
government, elections, politicians, political parties, legislation, public policy,
courts, war, international relations, political ideologies, protests, state institutions,
or politically organized movements.

Not political includes edits related to:
formatting, spelling, ordinary dates, ordinary sports, entertainment, science,
geography, general biography, maintenance, or vandalism with no clear political content.

Return only valid JSON in this exact format:
{{
  "label": "political",
  "confidence": 0.0,
  "reason": "brief reason"
}}

Wikipedia page title:
{page_title}

Edit comment:
{edit_comment}
""".strip()


def call_ollama(ollama_url: str, model: str, prompt: str, timeout: int) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    response = requests.post(ollama_url, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()


def parse_response(raw: str):
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)

        label = str(parsed.get("label", "uncertain")).strip().lower()
        confidence = parsed.get("confidence", "")
        reason = str(parsed.get("reason", "")).strip()

        if label not in {"political", "not_political", "uncertain"}:
            label = "uncertain"

        return label, confidence, reason

    except json.JSONDecodeError:
        lowered = raw.lower()

        if "not_political" in lowered or "not political" in lowered:
            return "not_political", "", "Fallback parse from non-JSON model response"

        if "political" in lowered:
            return "political", "", "Fallback parse from non-JSON model response"

        return "uncertain", "", "Could not parse model response"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify Wikipedia IP edits as political or not political using an Ollama-compatible model."
    )

    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", required=True, help="Output CSV file")

    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434/api/generate",
        help="Ollama /api/generate endpoint"
    )

    parser.add_argument("--limit", type=int, default=None, help="Only process this many rows")
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds")
    parser.add_argument("--sleep", type=float, default=0.0, help="Delay between requests")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", errors="replace", newline="") as infile:
        reader = csv.DictReader(infile)

        fieldnames = reader.fieldnames

        if fieldnames is None:
            raise ValueError("Input CSV has no header row.")

        required_cols = {"ip", "page_title", "timestamp", "edit_comment"}
        missing = required_cols - set(fieldnames)

        if missing:
            raise ValueError(
                f"Input CSV is missing required columns: {sorted(missing)}. "
                f"Found columns: {fieldnames}"
            )

        output_fields = list(fieldnames) + [
            "political_label",
            "political_confidence",
            "political_reason",
            "raw_model_response",
            "model_used"
        ]

        output_exists = output_path.exists() and output_path.stat().st_size > 0

        with output_path.open("a", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fields)

            if not output_exists:
                writer.writeheader()

            processed = 0

            for row_number, row in enumerate(reader, start=1):
                page_title = row.get("page_title", "")
                edit_comment = row.get("edit_comment", "")

                prompt = build_prompt(page_title, edit_comment)

                try:
                    raw_response = call_ollama(
                        ollama_url=args.ollama_url,
                        model=args.model,
                        prompt=prompt,
                        timeout=args.timeout
                    )

                    label, confidence, reason = parse_response(raw_response)

                except Exception as e:
                    raw_response = ""
                    label = "error"
                    confidence = ""
                    reason = str(e)

                output_row = dict(row)
                output_row["political_label"] = label
                output_row["political_confidence"] = confidence
                output_row["political_reason"] = reason
                output_row["raw_model_response"] = raw_response
                output_row["model_used"] = args.model

                writer.writerow(output_row)
                outfile.flush()

                processed += 1
                print(f"row={row_number} label={label} title={page_title}")

                if args.sleep > 0:
                    time.sleep(args.sleep)

                if args.limit is not None and processed >= args.limit:
                    break

    print(f"Done. Output written to: {output_path}")


if __name__ == "__main__":
    main()