---
name: extracting-job-from-url
description: Use when extracting job description data from a URL or web link (such as LinkedIn, Ashby, Greenhouse, Lever, Workable, or Gupy) to build a Normalized Job Brief for tailoring a resume, or when a job link fails to load, requires login, or tempts guessing requirements from the URL slug.
---

# Extracting Job Data from URLs

## Overview

Extract structured job requirements from a job posting URL and normalize them into the **Normalized Job Brief** required by `tailoring-resumes`.

**Core principle:** Always extract the actual job description text before building a resume. Never guess requirements from a URL slug, and never attempt to bypass login walls or CAPTCHAs.

**REQUIRED SUB-SKILL:** After producing the Normalized Job Brief, return to `tailoring-resumes` to map against `master.md` and run `build.py`.

## Workflow

1. **Run the bundled URL extractor:**
   ```bash
   python3 .agents/skills/extracting-job-from-url/scripts/fetch_job.py "<url>"
   ```
2. **Fallback on HTTP errors, login walls, or empty SPA shells:**
   If `fetch_job.py` prints `STATUS: HTTP_ERROR`, `STATUS: BLOCKED`, or `STATUS: EMPTY_SPA_SHELL`:
   - Query `search_web` with the company name, role title, and URL slug to find a public mirror of the job description.
   - **Never** attempt to bypass login walls, authwalls, Cloudflare Turnstile, or CAPTCHAs.
3. **Hard Stop When JD Text Is Unavailable:**
   If neither `fetch_job.py` nor `search_web` yields the actual job responsibilities and technical requirements (and the user did not supply them in the prompt), **STOP immediately and ask the user to paste the job description text or provide a file (`.pdf`, `.md`, `.txt`)**. Do **not** proceed to `build.py` by inferring stack from the URL slug.
4. **Produce the Normalized Job Brief:**
   Once the JD text is retrieved, extract this exact structure for `tailoring-resumes`:
   - `company_or_agency`: Company name (note if hiring via recruiting agency for a confidential client)
   - `target_role_title`: Exact job title from the posting
   - `resume_lang`: `en_us` or `pt_br` (matching the working language of the job)
   - `outreach_langs`: Language(s) for recruiter outreach if requested
   - `timezone_or_location`: Remote/hybrid model and target timezone (e.g., `EST`, `CET`, `BRT / UTC-3`)
   - `must_have_stack`: Core required technologies and responsibilities
   - `bonus_or_nice_to_have`: Desirable/bonus technologies explicitly marked as nice-to-have
   - `deliverables`: Resume (`.md` + `.pdf`), Cover Letter (`.md` + `.pdf`), and/or Recruiter Outreach (`dist/Email_*.md`)

## Rationalization Table

| Excuse | Reality |
|---|---|
| "LinkedIn/Ashby links usually block scraping, so I'll just extract the role and company from the URL slug" | Many job links return JSON-LD (`JobPosting`), `__NEXT_DATA__`, or `window.__appData` via `fetch_job.py`, or appear in `search_web`. Guessing from the slug produces a generic resume that misses the actual JD. |
| "The URL says `senior-kubernetes-platform-engineer-stripe`, so I already know the stack" | You know 1 keyword (`Kubernetes`), not the cloud provider, IaC tool, observability stack, compliance needs, or bonus tools. If `fetch_job.py` and `search_web` fail, STOP and ask the user. |

## Red Flags - STOP

- Skipping `fetch_job.py` and inferring requirements from the URL path/slug
- Running `build.py` after `fetch_job.py` and `search_web` failed to retrieve the job requirements
- Attempting to bypass a CAPTCHA or login wall
