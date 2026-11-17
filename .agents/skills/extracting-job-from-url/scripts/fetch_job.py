#!/usr/bin/env python3
"""Extract job description metadata and text from a job posting URL."""
import html
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "svg", "noscript", "head", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.json_ld: list[str] = []
        self.next_data: list[str] = []
        self._script_type = ""
        self._script_id = ""
        self._in_script = False
        self._script_buf: list[str] = []
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = attr_map.get("property") or attr_map.get("name") or ""
            val = attr_map.get("content", "")
            if key and val:
                self.meta[key.lower()] = val
        elif tag == "script":
            self._in_script = True
            self._script_type = attr_map.get("type", "").lower()
            self._script_id = attr_map.get("id", "")
            self._script_buf = []

        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"}:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            raw = "".join(self._script_buf).strip()
            if self._script_type == "application/ld+json" and raw:
                self.json_ld.append(raw)
            elif self._script_id == "__NEXT_DATA__" and raw:
                self.next_data.append(raw)
            elif "window.__appData" in raw:
                self.next_data.append(raw)
            self._in_script = False
            self._script_type = ""
            self._script_id = ""
            self._script_buf = []

        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_script:
            self._script_buf.append(data)
        if self._skip_depth == 0:
            cleaned = re.sub(r"[ \t]+", " ", data)
            if cleaned.strip():
                self.chunks.append(cleaned)


def strip_html_tags(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</h[1-6]>", "\n", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_job_posting_ld(blocks: list[str]) -> list[dict]:
    found = []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                if item.get("@type") == "JobPosting":
                    found.append(item)
                elif "@graph" in item and isinstance(item["@graph"], list):
                    found.extend(x for x in item["@graph"] if isinstance(x, dict) and x.get("@type") == "JobPosting")
    return found


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 fetch_job.py <url>")
    url = sys.argv[1].strip()

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            final_url = resp.geturl()
            status = resp.status
            raw_html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"STATUS: HTTP_ERROR ({e.code})")
        print(f"URL: {url}")
        print("ACTION_REQUIRED: Fallback to search_web for the job title/company, or ask the user to paste the job description text. NEVER guess requirements from the URL slug.")
        sys.exit(2)
    except Exception as e:
        print(f"STATUS: FETCH_FAILED ({e})")
        print(f"URL: {url}")
        print("ACTION_REQUIRED: Fallback to search_web for the job title/company, or ask the user to paste the job description text. NEVER guess requirements from the URL slug.")
        sys.exit(2)

    parser = TextExtractor()
    parser.feed(raw_html)

    title = parser.title.strip() or parser.meta.get("og:title", "")
    og_desc = parser.meta.get("og:description", "") or parser.meta.get("description", "")
    body_text = re.sub(r"\n{3,}", "\n\n", "".join(parser.chunks)).strip()
    ld_postings = extract_job_posting_ld(parser.json_ld)

    lower_html = raw_html.lower()
    is_authwall = "/authwall" in final_url.lower() or "authwall" in lower_html
    is_captcha = any(m in lower_html for m in ("cf-chl-bypass", "turnstile", "verify you are human", "g-recaptcha", "hcaptcha"))

    if is_captcha or is_authwall:
        reason = "ANTI_BOT_OR_CAPTCHA" if is_captcha else "LOGIN_AUTHWALL"
        print(f"STATUS: BLOCKED ({reason})")
        print(f"FINAL_URL: {final_url}")
        print("ACTION_REQUIRED: Do NOT attempt to bypass login walls or CAPTCHAs. Use search_web to look up the public posting text, or stop and ask the user to paste the job description.")
        sys.exit(3)

    print(f"FINAL_URL: {final_url} (HTTP {status})")
    if title:
        print(f"TITLE: {title}")
    if og_desc:
        print(f"META_DESCRIPTION: {og_desc}")

    if ld_postings:
        print("\n=== STRUCTURED JOB POSTING (JSON-LD) ===")
        for jp in ld_postings:
            print(f"Job Title: {jp.get('title', '')}")
            org = jp.get("hiringOrganization", {})
            if isinstance(org, dict):
                print(f"Company: {org.get('name', '')}")
            print(f"Employment Type: {jp.get('employmentType', '')}")
            desc = strip_html_tags(str(jp.get("description", "")))
            print(f"\n{desc}\n")

    if parser.next_data and not ld_postings:
        print("\n=== EMBEDDED APP DATA (SPA) ===")
        for nd in parser.next_data:
            print(nd[:8000])

    if len(body_text) >= 200:
        print("\n=== VISIBLE PAGE TEXT ===")
        print(body_text[:12000])
    elif not ld_postings and not parser.next_data:
        print("STATUS: EMPTY_SPA_SHELL (fewer than 200 chars of visible text and no structured job data)")
        print("ACTION_REQUIRED: Try search_web with the company and job title/slug. If full requirements are not found, stop and ask the user to paste the job description text. NEVER guess requirements from the URL slug.")
        sys.exit(4)


if __name__ == "__main__":
    main()
