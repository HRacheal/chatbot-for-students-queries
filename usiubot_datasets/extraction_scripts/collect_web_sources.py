"""Reproducible, robots.txt-respecting collector for the USIUBOT web sources (standard library only).

What it does
  * identifies itself honestly (User-Agent "USIUBOT-dataset-collector/1.0"); it never pretends to be a browser
    or another bot;
  * reads each host's robots.txt first and skips every URL the rules do not allow for this user agent;
    at the time of writing usiu.ac.ke's robots.txt ends with "User-agent: * / Disallow: /", so this script
    reports those pages as "blocked by robots.txt" and does NOT fetch them;
  * only fetches URLs on the allow-list (the manifest's URLs on usiu.ac.ke and the listed external bodies),
    never login pages, student portals or web forms (see BLOCKED_PATTERNS);
  * sends conditional requests (If-None-Match / If-Modified-Since) so unchanged pages are not downloaded again;
  * keeps the URL, final URL, HTTP status and dates for every attempt; records inaccessible pages and moves on;
  * hashes the extracted text and compares it with the current snapshot: unchanged pages keep their snapshot,
    changed pages get a new snapshot, the old one is moved to web_sources/history/<page_id>/ and the page is
    marked "changed_pending_review";
  * never approves anything (review_status stays "draft").

Pages that robots.txt blocks for automated collectors can still be added by a person: open the page in a
browser, save it as HTML, and run   --import-html <folder>   (the page URL is read from the saved file's
canonical link, or given in <folder>/urls.json as {"file.html": "https://..."}).

Usage (Windows PowerShell, from the project root):
  .\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\collect_web_sources.py --check-robots
  .\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\collect_web_sources.py --fetch
  .\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\collect_web_sources.py --import-html C:\\path\\to\\saved_pages
Then run build_all.py to rebuild the dataset, and review every page marked changed_pending_review.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

sys.dont_write_bytecode = True
DATASETS = Path(__file__).resolve().parents[1]
WEB = DATASETS / "web_sources"
SNAP = WEB / "snapshots"
HIST = WEB / "history"
MANIFEST = WEB / "collection_manifest.json"
CACHE = WEB / "http_cache.json"
LOG = WEB / "collection_log.jsonl"

USER_AGENT = "USIUBOT-dataset-collector/1.0 (university student-query chatbot dataset; manual review)"
ALLOWED_HOSTS = {"www.usiu.ac.ke", "usiu.ac.ke", "kuccps.net", "www.cue.or.ke", "www.knqa.go.ke"}
BLOCKED_PATTERNS = re.compile(r"itsweb\.|clear\.usiu|/webapp/|/wp-admin|login|signin|portal", re.I)
DEFAULT_DELAY = 5.0
TODAY = date.today().isoformat()


class TextExtractor(HTMLParser):
    """Visible main text: skips script/style/nav/header/footer/form/aside; keeps headings as markdown."""
    SKIP = {"script", "style", "nav", "header", "footer", "form", "aside", "noscript", "svg"}
    BLOCK = {"p", "div", "li", "tr", "br", "section", "article", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.title, self._in_title, self.canonical = [], 0, "", False, ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href", "")
        if tag == "meta" and a.get("property") == "og:url" and not self.canonical:
            self.canonical = a.get("content", "")
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif not self.skip and re.match(r"h[1-6]$", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif not self.skip and tag in self.BLOCK:
            self.out.append("\n")
        elif not self.skip and tag == "td":
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False
        elif not self.skip and (re.match(r"h[1-6]$", tag) or tag == "p"):
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip and data.strip():
            self.out.append(re.sub(r"\s+", " ", data))

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"[ \t]+\n", "\n", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def page_id(url):
    path = re.sub(r"^https?://[^/]+", "", url).strip("/")
    host = urlparse(url).netloc.replace("www.", "")
    base = path.replace("/", "__") or "home"
    return base if host == "usiu.ac.ke" else f"{host}__{base}"


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def log(entry):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


_robots = {}


def robots_for(url):
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(host + "/robots.txt")
        try:
            req = urllib.request.Request(host + "/robots.txt", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", errors="replace").splitlines())
            status = "read"
        except urllib.error.HTTPError as e:
            # RFC 9309: 4xx = no restrictions, 5xx = assume complete disallow
            rp.parse([] if 400 <= e.code < 500 else ["User-agent: *", "Disallow: /"])
            status = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            rp.parse(["User-agent: *", "Disallow: /"])
            status = f"unreachable ({type(e).__name__}); treated as disallow"
        _robots[host] = (rp, status)
    return _robots[host]


def permitted(url):
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        return False, "host not on the allow-list"
    if BLOCKED_PATTERNS.search(url):
        return False, "restricted system (login, portal or form) — never collected"
    rp, status = robots_for(url)
    if not rp.can_fetch(USER_AGENT, url):
        return False, f"blocked by robots.txt ({status})"
    return True, f"allowed by robots.txt ({status})"


def store(manifest, url, title, text, method, final_url=None, http_status=200, headers=None):
    pid = page_id(url)
    entry = manifest["pages"].get(pid, {"page_id": pid, "url": url, "previous_versions": [], "review_status": "draft"})
    new_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    entry.update({"final_url": final_url or url, "http_status": http_status, "last_checked": TODAY})
    if entry.get("snapshot_sha256") == new_hash:
        entry["change_status"] = "unchanged"
    else:
        old = SNAP / f"{pid}.md"
        if old.exists():
            dest = HIST / pid
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, dest / f"{entry.get('collected_at') or 'unknown'}_{(entry.get('snapshot_sha256') or '')[:12]}.md")
            entry["previous_versions"] = entry.get("previous_versions", []) + [{
                "collected_at": entry.get("collected_at"), "snapshot_sha256": entry.get("snapshot_sha256"),
                "collection_method": entry.get("collection_method"),
                "history_file": f"web_sources/history/{pid}/" + dest.name}]
        header = f"<!-- snapshot of {url} | collected {TODAY} via {method} -->\n\n"
        SNAP.mkdir(parents=True, exist_ok=True)
        old.write_text(header + (f"# {title}\n\n" if title else "") + text + "\n", encoding="utf-8", newline="\n")
        entry.update({"title": title, "collected_at": TODAY, "snapshot_sha256": new_hash, "collection_method": method,
                      "snapshot_file": f"web_sources/snapshots/{pid}.md",
                      "content_fidelity": "visible text extracted by html.parser (navigation, header, footer, forms "
                                          "removed); not a byte copy",
                      "change_status": "changed_pending_review" if entry.get("previous_versions") else "new",
                      "publication_date": entry.get("publication_date") or "Publication date not stated",
                      "review_status": "draft"})
    if headers:
        entry["http_headers"] = {k: headers.get(k) for k in ("ETag", "Last-Modified", "Content-Type") if headers.get(k)}
    manifest["pages"][pid] = entry
    return entry["change_status"]


def fetch_all(manifest, urls, delay):
    cache = load(CACHE, {})
    last = {}
    for url in urls:
        ok, why = permitted(url)
        rec = {"url": url, "checked_at": TODAY, "user_agent": USER_AGENT, "robots": why}
        if not ok:
            rec["outcome"] = "not fetched: " + why
            log(rec)
            print(f"SKIP  {url}  — {why}")
            continue
        host = urlparse(url).netloc
        rp, _ = robots_for(url)
        wait = max(delay, float(rp.crawl_delay(USER_AGENT) or 0))
        if host in last:
            time.sleep(max(0.0, wait - (time.time() - last[host])))
        headers = {"User-Agent": USER_AGENT}
        c = cache.get(url, {})
        if c.get("etag"):
            headers["If-None-Match"] = c["etag"]
        if c.get("last_modified"):
            headers["If-Modified-Since"] = c["last_modified"]
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                body = r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")
                ex = TextExtractor()
                ex.feed(body)
                status = store(manifest, url, ex.title.strip(), ex.text(), f"collect_web_sources.py ({USER_AGENT})",
                               final_url=r.geturl(), http_status=r.status, headers=r.headers)
                cache[url] = {"etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified")}
                rec.update({"outcome": status, "http_status": r.status, "final_url": r.geturl()})
        except urllib.error.HTTPError as e:
            if e.code == 304:
                pid = page_id(url)
                if pid in manifest["pages"]:
                    manifest["pages"][pid].update({"last_checked": TODAY, "change_status": "unchanged"})
                rec.update({"outcome": "unchanged (HTTP 304)", "http_status": 304})
            else:
                rec.update({"outcome": "inaccessible", "http_status": e.code})
        except Exception as e:  # noqa: BLE001
            rec.update({"outcome": "inaccessible", "error": f"{type(e).__name__}: {e}"[:200]})
        last[host] = time.time()
        log(rec)
        print(f"{rec['outcome']:<24} {url}")
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")


def import_html(manifest, folder):
    folder = Path(folder)
    mapping = load(folder / "urls.json", {})
    for f in sorted(folder.glob("*.htm*")):
        html = f.read_text(encoding="utf-8", errors="replace")
        ex = TextExtractor()
        ex.feed(html)
        url = mapping.get(f.name) or ex.canonical
        if not url or urlparse(url).netloc not in ALLOWED_HOSTS:
            print(f"SKIP  {f.name}: no allowed URL (add it to urls.json)")
            continue
        if BLOCKED_PATTERNS.search(url):
            print(f"SKIP  {f.name}: restricted system")
            continue
        status = store(manifest, url, ex.title.strip(), ex.text(), "saved from a browser by a person; imported with "
                       "collect_web_sources.py --import-html")
        log({"url": url, "checked_at": TODAY, "outcome": status, "method": "import-html", "file": f.name})
        print(f"{status:<24} {url}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check-robots", action="store_true", help="report, per URL, whether robots.txt allows this "
                                                                "collector (fetches robots.txt only)")
    ap.add_argument("--fetch", action="store_true", help="fetch permitted URLs with conditional requests")
    ap.add_argument("--import-html", metavar="DIR", help="import pages a person saved from a browser")
    ap.add_argument("--urls", metavar="FILE", help="text file with one URL per line (default: manifest URLs)")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="seconds between requests to one host")
    a = ap.parse_args()
    manifest = load(MANIFEST, {"pages": {}, "fetch_attempts": []})
    if a.urls:
        urls = [u.strip() for u in Path(a.urls).read_text(encoding="utf-8").splitlines() if u.strip().startswith("http")]
    else:
        urls = sorted({p["url"] for p in manifest["pages"].values() if p.get("url", "").startswith("http")
                       and not p["url"].endswith(".pdf")})
    if a.check_robots:
        rows = []
        for u in urls:
            ok, why = permitted(u)
            rows.append({"url": u, "permitted": ok, "reason": why})
            print(f"{'ALLOWED' if ok else 'BLOCKED':<8} {u}  — {why}")
        (WEB / "robots_check.json").write_text(json.dumps({"checked_at": TODAY, "user_agent": USER_AGENT,
                                                           "results": rows}, indent=1), encoding="utf-8")
        return
    if a.fetch:
        fetch_all(manifest, urls, a.delay)
    if a.import_html:
        import_html(manifest, a.import_html)
    if a.fetch or a.import_html:
        MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        print("Manifest updated. Nothing was approved. Rebuild with build_all.py and review changed pages.")
    if not (a.check_robots or a.fetch or a.import_html):
        ap.print_help()


if __name__ == "__main__":
    main()
