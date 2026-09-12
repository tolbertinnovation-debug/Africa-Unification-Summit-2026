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
SCHEDULE_TEMPLATE = ROOT / "templates" / "schedule-content.html"
STANDARD_TEMPLATES = {
    slug: ROOT / "templates" / f"{slug}-content.html"
    for slug in ("organizer", "speakers", "about-the-host", "blog", "contact")
}
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
    """Build a clean standalone About page without WordPress layout dependencies."""
    replacement = ABOUT_TEMPLATE.read_text(encoding="utf-8").strip()
    return f'''<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>About Us – Africa Unification Summit</title>
  <meta name="description" content="Learn about the Africa Unification Summit 2026, its mission, programme, focus sectors, partners, and opportunities to participate.">
  <link rel="icon" href="../wp-content/uploads/2026/04/cropped-Africa-Unification-Summit-32x32.png" sizes="32x32">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/about-shell.css">
  <link rel="stylesheet" href="../assets/about-page.css">
  <link rel="stylesheet" href="../assets/responsive-polish.css?v=20260912-3">
</head>
<body class="aus-about-ready">
{replacement}
</body>
</html>
'''


def enhance_schedule_page(text: str) -> str:
    """Build a branded standalone schedule page using the shared summit shell."""
    shell = ABOUT_TEMPLATE.read_text(encoding="utf-8").strip()
    schedule = SCHEDULE_TEMPLATE.read_text(encoding="utf-8").strip()
    shell = re.sub(r'<main id="main-content">.*?</main>', schedule, shell, count=1, flags=re.S)
    shell = shell.replace('<a class="is-current" href="../about-us/">About Us</a>', '<a href="../about-us/">About Us</a>', 1)
    shell = shell.replace('<a href="../event-schedule/">Schedule</a>', '<a class="is-current" href="../event-schedule/">Schedule</a>', 1)
    return f'''<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Event Schedule – Africa Unification Summit</title>
  <meta name="description" content="Explore the five-day programme for the Africa Unification Summit 2026 in Monrovia, Liberia, November 16–20, 2026.">
  <link rel="icon" href="../wp-content/uploads/2026/04/cropped-Africa-Unification-Summit-32x32.png" sizes="32x32">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/about-shell.css">
  <link rel="stylesheet" href="../assets/schedule-page.css">
  <link rel="stylesheet" href="../assets/responsive-polish.css?v=20260912-3">
</head>
<body class="aus-about-ready">
{shell}
</body>
</html>
'''


def enhance_standard_page(slug: str) -> str:
    """Build a branded standalone content page using the shared summit shell."""
    shell = ABOUT_TEMPLATE.read_text(encoding="utf-8").strip()
    content = STANDARD_TEMPLATES[slug].read_text(encoding="utf-8").strip()
    shell = re.sub(r'<main id="main-content">.*?</main>', content, shell, count=1, flags=re.S)
    shell = shell.replace(' class="is-current"', "")
    labels = {
        "organizer": "Organizer",
        "speakers": "Speakers",
        "about-the-host": "Host Country",
        "contact": "Contact",
    }
    label = labels.get(slug)
    if label:
        shell = shell.replace(f'<a href="../{slug}/">{label}</a>', f'<a class="is-current" href="../{slug}/">{label}</a>', 1)
    titles = {
        "organizer": "Organizer",
        "speakers": "Summit Speakers",
        "about-the-host": "Host Country",
        "blog": "News & Insights",
        "contact": "Contact",
    }
    return f'''<!doctype html>
<html lang="en-US"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{titles[slug]} – Africa Unification Summit</title>
  <meta name="description" content="Official Africa Unification Summit 2026 information for {titles[slug].lower()}.">
  <link rel="icon" href="../wp-content/uploads/2026/04/cropped-Africa-Unification-Summit-32x32.png" sizes="32x32">
  <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/about-shell.css"><link rel="stylesheet" href="../assets/standard-pages.css"><link rel="stylesheet" href="../assets/responsive-polish.css?v=20260912-3">
</head><body class="aus-about-ready">{shell}</body></html>'''


def add_body_class(text: str, class_name: str) -> str:
    """Add a class to the first body tag while preserving existing attributes."""
    def update(match: re.Match[str]) -> str:
        attrs = match.group(1)
        class_match = re.search(r'class=(["\'])(.*?)\1', attrs, flags=re.I | re.S)
        if class_match:
            classes = class_match.group(2).split()
            if class_name not in classes:
                classes.append(class_name)
            quoted = f'class={class_match.group(1)}{" ".join(classes)}{class_match.group(1)}'
            attrs = attrs[:class_match.start()] + quoted + attrs[class_match.end():]
        else:
            attrs = f' class="{class_name}"' + attrs
        return f'<body{attrs}>'

    return re.sub(r'<body([^>]*)>', update, text, count=1, flags=re.I)


def enhance_shared_brand(text: str, slug: str) -> str:
    """Apply the homepage-style summit header and footer to a mirrored page."""
    shell = ABOUT_TEMPLATE.read_text(encoding="utf-8")
    header_match = re.search(r'<header class="aus-site-header">.*?</header>', shell, flags=re.S)
    footer_match = re.search(r'<footer class="aus-site-footer">.*?</footer>', shell, flags=re.S)
    if not header_match or not footer_match:
        raise RuntimeError("Shared summit header or footer is missing from the template")

    prefix = "./" if not slug else "../"
    header = header_match.group(0).replace("../", prefix)
    footer = footer_match.group(0).replace("../", prefix)
    header = header.replace(' class="is-current"', "")
    active = {
        "": (prefix, "Home"),
        "organizer": (f"{prefix}organizer/", "Organizer"),
        "speakers": (f"{prefix}speakers/", "Speakers"),
        "about-the-host": (f"{prefix}about-the-host/", "Host Country"),
        "blog": (f"{prefix}blog/", "Blog"),
        "contact": (f"{prefix}contact/", "Contact"),
    }.get(slug)
    if active:
        href, label = active
        header = header.replace(f'<a href="{href}">{label}</a>', f'<a class="is-current" href="{href}">{label}</a>', 1)

    stylesheet = f'''\n  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{prefix}assets/about-shell.css">
  <link rel="stylesheet" href="{prefix}assets/responsive-polish.css?v=20260912-3">'''
    text = text.replace("</head>", f"{stylesheet}\n</head>", 1)
    text = add_body_class(text, "aus-global-shell")
    # Correct visible source copy so the published mirror reads professionally.
    corrections = {
        "ECOWAS Vision 20250": "ECOWAS Vision 2050",
        "Inrastructure and Financing Needs": "Infrastructure and Financing Needs",
        "This is a dynamic a dynamic platform": "This is a dynamic platform",
        "Event Partners &amp; <span>Sponsers</span>": "Event Partners &amp; <span>Sponsors</span>",
        "Checkout Recent <span>Blogs</span>": "Explore Recent <span>Updates</span>",
    }
    for old, new in corrections.items():
        text = text.replace(old, new)
    # Replace inactive source buttons with useful destinations already in the site.
    for label, destination in (
        ("LEARN MORE..", f"{prefix}event-schedule/"),
        ("MORE REVIEWS", f"{prefix}about-us/"),
    ):
        text = re.sub(
            rf'(<a\b[^>]*\bhref=)["\']#["\'](?=[^>]*>(?:(?!</a>).)*<span\b[^>]*>{re.escape(label)}</span>)',
            rf'\1"{destination}"',
            text,
            flags=re.I | re.S,
        )
    text = re.sub(r'(<body[^>]*>)', rf'\1\n{header}', text, count=1, flags=re.I)
    return text.replace("</body>", f"{footer}\n</body>", 1)


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
    page_documents: list[tuple[str, Path, str]] = []

    for slug, path in PAGES.items():
        url = urllib.parse.urljoin(ORIGIN, path)
        source = request(url).decode("utf-8", errors="replace")
        output = page_output(slug)
        page_documents.append((slug, output, source))
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

    for slug, output, source in page_documents:
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = rewrite(source, output)
        if output == page_output("about-us"):
            rendered = enhance_about_page(rendered)
        elif output == page_output("event-schedule"):
            rendered = enhance_schedule_page(rendered)
        elif slug in STANDARD_TEMPLATES:
            rendered = enhance_standard_page(slug)
        else:
            rendered = enhance_shared_brand(rendered, slug)
        output.write_text(rendered, encoding="utf-8")

    print(f"Static mirror ready: {len(page_documents)} pages, {len(downloaded)} assets")


if __name__ == "__main__":
    main()
