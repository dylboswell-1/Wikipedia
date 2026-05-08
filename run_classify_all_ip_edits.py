#!/usr/bin/env python3

import argparse
import csv
import subprocess
import tempfile
from pathlib import Path


REQUIRED_COLUMNS = ["ip", "page_title", "timestamp", "edit_comment"]


def clean_csv(input_csv: Path, cleaned_dir: Path) -> tuple[bool, str, int, int, Path | None]:
    """
    Create a cleaned CSV containing only rows where all required fields are non-empty.

    Returns:
        is_valid_file:
            True if the file has the required columns and at least one complete row.

        reason:
            Explanation of what happened.

        total_rows:
            Number of data rows in the original CSV.

        kept_rows:
            Number of complete rows written to the cleaned CSV.

        cleaned_path:
            Path to cleaned CSV, or None if no valid cleaned file was created.
    """

    try:
        with input_csv.open("r", encoding="utf-8", errors="replace", newline="") as infile:
            reader = csv.DictReader(infile)

            fieldnames = reader.fieldnames

            if fieldnames is None:
                return False, "missing header row", 0, 0, None

            missing_columns = [col for col in REQUIRED_COLUMNS if col not in fieldnames]

            if missing_columns:
                return False, f"missing required columns: {missing_columns}", 0, 0, None

            cleaned_path = cleaned_dir / input_csv.name

            total_rows = 0
            kept_rows = 0

            with cleaned_path.open("w", encoding="utf-8", newline="") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    total_rows += 1

                    row_is_complete = True

                    for col in REQUIRED_COLUMNS:
                        value = row.get(col)

                        if value is None or value.strip() == "":
                            row_is_complete = False
                            break

                    if row_is_complete:
                        writer.writerow(row)
                        kept_rows += 1

            if total_rows == 0:
                return False, "file has header but no data rows", total_rows, kept_rows, None

            if kept_rows == 0:
                return False, "no rows had all required values", total_rows, kept_rows, None

            skipped_rows = total_rows - kept_rows
            return (
                True,
                f"kept {kept_rows} rows; skipped {skipped_rows} incomplete rows",
                total_rows,
                kept_rows,
                cleaned_path,
            )

    except Exception as e:
        return False, f"could not read/clean file: {e}", 0, 0, None


def make_output_path(input_csv: Path, input_root: Path, output_root: Path) -> Path:
    """
    Preserve folder structure under Data/ip-edits-output.

    Example:
        Data/ip-edits-output/subfolder/file.csv

    becomes:
        Data/classified-ip-edits-output/subfolder/file_classified.csv
    """

    relative_path = input_csv.relative_to(input_root)
    output_name = relative_path.with_name(relative_path.stem + "_classified.csv")
    return output_root / output_name


def run_classifier(
    classify_script: Path,
    input_csv: Path,
    output_csv: Path,
    model: str,
    ollama_url: str,
    limit: int | None,
    timeout: int,
    sleep: float,
) -> int:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "python3",
        str(classify_script),
        "--input",
        str(input_csv),
        "--output",
        str(output_csv),
        "--model",
        model,
        "--ollama-url",
        ollama_url,
        "--timeout",
        str(timeout),
        "--sleep",
        str(sleep),
    ]

    if limit is not None:
        command.extend(["--limit", str(limit)])

    print()
    print("Running classifier:")
    print(" ".join(command))

    result = subprocess.run(command)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean extracted Wikipedia IP edit CSVs and run classify_ip_edits.py on complete rows."
    )

    parser.add_argument(
        "--input-dir",
        default="Data/ip-edits-output",
        help="Directory containing extracted IP edit CSV files",
    )

    parser.add_argument(
        "--output-dir",
        default="Data/classified-ip-edits-output",
        help="Directory where classified CSV files should be written",
    )

    parser.add_argument(
        "--classify-script",
        default="classify_ip_edits.py",
        help="Path to classify_ip_edits.py",
    )

    parser.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model name",
    )

    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434/api/generate",
        help="Ollama /api/generate endpoint",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit per file, useful for testing",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Ollama request timeout in seconds",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between model calls",
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files whose classified output already exists",
    )

    args = parser.parse_args()

    project_root = Path.cwd()

    input_root = (project_root / args.input_dir).resolve()
    output_root = (project_root / args.output_dir).resolve()
    classify_script = (project_root / args.classify_script).resolve()

    if not input_root.exists():
        raise FileNotFoundError(f"Input directory not found: {input_root}")

    if not classify_script.exists():
        raise FileNotFoundError(f"Classifier script not found: {classify_script}")

    output_root.mkdir(parents=True, exist_ok=True)

    report_path = output_root / "classification_run_report.csv"

    csv_files = sorted(input_root.rglob("*.csv"))

    if not csv_files:
        print(f"No CSV files found under: {input_root}")
        return

    print(f"Project root: {project_root}")
    print(f"Input folder: {input_root}")
    print(f"Output folder: {output_root}")
    print(f"Classifier script: {classify_script}")
    print(f"Found {len(csv_files)} CSV files.")

    total_cleanable_files = 0
    total_skipped_files = 0
    total_completed_files = 0
    total_failed_files = 0
    total_original_rows = 0
    total_kept_rows = 0

    with tempfile.TemporaryDirectory(prefix="cleaned_ip_edits_") as temp_dir:
        cleaned_root = Path(temp_dir)

        with report_path.open("w", encoding="utf-8", newline="") as report_file:
            report_writer = csv.DictWriter(
                report_file,
                fieldnames=[
                    "input_csv",
                    "cleaned_csv",
                    "output_csv",
                    "status",
                    "reason",
                    "total_rows",
                    "kept_rows",
                    "skipped_rows",
                ],
            )

            report_writer.writeheader()

            for input_csv in csv_files:
                output_csv = make_output_path(input_csv, input_root, output_root)

                print()
                print(f"Checking and cleaning: {input_csv}")

                is_valid, reason, total_rows, kept_rows, cleaned_csv = clean_csv(
                    input_csv=input_csv,
                    cleaned_dir=cleaned_root,
                )

                total_original_rows += total_rows
                total_kept_rows += kept_rows

                if not is_valid or cleaned_csv is None:
                    print(f"Skipping file: {reason}")
                    total_skipped_files += 1

                    report_writer.writerow(
                        {
                            "input_csv": str(input_csv),
                            "cleaned_csv": "",
                            "output_csv": str(output_csv),
                            "status": "skipped",
                            "reason": reason,
                            "total_rows": total_rows,
                            "kept_rows": kept_rows,
                            "skipped_rows": total_rows - kept_rows,
                        }
                    )
                    report_file.flush()
                    continue

                total_cleanable_files += 1

                print(reason)

                if args.skip_existing and output_csv.exists():
                    print(f"Skipping existing output: {output_csv}")
                    total_skipped_files += 1

                    report_writer.writerow(
                        {
                            "input_csv": str(input_csv),
                            "cleaned_csv": str(cleaned_csv),
                            "output_csv": str(output_csv),
                            "status": "skipped_existing",
                            "reason": "output already exists",
                            "total_rows": total_rows,
                            "kept_rows": kept_rows,
                            "skipped_rows": total_rows - kept_rows,
                        }
                    )
                    report_file.flush()
                    continue

                return_code = run_classifier(
                    classify_script=classify_script,
                    input_csv=cleaned_csv,
                    output_csv=output_csv,
                    model=args.model,
                    ollama_url=args.ollama_url,
                    limit=args.limit,
                    timeout=args.timeout,
                    sleep=args.sleep,
                )

                if return_code == 0:
                    print(f"Completed: {output_csv}")
                    total_completed_files += 1
                    status = "completed"
                    run_reason = "ok"
                else:
                    print(f"Classifier failed with return code {return_code}")
                    total_failed_files += 1
                    status = "failed"
                    run_reason = f"classifier returned code {return_code}"

                report_writer.writerow(
                    {
                        "input_csv": str(input_csv),
                        "cleaned_csv": str(cleaned_csv),
                        "output_csv": str(output_csv),
                        "status": status,
                        "reason": run_reason,
                        "total_rows": total_rows,
                        "kept_rows": kept_rows,
                        "skipped_rows": total_rows - kept_rows,
                    }
                )
                report_file.flush()

    print()
    print("Run summary")
    print(f"CSV files found:        {len(csv_files)}")
    print(f"Cleanable files:        {total_cleanable_files}")
    print(f"Skipped files:          {total_skipped_files}")
    print(f"Completed files:        {total_completed_files}")
    print(f"Failed files:           {total_failed_files}")
    print(f"Original rows scanned:  {total_original_rows}")
    print(f"Complete rows kept:     {total_kept_rows}")
    print(f"Incomplete rows skipped:{total_original_rows - total_kept_rows}")
    print(f"Report written to:      {report_path}")


if __name__ == "__main__":
    main()