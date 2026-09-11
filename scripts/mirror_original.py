#!/usr/bin/env python3
"""Create a bounded static mirror of the public Africa Unification Summit site."""

from __future__ import annotations

import concurrent.futures
import html
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ORIGIN = "https://africaunificationsummit.org"
HOSTS = {"africaunificationsummit.org", "www.africaunificationsummit.org"}
ROOT = Path(__file__).resolve().parents[1]
ABOUT_TEMPLATE = ROOT / "templates" / "about-page.html"
PAGES = {
    "": "/",
    "about-us": "/about-us/",
    "event-schedule": "/event-schedule/",
    "organizer": "/organizer/",
    "speakers": "/speakers/",
    "about-the-host": "/about-the-host/",
    "blog": "/blog/",
    "contact": "/contact/",
}
ASSET_EXTENSIONS = {
    ".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm",
}
URL_PATTERN = re.compile(
    r"(?:src|href|data-src|data-bg|data-lazy-src|poster)\s*=\s*['\"]([^'\"]+)['\"]"
    r"|(?:srcset|data-srcset)\s*=\s*['\"]([^'\"]+)['\"]"
    r"|url\(\s*['\"]?([^)'\"\s]+)",
    re.IGNORECASE,
)


def request(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SummitStaticMirror/1.0)",
            "Accept": "*/*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Unable to download {url}: {last_error}")


def clean_url(raw: str, base: str) -> str | None:
    raw = html.unescape(raw.strip()).replace("\\/", "/")
    if not raw or raw.startswith(("data:", "mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urllib.parse.urljoin(base, raw)
    parsed = urllib.parse.urlsplit(absolute)
    if parsed.hostname not in HOSTS:
        return None
    path = urllib.parse.unquote(parsed.path)
    suffix = Path(path).suffix.lower()
    if not (path.startswith(("/wp-content/", "/wp-includes/")) or suffix in ASSET_EXTENSIONS):
        return None
    return urllib.parse.urlunsplit(("https", "africaunificationsummit.org", parsed.path, parsed.query, ""))


def extract_assets(text: str, base: str) -> set[str]:
    found: set[str] = set()
    for match in URL_PATTERN.finditer(text):
        value = next((part for part in match.groups() if part), "")
        candidates = [
            parts[0]
            for chunk in value.split(",")
            if (parts := chunk.strip().split())
        ]
        for candidate in candidates:
            cleaned = clean_url(candidate, base)
            if cleaned:
                found.add(cleaned)
    return found


def asset_path(url: str) -> Path:
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip("/")
    return ROOT / path


def relative_prefix(output: Path) -> str:
    return os.path.relpath(ROOT, output.parent).replace(os.sep, "/").rstrip("/") + "/"


def make_lazy_images_eager(text: str) -> str:
    def update_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        lazy = re.search(r"\sdata-(?:lazy-)?src=['\"]([^'\"]+)['\"]", tag, re.I)
        if lazy:
            if re.search(r"\ssrc=['\"][^'\"]*['\"]", tag, re.I):
                tag = re.sub(r"\ssrc=['\"][^'\"]*['\"]", f' src="{lazy.group(1)}"', tag, count=1, flags=re.I)
            else:
                tag = tag[:-1] + f' src="{lazy.group(1)}">'
        lazyset = re.search(r"\sdata-srcset=['\"]([^'\"]+)['\"]", tag, re.I)
        if lazyset:
            if re.search(r"\ssrcset=['\"][^'\"]*['\"]", tag, re.I):
                tag = re.sub(r"\ssrcset=['\"][^'\"]*['\"]", f' srcset="{lazyset.group(1)}"', tag, count=1, flags=re.I)
            else:
                tag = tag[:-1] + f' srcset="{lazyset.group(1)}">'
        return tag

    return re.sub(r"<(?:img|source)\b[^>]*>", update_tag, text, flags=re.I)


def rewrite(text: str, output: Path) -> str:
    prefix = relative_prefix(output)
    text = make_lazy_images_eager(text)
    for origin in (
        "https://africaunificationsummit.org/",
        "http://africaunificationsummit.org/",
        "https://www.africaunificationsummit.org/",
        "http://www.africaunificationsummit.org/",
        "//africaunificationsummit.org/",
        "//www.africaunificationsummit.org/",
    ):
        text = text.replace(origin, prefix)
        text = text.replace(origin.replace("/", "\\/"), prefix.replace("/", "\\/"))
    # Root-relative WordPress assets must also work beneath a GitHub project path.
    text = re.sub(
        r"(?P<q>['\"])/(?!/)(?P<path>(?:wp-content|wp-includes)/)",
        lambda m: f"{m.group('q')}{prefix}{m.group('path')}",
        text,
        flags=re.I,
    )
    return text


def enhance_about_page(text: str) -> str:
    """Replace the original unformatted About page body with the maintained design."""
    start_marker = '<div data-elementor-type="wp-page" data-elementor-id="68"'
    end_marker = '<div class="ekit-template-content-markup ekit-template-content-footer'
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("Unable to locate the About page content markers")
    stylesheets = (
        '<link rel="stylesheet" href="../assets/about-shell.css">'
        '<link rel="stylesheet" href="../assets/about-page.css">'
    )
    if "../assets/about-shell.css" not in text:
        text = text.replace("</head>", f"{stylesheets}</head>", 1)
    replacement = ABOUT_TEMPLATE.read_text(encoding="utf-8").strip()
    return text[:start] + replacement + text[end:]


def page_output(slug: str) -> Path:
    return ROOT / "index.html" if not slug else ROOT / slug / "index.html"


def download_asset(url: str) -> tuple[str, bytes, str]:
    data = request(url)
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    text = ""
    if suffix in {".css", ".js", ".mjs", ".svg"}:
        text = data.decode("utf-8", errors="replace")
    return url, data, text


def main() -> None:
    queued: set[str] = set()
    page_documents: list[tuple[Path, str]] = []

    for slug, path in PAGES.items():
        url = urllib.parse.urljoin(ORIGIN, path)
        source = request(url).decode("utf-8", errors="replace")
        output = page_output(slug)
        page_documents.append((output, source))
        queued.update(extract_assets(source, url))
        print(f"Fetched page: {path}")

    downloaded: set[str] = set()
    while queued - downloaded:
        batch = sorted(queued - downloaded)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(download_asset, url): url for url in batch}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    final_url, data, text = future.result()
                except Exception as exc:
                    print(f"Warning: {exc}")
                    downloaded.add(url)
                    continue
                output = asset_path(final_url)
                output.parent.mkdir(parents=True, exist_ok=True)
                if text:
                    queued.update(extract_assets(text, final_url))
                    output.write_text(rewrite(text, output), encoding="utf-8")
                else:
                    output.write_bytes(data)
                downloaded.add(url)
        print(f"Downloaded {len(downloaded)} assets")

    for output, source in page_documents:
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = rewrite(source, output)
        if output == page_output("about-us"):
            rendered = enhance_about_page(rendered)
        output.write_text(rendered, encoding="utf-8")

    print(f"Static mirror ready: {len(page_documents)} pages, {len(downloaded)} assets")


if __name__ == "__main__":
    main()
