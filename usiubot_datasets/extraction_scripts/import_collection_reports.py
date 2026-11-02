"""Split the 2026-11-01 web collection reports into one snapshot file per page.

The pages were read on 2026-11-01 with Claude's WebFetch tool (user agent Claude-User, which the
usiu.ac.ke robots.txt allows: "AI assistants and AI search: fetch pages when someone asks about USIU").
Each fetch was made by a fetching agent that returned the page's main content as markdown. Those
reports are kept unchanged in web_sources/raw_collection_reports/. This script cuts them into
per-page snapshots (web_sources/snapshots/<page_id>.md) and writes web_sources/collection_manifest.json.

Limitations recorded in every manifest entry:
  * the text is WebFetch's HTML-to-markdown conversion as transcribed by the fetching agent; it is
    not a byte copy of the HTML and table layout may have been rebuilt from cell order;
  * site-wide navigation, footers and cookie banners were left out on purpose.

Run:  backend/.venv/Scripts/python.exe usiubot_datasets/extraction_scripts/import_collection_reports.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import web_config as W  # noqa: E402

DATASETS = Path(__file__).resolve().parents[1]
WEB = DATASETS / "web_sources"
RAW = WEB / "raw_collection_reports"
SNAP = WEB / "snapshots"

URL_HEAD = re.compile(r"^#{1,3}\s+(?:\d+\.\s+)?(https?://\S+?)\s*$")
END_MARK = re.compile(r"^#{0,3}\s*\**(Observations|Notes|Summary|Discrepancies|Final URLs|Shared contact|Correction on|"
                      r"Unsure or flagged|Links in main content|Method notes)\b", re.I)


def page_id(url):
    path = re.sub(r"^https?://[^/]+", "", url).strip("/")
    host = re.match(r"https?://([^/]+)", url).group(1).replace("www.", "")
    base = path.replace("/", "__") or "home"
    return base if host == "usiu.ac.ke" else f"{host}__{base}"


def blocks(text):
    """Yield (url, block_text) for every '## <url>' section of a report."""
    lines = text.split("\n")
    cur, buf = None, []
    for ln in lines + ["## https://END"]:
        m = URL_HEAD.match(ln.strip())
        if m:
            if cur:
                yield cur, "\n".join(buf)
            cur, buf = m.group(1), []
            continue
        if cur and END_MARK.match(ln.strip()) and not ln.startswith("###"):
            # A report-level note after the last page: stop this block here.
            if "Links in main content" in ln:
                buf.append(ln)  # links belong to the page
                continue
            yield cur, "\n".join(buf)
            cur, buf = None, []
            continue
        if cur:
            buf.append(ln)


def clean_block(b):
    b = b.strip()
    b = re.sub(r"\n-{3,}\s*$", "", b).strip()
    return b + "\n"


def main():
    SNAP.mkdir(parents=True, exist_ok=True)
    manifest = {}
    attempts = []
    for rep in sorted(RAW.glob("*.md")):
        text = rep.read_text(encoding="utf-8")
        found = list(blocks(text))
        if rep.name in W.REPORT_SPECIAL:
            found = W.REPORT_SPECIAL[rep.name](text)
        for url, b in found:
            if url == "https://END":
                continue
            url = url.rstrip(")").rstrip(".")
            head = b[:400]
            failed = bool(re.search(r"FAILED|ECONNREFUSED", head)) and "200" not in head.split("\n")[0:3].__str__()
            attempts.append({"url": url, "report": rep.name, "outcome": "failed" if failed else "ok",
                             "detail": (re.search(r"(ECONNREFUSED[^\n]*|HTTP[^\n]{0,80})", head) or [""])[0]})
            if failed:
                continue
            if url in W.SKIP_BLOCKS.get(rep.name, ()):
                continue
            pid = page_id(url)
            body = clean_block(b)
            prev = manifest.get(pid)
            if prev and W.PREFERRED_REPORT.get(pid) not in (None, rep.name):
                continue
            manifest[pid] = {"page_id": pid, "url": url, "report": rep.name, "body": body}

    out = {}
    for pid, m in sorted(manifest.items()):
        info = W.page_info(m["url"])
        title = (re.search(r"(?:Page title[^:]*:|H1:)\s*\**\s*[\"`“]?([^\"`”\n]+)", m["body"]) or [None, ""])[1].strip()
        header = (f"<!-- snapshot of {m['url']} | collected 2026-11-01 via Claude WebFetch (Claude-User) | "
                  f"source report: raw_collection_reports/{m['report']} -->\n\n")
        text = header + m["body"]
        path = SNAP / f"{pid}.md"
        path.write_text(text, encoding="utf-8", newline="\n")
        out[pid] = {
            "page_id": pid,
            "url": m["url"],
            "final_url": m["url"],
            "title": title or info.get("title", ""),
            "source_type": info.get("source_type", "official" if "usiu.ac.ke" in m["url"] else "external"),
            "publisher": info.get("publisher", "USIU-Africa" if "usiu.ac.ke" in m["url"] else ""),
            "category_id": info.get("category", "01"),
            "http_status": 200,
            "collected_at": "2026-11-01",
            "last_checked": "2026-11-01",
            "publication_date": "Publication date not stated",
            "sitemap_lastmod": W.SITEMAP_LASTMOD.get(m["url"], ""),
            "collection_method": "Claude WebFetch (user agent Claude-User, allowed by usiu.ac.ke robots.txt) on the "
                                 "user's request; main content transcribed to markdown by the fetching agent",
            "content_fidelity": info.get("fidelity", "verbatim main content (markdown conversion)"),
            "snapshot_file": f"web_sources/snapshots/{pid}.md",
            "snapshot_sha256": hashlib.sha256(m["body"].encode("utf-8")).hexdigest(),
            "source_report": f"web_sources/raw_collection_reports/{m['report']}",
            "change_status": "new",
            "previous_versions": [],
            "review_status": "draft",
        }
    for f in W.FAILED_ONLY:
        out.setdefault(f["page_id"], dict(f, collected_at="", last_checked="2026-11-01"))
    (WEB / "collection_manifest.json").write_text(json.dumps({"pages": out, "fetch_attempts": attempts}, indent=1,
                                                             ensure_ascii=False), encoding="utf-8")
    ok = [p for p in out.values() if p.get("http_status") == 200]
    print(f"snapshots: {len(ok)}  not collected: {len(out) - len(ok)}  attempts: {len(attempts)}")


if __name__ == "__main__":
    main()
