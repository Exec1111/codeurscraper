"""Shared HTTP fetch helper for all source scrapers."""

import requests

USER_AGENT = (
    "codeurscraper/1.0 (+https://github.com/exec1111/codeurscraper; "
    "personal daily digest script)"
)
HEADERS = {"User-Agent": USER_AGENT}
REQUEST_TIMEOUT = 20


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text
