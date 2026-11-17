---
name: extracting-job-from-file
description: Use when extracting job description data from a local file (.pdf, .md, .txt) to build a Normalized Job Brief for tailoring a resume, or when a job file contains multiple openings, noisy page dumps, or scanned PDF pages.
---

# Extracting Job Data from Files (.pdf, .md, .txt)

## Overview

Extract structured job requirements from local `.pdf`, `.md`, or `.txt` files and normalize them into the **Normalized Job Brief** required by `tailoring-resumes`.

**Core principle:** Use the bundled extractor (`pdftotext` for PDFs, UTF-8/latin-1 reader for `.md`/`.txt`) rather than unavailable third-party Python PDF libraries (`pypdf`, `pdfplumber`, `fitz`), disambiguate multi-role documents explicitly, and separate the job's working language from the recruiter's contact language.

**REQUIRED SUB-SKILL:** After producing the Normalized Job Brief, return to `tailoring-resumes` to map against `master.md` and run `build.py`.

## Workflow

1. **Run the bundled file extractor:**
   ```bash
   python3 .agents/skills/extracting-job-from-file/scripts/extract_job_file.py "<file-path>"
   ```
   - If `extract_job_file.py` reports `STATUS: EMPTY_OR_SCANNED_PDF`, call `read_file` on the PDF path to inspect it visually. If still unreadable or missing requirements, **STOP and ask the user for the job description text**.
2. **Disambiguate Multi-Role Files:**
   Job PDFs and `.md`/`.txt` exports often list multiple openings on the same page:
   - **Single Relevant Match:** If only one opening matches the candidate's domain in `master.md` (SRE, Platform, DevOps, DevSecOps, Cloud, Infrastructure) while others are unrelated (e.g., Backend Rust/Product, Mobile, Frontend), automatically select the matching Cloud/Platform/SRE/DevOps role and state which opening was selected and which was discarded.
   - **Multiple Relevant Matches:** If two or more openings in the file match the candidate's domain (e.g., *Senior SRE* **and** *Senior Platform Engineer*) and the user did not specify which one, **STOP and ask the user which opening to target** (or whether to generate both) before running `build.py`.
3. **Separate Working Language (`resume_lang`) from Recruiter Outreach Language (`outreach_langs`):**
   - Look for explicit cues in the file (*"Send CV in English"*, *"working language: English"*, *"US Timezone EST"*, *"CET"*).
   - Set `resume_lang` (`en_us` or `pt_br`) to the **working language of the role**, even if the file or recruiter headers are in Portuguese or Spanish.
   - If the file includes a recruiter contact (e.g., email or LinkedIn handle), include `dist/Email_Lazaro_Bonifacio_<Role>_<Company>.md` in `deliverables`.
4. **Produce the Normalized Job Brief:**
   Output this exact structure for `tailoring-resumes`:
   - `company_or_agency`: Target company name (or agency name + note if end-client is confidential)
   - `target_role_title`: Exact job title of the selected opening
   - `resume_lang`: `en_us` or `pt_br`
   - `outreach_langs`: Language(s) for `dist/Email_*.md`
   - `timezone_or_location`: Remote/hybrid model and target timezone (e.g., `EST`, `CET`, `BRT / UTC-3`)
   - `must_have_stack`: Core required technologies and responsibilities
   - `bonus_or_nice_to_have`: Desirable/bonus technologies explicitly marked as bonus/nice-to-have
   - `deliverables`: Resume (`.md` + `.pdf`), Cover Letter (`.md` + `.pdf`), and/or Recruiter Outreach (`dist/Email_*.md`)

## Common Mistakes

- **Trying `import pypdf` / `import pdfplumber` / `import fitz` in ad-hoc Python one-liners:** Those packages are not installed. Always run `python3 .agents/skills/extracting-job-from-file/scripts/extract_job_file.py "<path>"` (which uses `/usr/bin/pdftotext`) or the `read_file` tool.
- **Printing the recruiter intro message only in chat instead of saving `dist/Email_*.md`:** When a file requests an intro message or lists recruiter contact details, always pass it in `deliverables` so `tailoring-resumes` writes `dist/Email_Lazaro_Bonifacio_<Role>_<Company>.md`.
