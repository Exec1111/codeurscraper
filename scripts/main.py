"""Daily orchestration: scrape codeur.com, score against criteria.txt, publish results."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import scrape
import score

ROOT = Path(__file__).resolve().parent.parent
CRITERIA_PATH = ROOT / "criteria.txt"
DATA_DIR = ROOT / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"
SEEN_PATH = DATA_DIR / "seen_ids.json"
LATEST_PATH = DATA_DIR / "latest.json"

MAX_SCRAPE_PAGES = 8
STAGE_B_CANDIDATES_CAP = 25
FINAL_MAX = 20
DETAIL_FETCH_DELAY = 1.2
SEEN_IDS_KEEP = 4000


def load_seen_ids() -> set[int]:
    if not SEEN_PATH.exists():
        return set()
    return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")))


def save_seen_ids(ids: set[int]) -> None:
    trimmed = sorted(ids, reverse=True)[:SEEN_IDS_KEEP]
    SEEN_PATH.write_text(json.dumps(sorted(trimmed)), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    criteria = CRITERIA_PATH.read_text(encoding="utf-8")
    seen_ids = load_seen_ids()

    new_listings = scrape.crawl_new_listings(seen_ids, max_pages=MAX_SCRAPE_PAGES)
    scanned_ids = seen_ids | {item["id"] for item in new_listings}

    final_records: list[dict] = []

    if new_listings:
        stage_a = score.score_snippets(criteria, new_listings)
        ranked = sorted(
            new_listings,
            key=lambda item: stage_a.get(item["id"], {}).get("score", 0),
            reverse=True,
        )
        candidates = ranked[:STAGE_B_CANDIDATES_CAP]

        for item in candidates:
            try:
                html = scrape.fetch(item["url"])
                item["description"] = scrape.parse_detail_description(html)
            except Exception as exc:  # noqa: BLE001 - keep going on a single failure
                print(f"WARN: failed to fetch detail for {item['url']}: {exc}")
                item["description"] = item["snippet"]
            time.sleep(DETAIL_FETCH_DELAY)

        stage_b = score.score_full_descriptions(criteria, candidates)
        ranked_final = sorted(
            candidates,
            key=lambda item: stage_b.get(item["id"], {}).get("score", 0),
            reverse=True,
        )[:FINAL_MAX]

        for item in ranked_final:
            result = stage_b.get(item["id"], {})
            final_records.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "url": item["url"],
                    "budget": item["budget"],
                    "offers": item["offers"],
                    "views": item["views"],
                    "tags": item["tags"],
                    "score": result.get("score", 0),
                    "reason": result.get("reason", ""),
                }
            )

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "new_listings_scanned": len(new_listings),
        "missions": final_records,
    }

    LATEST_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    history_path = HISTORY_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.json"
    history_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    save_seen_ids(scanned_ids)

    print(
        f"Scanned {len(new_listings)} new listings, "
        f"published {len(final_records)} missions."
    )


if __name__ == "__main__":
    main()
