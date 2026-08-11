"""Scraping helpers for freelancer.com project listings.

/jobs (and /jobs/N for pagination, path-based -- query strings on /jobs are
blocked by robots.txt) lists all categories sorted "Newest first" by
default, mixing fixed-price and hourly projects. We only want fixed-price
ones (task/project-based payment, matching what codeur.com and this tool
are for), so listing parsing keeps every card and filtering to fixed-price
happens after, same pattern as a mixed-contract-type source would.
"""

import re
import time

from bs4 import BeautifulSoup

from .common import fetch

SOURCE_ID = "freelancer"
BASE_URL = "https://www.freelancer.com"


def parse_listing_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.JobSearchCard-item")

    listings = []
    for card in cards:
        a = card.select_one("a.JobSearchCard-primary-heading-link")
        href = a.get("href", "") if a else ""
        if not href.startswith("/projects/"):
            # skips design contests (/contest/...), which pay one winner on
            # spec rather than being a mission a freelancer is hired for
            continue

        price_div = card.select_one("div.JobSearchCard-primary-price")
        price_text = price_div.get_text(" ", strip=True) if price_div else ""
        is_hourly = "/ hr" in price_text
        price_match = re.search(r"\$[\d,]+(?:\s*/\s*hr)?", price_text)

        desc_p = card.select_one("p.JobSearchCard-primary-description")
        tags = [
            t.get_text(strip=True) for t in card.select("a.JobSearchCard-primary-tagsLink")
        ]

        listings.append(
            {
                "id": f"{SOURCE_ID}:{href}",
                "source": SOURCE_ID,
                "url": BASE_URL + href,
                "title": a.get_text(strip=True),
                "status": None,
                "budget": price_match.group() if price_match else None,
                "offers": None,
                "views": None,
                "snippet": desc_p.get_text(" ", strip=True) if desc_p else "",
                "tags": tags,
                "is_hourly": is_hourly,
            }
        )
    return listings


def parse_detail_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    desc = soup.select_one(".Project-description")
    if not desc:
        return ""
    return desc.get_text("\n", strip=True)


def crawl_new_listings(
    seen_ids: set[str], max_pages: int = 8, delay: float = 1.2
) -> tuple[list[dict], set[str]]:
    """Walk /jobs pages ("Newest first" sort) and collect fixed-price
    listings not in seen_ids.

    Stops once a full page contributes no new listing of any pricing type,
    since pages are recency-ordered. scanned_ids covers every new card seen
    (including hourly ones we don't return), so those don't get re-walked as
    "new" on the next run either.
    """
    new_listings: list[dict] = []
    scanned_ids: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/jobs/{page}" if page > 1 else f"{BASE_URL}/jobs"
        html = fetch(url)
        listings = parse_listing_page(html)
        if not listings:
            break

        page_new = [item for item in listings if item["id"] not in seen_ids]
        if not page_new:
            break

        scanned_ids.update(item["id"] for item in page_new)
        new_listings.extend(item for item in page_new if not item["is_hourly"])

        time.sleep(delay)

    return new_listings, scanned_ids
