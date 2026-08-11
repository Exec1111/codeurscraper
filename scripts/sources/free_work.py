"""Scraping helpers for free-work.com tech/IT mission listings.

The /fr/tech-it/jobs feed mixes permanent (CDI/CDD) and freelance postings
in the same recency-ordered pages, and the same posting can be open to
several contract types at once. We only want freelance missions, but we
still need to walk past non-freelance cards to find fresh freelance ones
further down a page -- so listing parsing keeps every card, and filtering
to freelance-only happens after the page has been walked.
"""

import time

from bs4 import BeautifulSoup

from .common import fetch

SOURCE_ID = "free_work"
BASE_URL = "https://www.free-work.com"
LISTING_PATH = "/fr/tech-it/jobs"
CONTRACT_LABELS = {"CDI", "CDD", "Freelance", "Stage", "Alternance", "Intérim"}


def parse_listing_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('h2 a[href^="/fr/tech-it/job-mission/"]')

    listings = []
    seen_hrefs: set[str] = set()
    for a in links:
        href = a.get("href", "")
        if not href or href in seen_hrefs:
            # each posting is rendered twice (desktop + mobile layout)
            continue
        seen_hrefs.add(href)

        card = a.find_parent("div", class_=lambda c: c and "cursor-pointer" in c)
        if card is None:
            continue

        all_tags = [t.get_text(strip=True) for t in card.select("span.tag div.truncate")]
        contract_types = [t for t in all_tags if t in CONTRACT_LABELS]
        skill_tags = [
            t for t in all_tags if t not in CONTRACT_LABELS and not t.startswith("+")
        ]

        snippet_div = card.select_one("div.fw-text-highlight.line-clamp-4")

        listings.append(
            {
                "id": f"{SOURCE_ID}:{href}",
                "source": SOURCE_ID,
                "url": BASE_URL + href,
                "title": a.get_text(strip=True),
                "status": None,
                "budget": None,
                "offers": None,
                "views": None,
                "snippet": snippet_div.get_text(" ", strip=True) if snippet_div else "",
                "tags": skill_tags,
                "contract_types": contract_types,
            }
        )
    return listings


def parse_detail_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    desc = soup.select_one("div.html-renderer.prose-content")
    if not desc:
        return ""
    return desc.get_text("\n", strip=True)


def crawl_new_listings(
    seen_ids: set[str], max_pages: int = 8, delay: float = 1.2
) -> tuple[list[dict], set[str]]:
    """Walk /fr/tech-it/jobs pages and collect freelance listings not in seen_ids.

    Stops once a full page contributes no new listing of any contract type
    (freelance or not), since pages are recency-ordered. scanned_ids covers
    every new card seen (including CDI/CDD ones we don't return), so those
    don't get re-walked as "new" on the next run either.
    """
    new_listings: list[dict] = []
    scanned_ids: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}{LISTING_PATH}?page={page}" if page > 1 else f"{BASE_URL}{LISTING_PATH}"
        html = fetch(url)
        listings = parse_listing_page(html)
        if not listings:
            break

        page_new = [item for item in listings if item["id"] not in seen_ids]
        if not page_new:
            break

        scanned_ids.update(item["id"] for item in page_new)
        new_listings.extend(
            item for item in page_new if "Freelance" in item["contract_types"]
        )

        time.sleep(delay)

    return new_listings, scanned_ids
