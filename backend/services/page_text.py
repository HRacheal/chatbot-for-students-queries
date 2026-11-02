"""Visible text of an HTML page, processed in memory.

Used by the live website retriever (``services/web_access.py``) and by the optional
staging tool (``tools/knowledge_sources.py``). Page text is untrusted data.
"""

import datetime
import re
from html.parser import HTMLParser


class PageTextParser(HTMLParser):
    """Visible text of a web page, without scripts, menus, headers, footers and forms.

    If the page has a ``<main>``/``<article>`` element with real content, only that is
    kept, so navigation repeated on every page does not end up in the source text.
    """

    SKIP = {"script", "style", "noscript", "template", "svg", "nav", "header", "footer", "form",
            "aside", "iframe", "button", "select", "textarea", "head"}
    BLOCK = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section",
             "article", "main", "dd", "dt", "blockquote", "pre", "figcaption", "caption"}
    VOID = {"br", "hr", "img", "meta", "link", "input", "source", "wbr", "area", "base", "col", "embed"}
    MAIN = {"main", "article"}
    DATE_META = ("article:modified_time", "og:updated_time", "article:published_time", "dc.date", "date")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.main_parts, self.title_parts = [], [], []
        self.meta = {}
        self.canonical = ""
        self._skip_tag, self._skip_depth = None, 0
        self._main_tag, self._main_depth = None, 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key in self.DATE_META and attrs.get("content"):
                self.meta.setdefault(key, attrs["content"])
            return
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split() and not self.canonical:
            self.canonical = (attrs.get("href") or "").strip()
            return
        if tag == "title":
            self._in_title = True
            return
        if tag in ("br", "hr"):
            self._newline()
        if tag in self.VOID:
            return
        if self._skip_tag:
            self._skip_depth += tag == self._skip_tag
            return
        if tag in self.SKIP:
            self._skip_tag, self._skip_depth = tag, 1
            return
        if self._main_tag:
            self._main_depth += tag == self._main_tag
        elif tag in self.MAIN or attrs.get("role") == "main":
            self._main_tag, self._main_depth = tag, 1
        if tag in self.BLOCK:
            self._newline()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            return
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if not self._skip_depth:
                    self._skip_tag = None
            return
        if self._main_tag and tag == self._main_tag:
            self._main_depth -= 1
            if not self._main_depth:
                self._main_tag = None
        if tag in self.BLOCK:
            self._newline()

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        elif not self._skip_tag:
            self.parts.append(data)
            if self._main_tag:
                self.main_parts.append(data)

    def _newline(self):
        self.parts.append("\n")
        if self._main_tag:
            self.main_parts.append("\n")

    @staticmethod
    def _clean(parts):
        lines, previous = [], None
        for line in "".join(parts).splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if line and line != previous:
                lines.append(line)
            previous = line or previous
        return "\n".join(lines)

    def result(self):
        main = self._clean(self.main_parts)
        text = main if len(main) >= 200 else self._clean(self.parts)
        date = next((self.meta[k] for k in self.DATE_META if k in self.meta), "")
        return text, re.sub(r"\s+", " ", "".join(self.title_parts)).strip(), _iso_date(date)


def _iso_date(value):
    """'2026-03-14T08:00:00+03:00' or 'D:20260314...' -> '2026-03-14'; anything else -> ''."""
    match = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", value or "")
    if not match:
        return ""
    try:
        return datetime.date(*map(int, match.groups())).isoformat()
    except ValueError:
        return ""


def _parse(data):
    parser = PageTextParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    parser.close()
    return parser


def extract_html(data):
    return _parse(data).result()


def extract_html_details(data):
    """``extract_html`` plus the page's declared canonical URL (``<link rel="canonical">``, may be '')."""
    parser = _parse(data)
    text, title, date = parser.result()
    return {"text": text, "title": title, "date": date, "canonical": parser.canonical}
