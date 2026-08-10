"""Scraping helpers for codeur.com project listings."""

import re
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.codeur.com"
HEADERS = {
    "User-Agent": (
        "codeurscraper/1.0 (+https://github.com/exec1111/codeurscraper; "
        "personal daily digest script)"
    )
}
REQUEST_TIMEOUT = 20


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_listing_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("#projects-list")
    if not container:
        return []

    listings = []
    for a in container.select(":scope > a[href^='/projects/']"):
        href = a.get("href", "")
        match = re.match(r"^/projects/(\d+)", href)
        if not match:
            continue
        project_id = int(match.group(1))

        h3 = a.select_one("h3")
        title = h3.get_text(strip=True) if h3 else a.get("aria-label", "").strip()

        status_span = a.select_one("span:-soup-contains('Ouvert')") or a.select_one(
            "span:-soup-contains('En cours')"
        )
        budget_span = a.select_one('span[title="Budget"]')
        offers_span = a.select_one('span[title="Offres"]')
        views_span = a.select_one('span[title="Vues"]')
        snippet_div = a.select_one("div.line-clamp-3")
        tag_container = a.select_one("div.max-h-6.overflow-hidden")
        tags = (
            [s.get_text(strip=True) for s in tag_container.select("span")]
            if tag_container
            else []
        )

        offers_text = offers_span.get_text(strip=True) if offers_span else ""
        offers_match = re.search(r"\d+", offers_text)

        listings.append(
            {
                "id": project_id,
                "url": BASE_URL + href,
                "title": title,
                "status": status_span.get_text(strip=True) if status_span else None,
                "budget": budget_span.get_text(strip=True) if budget_span else None,
                "offers": int(offers_match.group()) if offers_match else None,
                "views": views_span.get_text(strip=True) if views_span else None,
                "snippet": snippet_div.get_text(strip=True) if snippet_div else "",
                "tags": tags,
            }
        )
    return listings


def parse_detail_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    desc = soup.select_one("div.project-description .content")
    if not desc:
        return ""
    return desc.get_text("\n", strip=True)


def crawl_new_listings(
    seen_ids: set[int], max_pages: int = 8, delay: float = 1.2
) -> list[dict]:
    """Walk /projects pages (most recent first) and collect listings not in seen_ids.

    Stops once a full page contributes no new listing, since pages are
    ordered by recency and everything beyond is presumably already seen.
    """
    new_listings: list[dict] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/projects?page={page}" if page > 1 else f"{BASE_URL}/projects"
        html = fetch(url)
        listings = parse_listing_page(html)
        if not listings:
            break

        page_new = [item for item in listings if item["id"] not in seen_ids]
        new_listings.extend(page_new)

        if not page_new:
            break

        time.sleep(delay)

    return new_listings
