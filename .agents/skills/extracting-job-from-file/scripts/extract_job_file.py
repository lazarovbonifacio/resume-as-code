#!/usr/bin/env python3
"""Extract job description text from local .pdf, .md, or .txt files."""
import re
import shutil
import subprocess
import sys
from pathlib import Path


def extract_pdf(path: Path) -> str:
    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    return ""


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 extract_job_file.py <path-to-file>")
    p = Path(sys.argv[1]).expanduser().resolve()
    if not p.exists():
        print(f"STATUS: FILE_NOT_FOUND ({p})")
        sys.exit(2)

    ext = p.suffix.lower()
    if ext == ".pdf":
        text = extract_pdf(p)
        cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(cleaned) < 50:
            print(f"STATUS: EMPTY_OR_SCANNED_PDF ({p})")
            print("ACTION_REQUIRED: Text layer is empty or too short. Use the read_file tool on the PDF to inspect visually; if still unreadable, stop and ask the user for the job description text.")
            sys.exit(3)
        print(f"SOURCE_FILE: {p} (PDF, {len(cleaned)} chars)")
        print("\n=== EXTRACTED PDF TEXT ===")
        print(cleaned[:16000])
    else:
        try:
            raw = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = p.read_text(encoding="latin-1", errors="replace")
        cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
        if len(cleaned) < 30:
            print(f"STATUS: EMPTY_OR_TOO_SHORT ({p})")
            print("ACTION_REQUIRED: File contains fewer than 30 characters. Stop and ask the user for the full job description.")
            sys.exit(3)
        print(f"SOURCE_FILE: {p} ({ext or 'text'}, {len(cleaned)} chars)")
        print("\n=== EXTRACTED FILE TEXT ===")
        print(cleaned[:16000])


if __name__ == "__main__":
    main()
