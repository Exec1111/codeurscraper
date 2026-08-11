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
    if "charset" not in resp.headers.get("Content-Type", "").lower():
        # some sites (e.g. freelancer.com) omit charset, and requests then
        # falls back to ISO-8859-1 per HTTP spec even though the body is
        # UTF-8, mangling accents/punctuation
        resp.encoding = resp.apparent_encoding
    return resp.text
