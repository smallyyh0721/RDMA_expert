#!/usr/bin/env python3
"""
RDMA RAG Knowledge Base Builder
================================
Downloads and extracts content from curated sources to build a RAG knowledge base
for RDMA, RoCE, InfiniBand, and general networking topics.

Usage:
    python3 rdma_rag_scraper.py                  # Scrape all sources
    python3 rdma_rag_scraper.py --category blogs  # Scrape only blogs
    python3 rdma_rag_scraper.py --dry-run         # Show what would be scraped
    python3 rdma_rag_scraper.py --retry-failed    # Retry previously failed sources
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
SOURCES_FILE = SCRIPT_DIR / "sources.yaml"
OUTPUT_BASE = SCRIPT_DIR.parent / "RDMA_RAG_Train" / "Scraped_Content"
MANIFEST_FILE = SCRIPT_DIR / "scrape_manifest.json"
LOG_FILE = SCRIPT_DIR / "scraper.log"

REQUEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2  # seconds base
RATE_LIMIT_DELAY = 1.0  # seconds between requests
MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB max per page

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

CATEGORY_DIRS = {
    "manuals": "01_Manuals",
    "specifications": "02_Specifications",
    "product_docs": "03_Product_Docs",
    "troubleshooting": "04_Troubleshooting",
    "kb": "05_Knowledge_Base",
    "blogs": "06_Blogs",
    "web_content": "07_Web_Content",
}

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
log = logging.getLogger("rdma_rag_scraper")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def url_to_filename(url: str, title: str) -> str:
    """Generate a safe filename from title and URL."""
    # Clean title for filename
    safe = re.sub(r'[^\w\s-]', '', title.lower())
    safe = re.sub(r'[\s]+', '_', safe.strip())
    safe = safe[:80]
    # Add short hash to avoid collisions
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{safe}_{url_hash}.md"


def load_sources(path: Path) -> dict:
    """Load the YAML source registry."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_manifest(path: Path) -> dict:
    """Load the scrape manifest (tracks what's been downloaded)."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"scraped": {}, "failed": {}}


def save_manifest(path: Path, manifest: dict):
    """Save the scrape manifest."""
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)


def fetch_url(url: str, session: requests.Session) -> str | None:
    """Fetch URL content with retry logic."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            resp.raise_for_status()
            if len(resp.content) > MAX_CONTENT_SIZE:
                log.warning(f"Content too large ({len(resp.content)} bytes): {url}")
                return resp.text[:MAX_CONTENT_SIZE]
            return resp.text
        except requests.exceptions.RequestException as e:
            wait = RETRY_BACKOFF * attempt
            log.warning(f"Attempt {attempt}/{RETRY_ATTEMPTS} failed for {url}: {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(wait)
    return None


def extract_content(html: str, url: str) -> str:
    """Extract meaningful content from HTML and convert to markdown."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer, header elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                              "aside", "iframe", "noscript"]):
        tag.decompose()

    # Try to find main content area
    content = None
    for selector in [
        soup.find("main"),
        soup.find("article"),
        soup.find(id=re.compile(r"content|main|article|body", re.I)),
        soup.find(class_=re.compile(r"content|main|article|post|entry", re.I)),
        soup.find("div", class_=re.compile(r"markdown|doc|wiki", re.I)),
    ]:
        if selector:
            content = selector
            break

    if content is None:
        content = soup.find("body") or soup

    # Convert to markdown
    markdown_text = md(
        str(content),
        heading_style="ATX",
        bullets="-",
        strip=["img", "svg", "button", "input", "form", "select"],
    )

    # Clean up excessive whitespace
    markdown_text = re.sub(r'\n{4,}', '\n\n\n', markdown_text)
    markdown_text = re.sub(r'[ \t]+$', '', markdown_text, flags=re.MULTILINE)
    markdown_text = markdown_text.strip()

    return markdown_text


def is_raw_text(url: str) -> bool:
    """Check if URL points to raw text (not HTML)."""
    return any(url.endswith(ext) for ext in ['.md', '.txt', '.rst', '.json', '.yaml'])


def format_document(title: str, url: str, tags: list, content: str, category: str) -> str:
    """Format extracted content as a structured markdown document."""
    tag_str = ", ".join(tags) if tags else ""
    return f"""---
title: "{title}"
source: "{url}"
category: {category}
tags: [{tag_str}]
scraped_at: "{datetime.now(timezone.utc).isoformat()}"
---

# {title}

> **Source:** [{url}]({url})
> **Category:** {category}
> **Tags:** {tag_str}

---

{content}
"""


# ---------------------------------------------------------------------------
# Main scraping logic
# ---------------------------------------------------------------------------
def scrape_sources(
    sources: dict,
    categories: list[str] | None = None,
    dry_run: bool = False,
    retry_failed: bool = False,
    force: bool = False,
):
    """Main scraping loop."""
    manifest = load_manifest(MANIFEST_FILE)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    stats = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

    cats_to_process = categories or list(CATEGORY_DIRS.keys())

    for category in cats_to_process:
        if category not in sources:
            log.warning(f"Category '{category}' not found in sources")
            continue

        cat_dir = OUTPUT_BASE / CATEGORY_DIRS[category]
        cat_dir.mkdir(parents=True, exist_ok=True)

        entries = sources[category]
        log.info(f"\n{'='*60}")
        log.info(f"Category: {category} ({len(entries)} sources)")
        log.info(f"{'='*60}")

        for entry in entries:
            url = entry["url"]
            title = entry["title"]
            tags = entry.get("tags", [])
            stats["total"] += 1

            filename = url_to_filename(url, title)
            filepath = cat_dir / filename

            # Skip already downloaded (unless force)
            if not force and url in manifest["scraped"] and filepath.exists():
                if not retry_failed:
                    log.info(f"  [SKIP] {title}")
                    stats["skipped"] += 1
                    continue

            # Skip if not retrying failed and it previously failed
            if retry_failed and url not in manifest.get("failed", {}):
                stats["skipped"] += 1
                continue

            if dry_run:
                log.info(f"  [DRY-RUN] Would download: {title}")
                log.info(f"            URL: {url}")
                log.info(f"            Save to: {filepath}")
                continue

            log.info(f"  [FETCH] {title}")
            log.info(f"          {url}")

            html = fetch_url(url, session)
            if html is None:
                log.error(f"  [FAIL] Could not fetch: {url}")
                manifest.setdefault("failed", {})[url] = {
                    "title": title,
                    "category": category,
                    "error": "fetch_failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                stats["failed"] += 1
                time.sleep(RATE_LIMIT_DELAY)
                continue

            # Extract content
            if is_raw_text(url):
                content = html
            else:
                content = extract_content(html, url)

            if not content or len(content.strip()) < 100:
                log.warning(f"  [WARN] Very little content extracted from: {url}")
                # Still save what we got
                if not content:
                    content = "(No extractable content found at this URL)"

            # Format and save
            document = format_document(title, url, tags, content, category)
            filepath.write_text(document, encoding="utf-8")
            log.info(f"  [SAVED] {filepath.name} ({len(document)} chars)")

            # Update manifest
            manifest["scraped"][url] = {
                "title": title,
                "category": category,
                "filename": str(filepath.relative_to(SCRIPT_DIR.parent)),
                "size": len(document),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            # Remove from failed if it was there
            manifest.get("failed", {}).pop(url, None)

            stats["downloaded"] += 1
            save_manifest(MANIFEST_FILE, manifest)
            time.sleep(RATE_LIMIT_DELAY)

    # Final save
    save_manifest(MANIFEST_FILE, manifest)

    log.info(f"\n{'='*60}")
    log.info(f"Scraping Complete!")
    log.info(f"  Total sources:  {stats['total']}")
    log.info(f"  Downloaded:     {stats['downloaded']}")
    log.info(f"  Skipped:        {stats['skipped']}")
    log.info(f"  Failed:         {stats['failed']}")
    log.info(f"{'='*60}")

    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="RDMA RAG Knowledge Base Builder - Download and extract RDMA documentation"
    )
    parser.add_argument(
        "--category", "-c",
        choices=list(CATEGORY_DIRS.keys()),
        help="Scrape only a specific category",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be scraped without downloading",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry previously failed sources",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download even if already scraped",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=SOURCES_FILE,
        help=f"Path to sources YAML file (default: {SOURCES_FILE})",
    )
    args = parser.parse_args()

    log.info("RDMA RAG Knowledge Base Builder")
    log.info(f"Sources file: {args.sources}")
    log.info(f"Output directory: {OUTPUT_BASE}")

    sources = load_sources(args.sources)
    categories = [args.category] if args.category else None

    scrape_sources(
        sources,
        categories=categories,
        dry_run=args.dry_run,
        retry_failed=args.retry_failed,
        force=args.force,
    )


if __name__ == "__main__":
    main()
