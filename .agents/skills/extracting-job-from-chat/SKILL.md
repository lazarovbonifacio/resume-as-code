---
name: extracting-job-from-chat
description: Use when extracting job description data pasted directly in the chat (such as a LinkedIn DM, WhatsApp forward, email body, or raw job description text) to build a Normalized Job Brief for tailoring a resume, especially when the recruiter's message language differs from the job's working language or when the pasted text is incomplete.
---

# Extracting Job Data from Chat

## Overview

Parse job postings, recruiter DMs, WhatsApp forwards, or raw job descriptions pasted directly in chat into the **Normalized Job Brief** required by `tailoring-resumes`.

**Core principle:** Separate the recruiter's message language from the role's working language, distinguish recruiting agencies from confidential end-clients, and stop if the chat prompt lacks concrete technical requirements.

**REQUIRED SUB-SKILL:** After producing the Normalized Job Brief, return to `tailoring-resumes` to map against `master.md` and run `build.py`.

## Workflow

1. **Minimum Completeness Gate (Hard Stop on Vague Chat Prompts):**
   Verify the pasted chat text includes:
   - A target role/domain (e.g., SRE, Platform, DevOps, DevSecOps, Cloud, Infrastructure), **and**
   - At least **3 concrete technical requirements or responsibilities** (e.g., `AWS, EKS, Terraform` or specific duties).
   - **Hard Stop:** If the user only writes a vague request (*"Gera um currículo pra uma vaga de SRE sênior remoto que paga em dólar"* or *"Preciso de um CV pra DevOps na Empresa X"*) without stack or responsibilities, **STOP and ask the user to paste the job description or required stack**. Do **not** guess requirements.
2. **Separate Working Language (`resume_lang`) from Recruiter Language (`outreach_langs`):**
   Recruiters in LATAM/Brazil/Spain frequently send messages in Portuguese or Spanish for international roles whose working language is English:
   - If the message mentions *"cliente internacional"*, *"idioma de trabalho: Inglês"*, *"inglés avanzado"*, *"US timezone / EST"*, or *"fuso CET / Europa"*, set `resume_lang = en_us` (so both the Resume and Cover Letter are built in English).
   - Set `outreach_langs` to include **both** the recruiter's language (`pt_br` or `es`) and `en_us` so `tailoring-resumes` persists a bilingual reply file in `dist/Email_Lazaro_Bonifacio_<Role>_<Company>.md`.
3. **Distinguish Recruiting Agency vs. Confidential End-Client:**
   - If the chat message is from a recruiting agency or consultancy (e.g., *Noara Labs*, *TechHunt Consultoria*) hiring for an unnamed client (*"para cliente internacional"*):
     - Set `--company` to the agency slug (e.g., `"TechHunt"` or `"Noara_Labs"`) for file naming in `dist/`.
     - Note in `company_or_agency` that the end-client is confidential so the Cover Letter uses `**Re: <Role> (<Agency> Client)**` and `Dear Hiring Team,` (never *"apply for the role at TechHunt"* as if the agency itself were the engineering employer).
4. **Produce the Normalized Job Brief:**
   Output this exact structure for `tailoring-resumes`:
   - `company_or_agency`: Company name, or `<Agency> (Confidential End-Client)`
   - `target_role_title`: Exact job title from the message
   - `resume_lang`: `en_us` or `pt_br` (working language of the role)
   - `outreach_langs`: Language(s) for `dist/Email_*.md` (e.g., `[pt_br, en_us]` or `[es, en_us]`)
   - `timezone_or_location`: Remote/hybrid model and target timezone (e.g., `EST`, `CET`, `BRT / UTC-3`)
   - `must_have_stack`: Core required technologies and responsibilities
   - `bonus_or_nice_to_have`: Desirable/bonus technologies explicitly marked as bonus/desirable
   - `deliverables`: Resume (`.md` + `.pdf`), Cover Letter (`.md` + `.pdf`), and/or Recruiter Outreach (`dist/Email_*.md` — always included when the input is a recruiter DM/WhatsApp/email)

## Common Mistakes

- **Building the resume in `pt_br` because the WhatsApp/LinkedIn message was written in Portuguese for a US/EU English role:** Always key `resume_lang` to the working language of the job, not the language of the chat wrapper.
- **Addressing the Cover Letter to a recruiting agency as if it were the product company:** When an agency hires for a confidential client, address the Cover Letter to `Dear Hiring Team,` and frame the outreach message around the agency's client.
- **Replying to a recruiter DM only in chat text without saving `dist/Email_Lazaro_Bonifacio_<Role>_<Company>.md`:** Always include `dist/Email_*.md` in `deliverables` for recruiter messages.
