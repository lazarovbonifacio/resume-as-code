#!/usr/bin/env python3
"""Build Harvard-style resumes (.md and .pdf) from master.md Lego blocks."""
import argparse
import os
import re
import sys
from pathlib import Path

ROLES = ("sre", "platform", "devops", "devsecops", "cloud", "infra")
LANGS = ("pt_br", "en_us")
MAX_PAGES = 2

LABELS = {
    "pt_br": {
        "summary": "RESUMO PROFISSIONAL",
        "skills": "COMPETÊNCIAS TÉCNICAS",
        "experience": "EXPERIÊNCIA PROFISSIONAL",
        "career_break": "PAUSA NA CARREIRA & TRANSIÇÃO PROFISSIONAL",
        "projects": "PROJETOS DE PLATAFORMA & OPEN SOURCE",
        "education": "FORMAÇÃO ACADÊMICA",
        "certifications": "CERTIFICAÇÕES",
    },
    "en_us": {
        "summary": "PROFESSIONAL SUMMARY",
        "skills": "TECHNICAL SKILLS",
        "experience": "PROFESSIONAL EXPERIENCE",
        "career_break": "CAREER BREAK & PROFESSIONAL DEVELOPMENT",
        "projects": "KEY PLATFORM & OPEN SOURCE PROJECTS",
        "education": "EDUCATION",
        "certifications": "CERTIFICATIONS",
    },
}

ROLE_FILENAMES = {
    "sre": "SRE",
    "platform": "Platform_Engineer",
    "devops": "DevOps_Engineer",
    "devsecops": "DevSecOps_Engineer",
    "cloud": "Cloud_Engineer",
    "infra": "Infrastructure_Engineer",
}


def md_inline(text: str) -> str:
    """Convert inline markdown (**bold** and [text](url)) to HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color:#000;text-decoration:none;">\1</a>', text)
    return text


def parse_master(path: Path) -> dict:
    """Parse master.md into profile, sections, and tagged blocks."""
    data = {
        "profile": {},
        "headlines": [],
        "summaries": [],
        "skills": [],
        "companies": [],
        "career_break": [],
        "projects": [],
        "education": [],
        "certifications": [],
    }
    section = None
    curr_block = None
    curr_company = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line == "---" or line.startswith(">"):
            continue

        if line.startswith("## "):
            section = line[3:].strip().lower().replace(" ", "_")
            curr_block = None
            curr_company = None
            continue

        if section == "experience" and line.startswith("### Company:"):
            comp_id = line.split(":", 1)[1].strip()
            curr_company = {"id": comp_id, "meta": {}, "bullets": []}
            data["companies"].append(curr_company)
            curr_block = None
            continue

        m_block = re.match(r"^#{3,4}\s+\[([a-z0-9_-]+)\]\s+tags:\s*(.+)$", line)
        if m_block:
            bid, raw_tags = m_block.group(1), m_block.group(2)
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            curr_block = {"id": bid, "tags": tags, "fields": {}}
            if section == "experience":
                assert curr_company is not None, f"Block {bid} outside company"
                curr_company["bullets"].append(curr_block)
            elif section in data:
                data[section].append(curr_block)
            continue

        m_kv = re.match(r"^-\s+\*\*([a-z0-9_]+)\*\*:\s*(.*)$", line)
        if m_kv:
            k, v = m_kv.group(1), m_kv.group(2).strip()
            if section == "profile":
                data["profile"][k] = v
            elif curr_block is not None:
                curr_block["fields"][k] = v
            elif curr_company is not None:
                curr_company["meta"][k] = v

    return data


def matches(block: dict, role: str, include_ids: set | None, exclude_ids: set) -> bool:
    bid = block["id"]
    if bid in exclude_ids:
        return False
    if include_ids is not None and bid in include_ids:
        return True
    tags = block["tags"]
    return "all" in tags or role in tags


def select_resume(data: dict, role: str, lang: str, include_ids: set | None = None, exclude_ids: set | None = None, custom_title: str | None = None) -> dict:
    exclude_ids = exclude_ids or set()
    p = data["profile"]

    headlines = [b for b in data["headlines"] if matches(b, role, include_ids, exclude_ids)]
    headline = custom_title or (headlines[0]["fields"][lang] if headlines else role.upper())

    summaries = [b for b in data["summaries"] if matches(b, role, include_ids, exclude_ids)]
    summary = summaries[0]["fields"][lang] if summaries else ""

    skills = [b["fields"][lang] for b in data["skills"] if matches(b, role, include_ids, exclude_ids)]

    experiences = []
    for comp in data["companies"]:
        bullets = [b["fields"][lang] for b in comp["bullets"] if matches(b, role, include_ids, exclude_ids)]
        if not bullets:
            continue
        meta = comp["meta"]
        role_title = meta.get(f"role_{role}_{lang}") or meta.get(f"role_default_{lang}", "")
        experiences.append({
            "company": meta["company"],
            "location": meta[f"location_{lang}"],
            "dates": meta[f"dates_{lang}"],
            "context": meta.get(f"context_{lang}", ""),
            "title": role_title,
            "bullets": bullets,
        })

    career_breaks = []
    for b in data["career_break"]:
        if matches(b, role, include_ids, exclude_ids):
            f = b["fields"]
            career_breaks.append({
                "title": f[f"title_{lang}"],
                "location": f[f"location_{lang}"],
                "dates": f[f"dates_{lang}"],
                "desc": f[lang],
            })

    projects = []
    for b in data["projects"]:
        if matches(b, role, include_ids, exclude_ids):
            f = b["fields"]
            projects.append({
                "name": f["name"],
                "url": f["url"],
                "sub": f[f"sub_{lang}"],
                "desc": f[lang],
            })

    education = []
    for b in data["education"]:
        if matches(b, role, include_ids, exclude_ids):
            f = b["fields"]
            education.append({
                "institution": f[f"institution_{lang}"],
                "degree": f[f"degree_{lang}"],
                "dates": f[f"dates_{lang}"],
            })

    certs = [b["fields"][lang] for b in data["certifications"] if matches(b, role, include_ids, exclude_ids)]

    return {
        "name": p["name"],
        "email": p["email"],
        "phone": p["phone"],
        "website": p["website"],
        "linkedin": p["linkedin"],
        "github": p["github"],
        "location": p[f"location_{lang}"],
        "headline": headline,
        "summary": summary,
        "skills": skills,
        "experiences": experiences,
        "career_breaks": career_breaks,
        "projects": projects,
        "education": education,
        "certifications": certs,
        "labels": LABELS[lang],
    }


def render_markdown(r: dict) -> str:
    L = r["labels"]
    lines = [
        f"# {r['name']}",
        f"**{r['headline']}**  ",
        f"{r['location']} | {r['phone']} | {r['email']}  ",
        f"[linkedin.com/in/lazarovbonifacio](https://{r['linkedin']}) | [github.com/lazarovbonifacio](https://{r['github']}) | [{r['website']}](https://{r['website']})",
        "",
        "---",
        "",
        f"## {L['summary']}",
        "",
        r["summary"],
        "",
        "---",
        "",
        f"## {L['skills']}",
        "",
    ]
    for s in r["skills"]:
        lines.append(f"- {s}")

    lines += ["", "---", "", f"## {L['experience']}", ""]
    for exp in r["experiences"]:
        lines.append(f"### **{exp['company']}** — {exp['location']}")
        lines.append(f"*{exp['title']}* | *{exp['dates']}*")
        if exp["context"]:
            lines.append(f"*{exp['context']}*")
        lines.append("")
        for b in exp["bullets"]:
            lines.append(f"- {b}")
        lines.append("")

    if r["career_breaks"]:
        lines += ["---", "", f"## {L['career_break']}", ""]
        for cb in r["career_breaks"]:
            lines.append(f"### **{cb['title']}** — {cb['location']} (*{cb['dates']}*)")
            lines.append(f"- {cb['desc']}")
            lines.append("")

    if r["projects"]:
        lines += ["---", "", f"## {L['projects']}", ""]
        for prj in r["projects"]:
            lines.append(f"### [{prj['name']}]({prj['url']}) — *{prj['sub']}*")
            lines.append(f"- {prj['desc']}")
            lines.append("")

    lines += ["---", "", f"## {L['education']}", ""]
    for edu in r["education"]:
        lines.append(f"- **{edu['degree']}** — {edu['institution']} (*{edu['dates']}*)")

    lines += ["", "---", "", f"## {L['certifications']}", ""]
    for c in r["certifications"]:
        lines.append(f"- {c}")

    return "\n".join(lines).strip() + "\n"


def render_harvard_html(r: dict, font_pt: float = 9.2, line_height: float = 1.2) -> str:
    """Render strict Harvard OCS template HTML compatible with QTextDocument & browsers."""
    L = r["labels"]
    sub_pt = round(font_pt - 0.4, 1)
    sec_pt = round(font_pt + 0.5, 1)

    def sec_header(title: str) -> str:
        return (
            f'<div style="font-size:{sec_pt}pt;font-weight:bold;margin-top:6px;margin-bottom:0px;">{title}</div>'
            f'<hr style="border:0;background-color:#000;height:1px;margin-top:1px;margin-bottom:3px;" />'
        )

    skills_html = "".join(
        f'<li style="margin-bottom:1px;">{md_inline(s)}</li>' for s in r["skills"]
    )

    exp_html = []
    for exp in r["experiences"]:
        ctx_row = (
            f'<tr><td colspan="2" style="font-size:{sub_pt}pt;font-style:italic;color:#222;">{exp["context"]}</td></tr>'
            if exp["context"]
            else ""
        )
        bullets = "".join(
            f'<li style="margin-bottom:1px;">{md_inline(b)}</li>' for b in exp["bullets"]
        )
        exp_html.append(
            f'<table width="100%" cellspacing="0" cellpadding="0" style="margin-top:4px;">'
            f'<tr><td style="font-size:{sec_pt}pt;font-weight:bold;">{exp["company"]}</td>'
            f'<td align="right" style="font-size:{font_pt}pt;">{exp["location"]}</td></tr>'
            f'<tr><td style="font-size:{font_pt}pt;font-style:italic;font-weight:bold;">{exp["title"]}</td>'
            f'<td align="right" style="font-size:{font_pt}pt;font-style:italic;">{exp["dates"]}</td></tr>'
            f"{ctx_row}</table>"
            f'<ul style="margin-top:1px;margin-bottom:3px;margin-left:15px;">{bullets}</ul>'
        )

    cb_html = []
    for cb in r["career_breaks"]:
        cb_html.append(
            f'<table width="100%" cellspacing="0" cellpadding="0" style="margin-top:3px;">'
            f'<tr><td style="font-size:{font_pt}pt;font-weight:bold;">{cb["title"]}</td>'
            f'<td align="right" style="font-size:{font_pt}pt;font-style:italic;">{cb["location"]} &bull; {cb["dates"]}</td></tr>'
            f"</table>"
            f'<ul style="margin-top:1px;margin-bottom:3px;margin-left:15px;">'
            f'<li style="margin-bottom:1px;">{md_inline(cb["desc"])}</li></ul>'
        )

    proj_html = []
    for prj in r["projects"]:
        proj_html.append(
            f'<div style="margin-top:2px;margin-bottom:2px;">'
            f'<span style="font-weight:bold;">{prj["name"]}</span> '
            f'<span style="font-style:italic;font-size:{sub_pt}pt;">({prj["sub"]})</span> — '
            f'{md_inline(prj["desc"])}'
            f"</div>"
        )

    edu_rows = "".join(
        f'<tr><td style="padding-bottom:1px;"><b>{edu["degree"]}</b> — {edu["institution"]}</td>'
        f'<td align="right" style="font-style:italic;padding-bottom:1px;">{edu["dates"]}</td></tr>'
        for edu in r["education"]
    )

    cert_html = "".join(
        f'<li style="margin-bottom:1px;">{md_inline(c)}</li>' for c in r["certifications"]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: "Times New Roman", "Liberation Serif", Georgia, serif;
    font-size: {font_pt}pt;
    line-height: {line_height};
    color: #000000;
  }}
  a {{ color: #000000; text-decoration: none; }}
  ul {{ margin-top: 1px; margin-bottom: 3px; padding-left: 15px; }}
  li {{ margin-bottom: 1px; }}
</style>
</head>
<body>
  <div align="center" style="margin-bottom:4px;">
    <div style="font-size:15pt;font-weight:bold;letter-spacing:0.5px;">{r['name'].upper()}</div>
    <div style="font-size:{font_pt}pt;font-weight:bold;margin-top:1px;">{r['headline']}</div>
    <div style="font-size:{sub_pt}pt;margin-top:1px;">
      {r['location']} &bull; {r['phone']} &bull; <a href="mailto:{r['email']}">{r['email']}</a>
    </div>
    <div style="font-size:{sub_pt}pt;">
      <a href="https://{r['linkedin']}">{r['linkedin']}</a> &bull;
      <a href="https://{r['github']}">{r['github']}</a> &bull;
      <a href="https://{r['website']}">{r['website']}</a>
    </div>
  </div>

  {sec_header(L['summary'])}
  <div style="margin-top:1px;margin-bottom:3px;text-align:justify;">
    {md_inline(r['summary'])}
  </div>

  {sec_header(L['skills'])}
  <ul>{skills_html}</ul>

  {sec_header(L['experience'])}
  {"".join(exp_html)}

  {sec_header(L['career_break']) if cb_html else ""}
  {"".join(cb_html)}

  {sec_header(L['projects']) if proj_html else ""}
  {"".join(proj_html)}

  {sec_header(L['education'])}
  <table width="100%" cellspacing="0" cellpadding="0" style="margin-top:1px;">
    {edu_rows}
  </table>

  {sec_header(L['certifications'])}
  <ul>{cert_html}</ul>
</body>
</html>"""


def write_pdf(res: dict, pdf_path: Path) -> int:
    """Render PDF enforcing the strict 2-page maximum limit."""
    # shortcut: uses Qt QTextDocument (HTML4/CSS2 subset), switch to WeasyPrint/Chromium if flexbox is needed
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QMarginsF, QSizeF
    from PyQt6.QtGui import QGuiApplication, QPageLayout, QPageSize, QTextDocument
    from PyQt6.QtPrintSupport import QPrinter

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_path))

    # Try progressive typography presets until pageCount() <= MAX_PAGES
    presets = [
        (9.2, 1.20, 10, 8),
        (8.8, 1.16, 9, 7),
        (8.4, 1.12, 8, 6),
    ]
    doc = QTextDocument()
    doc.setDocumentMargin(0)

    for font_pt, lh, mx, my in presets:
        layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(mx, my, mx, my),
            QPageLayout.Unit.Millimeter,
        )
        printer.setPageLayout(layout)
        doc.setHtml(render_harvard_html(res, font_pt=font_pt, line_height=lh))
        doc.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.DevicePixel).size()))
        if doc.pageCount() <= MAX_PAGES:
            break

    pages = doc.pageCount()
    if pages > MAX_PAGES:
        raise ValueError(f"{pdf_path.name} has {pages} pages (exceeds strict {MAX_PAGES}-page limit). Use --exclude to remove blocks.")

    doc.print(printer)
    return pages


def validate_bullet_formula(block_id: str, lang: str, text: str) -> None:
    """Verify bullet starts with **Action Verb** and has at least 3 bold segments (Verb, Metric/Achievement, Tools)."""
    assert text.startswith("**"), f"[{block_id}:{lang}] must start with **Action Verb**: {text[:40]}..."
    bolds = re.findall(r"\*\*(.+?)\*\*", text)
    assert len(bolds) >= 3, (
        f"[{block_id}:{lang}] must have >= 3 bold segments "
        f"(1: Action Verb, 2: Metric/Achievement/Promotion/Recognition, 3: Tools). Found {len(bolds)} in: {text}"
    )


def list_blocks(data: dict) -> None:
    for sec in ("headlines", "summaries", "skills", "career_break", "projects", "education", "certifications"):
        print(f"\n[{sec.upper()}]")
        for b in data[sec]:
            print(f"  {b['id']:22s} tags: {', '.join(b['tags'])}")
    print("\n[EXPERIENCE]")
    for c in data["companies"]:
        print(f"  Company: {c['meta']['company']} ({c['id']})")
        for b in c["bullets"]:
            print(f"    {b['id']:20s} tags: {', '.join(b['tags'])}")


def build_one(data: dict, role: str, lang: str, out_dir: Path, include_ids: set | None = None, exclude_ids: set | None = None, custom_title: str | None = None, company: str | None = None) -> tuple[Path, Path, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    res = select_resume(data, role, lang, include_ids, exclude_ids, custom_title)
    role_part = ROLE_FILENAMES.get(role, role.upper())
    comp_part = f"_{re.sub(r'[^A-Za-z0-9]+', '_', company).strip('_')}" if company else ""
    stem = f"Resume_Lazaro_Bonifacio_{role_part}{comp_part}_{lang.upper()}"
    md_path = out_dir / f"{stem}.md"
    pdf_path = out_dir / f"{stem}.pdf"

    md_path.write_text(render_markdown(res), encoding="utf-8")
    pages = write_pdf(res, pdf_path)
    return md_path, pdf_path, pages


def run_check(master_path: Path) -> None:
    data = parse_master(master_path)
    assert data["profile"].get("name") == "Lazaro Bonifacio", "Missing profile name"
    assert len(data["career_break"]) >= 1, "Missing Career Break section"

    # Check bullet formula across all experience, career break, and project blocks
    for comp in data["companies"]:
        for b in comp["bullets"]:
            for l in LANGS:
                validate_bullet_formula(b["id"], l, b["fields"][l])
    for b in data["career_break"]:
        for l in LANGS:
            validate_bullet_formula(b["id"], l, b["fields"][l])
    for b in data["projects"]:
        for l in LANGS:
            validate_bullet_formula(b["id"], l, b["fields"][l])

    tmp_dir = Path("/tmp/cvs_check")
    for r in ROLES:
        for l in LANGS:
            _, pdf_p, pages = build_one(data, r, l, tmp_dir)
            assert 1 <= pages <= MAX_PAGES, f"{pdf_p.name} has {pages} pages (max {MAX_PAGES})"
    print(f"OK: verified bullet formula, career break section, and <={MAX_PAGES} pages across {len(ROLES)*len(LANGS)} variants.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build Harvard resumes (.md + .pdf) from master.md")
    ap.add_argument("--master", default="master.md", help="Path to master markdown file")
    ap.add_argument("--role", choices=ROLES, default="platform", help="Target role")
    ap.add_argument("--lang", choices=LANGS, default="en_us", help="Target language")
    ap.add_argument("--blocks", help="Comma-separated block IDs to force-include (e.g. proj-asus)")
    ap.add_argument("--exclude", help="Comma-separated block IDs to exclude (e.g. cb-cloud-transition,bd-infra)")
    ap.add_argument("--title", help="Custom role title override in the header")
    ap.add_argument("--company", help="Target company name suffix for output files")
    ap.add_argument("--out", default="dist", help="Output directory (default: dist)")
    ap.add_argument("--all", action="store_true", help="Build all roles x languages")
    ap.add_argument("--list", action="store_true", help="List all available Lego blocks and tags")
    ap.add_argument("--check", action="store_true", help="Run self-check assertions")
    args = ap.parse_args()

    master_path = Path(args.master)
    if args.check:
        run_check(master_path)
        return

    data = parse_master(master_path)
    if args.list:
        list_blocks(data)
        return

    inc = {x.strip() for x in args.blocks.split(",") if x.strip()} if args.blocks else None
    exc = {x.strip() for x in args.exclude.split(",") if x.strip()} if args.exclude else set()
    out_dir = Path(args.out)

    if args.all:
        for r in ROLES:
            for l in LANGS:
                md_p, pdf_p, pages = build_one(data, r, l, out_dir, inc, exc)
                print(f"Built ({pages}p): {md_p} & {pdf_p}")
    else:
        md_p, pdf_p, pages = build_one(data, args.role, args.lang, out_dir, inc, exc, args.title, args.company)
        print(f"Built ({pages}p): {md_p} & {pdf_p}")


if __name__ == "__main__":
    main()
