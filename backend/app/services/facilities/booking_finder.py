"""
Looks for a real appointment-booking link on a hospital's OWN website.

What counts as "verified": the link was actually found in the HTML of the
facility's official website (the URL Google Places gave us). We never invent
or guess a booking URL. If nothing is found we say so.

Safety: this fetches URLs that came from a third party, so it refuses anything
that is not plain http(s) to a public host (SSRF guard), uses short timeouts,
reads at most MAX_BYTES, and follows no redirects to private addresses.
"""

import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests

FETCH_TIMEOUT = 4
MAX_BYTES = 400_000
MAX_REDIRECTS = 3
USER_AGENT = "HealthcareAssistantBot/1.0 (appointment link lookup)"

_BOOKING_WORDS = re.compile(
    r"appointment|book(?:ing)?\s*(?:an?\s*)?(?:appointment|doctor|consult|visit|now)?|"
    r"opd|consult\s*(?:a\s*)?doctor|schedule\s*(?:a\s*)?visit|अपॉइंटमेंट|अपॉईंटमेंट",
    re.I,
)
_BOOKING_HREF = re.compile(r"appointment|book(?:ing)?|opd|schedule", re.I)
_NEGATIVE_TEXT = re.compile(r"book\s*(?:store|mark)|blog|news|career|job|login|sign\s*in|tenders?", re.I)


@dataclass
class BookingInfo:
    status: str                      # "found" | "not_found" | "unreachable" | "no_website"
    url: Optional[str] = None        # the booking page, only when status == "found"
    external_provider: bool = False  # booking page is on a different site than the hospital's
    provider_host: Optional[str] = None


def is_public_http_url(url: str) -> bool:
    """True only for http(s) URLs whose host resolves to public addresses."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[tuple] = []   # (href, text)
        self._href = None
        self._text: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def extract_booking_links(html: str, base_url: str) -> List[str]:
    """Booking-looking links in `html`, best first, as absolute URLs."""
    parser = _LinkParser()
    try:
        parser.feed(html)
    except Exception:
        return []

    scored = []
    for href, text in parser.links:
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if _NEGATIVE_TEXT.search(text) or _NEGATIVE_TEXT.search(href):
            continue
        text_hit = bool(_BOOKING_WORDS.search(text))
        href_hit = bool(_BOOKING_HREF.search(href))
        if not (text_hit or href_hit):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).scheme not in ("http", "https"):
            continue
        score = (2 if text_hit else 0) + (2 if href_hit else 0) + (1 if "appointment" in (text + href).lower() else 0)
        scored.append((score, absolute))

    scored.sort(key=lambda item: -item[0])
    seen, ordered = set(), []
    for _, link in scored:
        if link not in seen:
            seen.add(link)
            ordered.append(link)
    return ordered


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _same_site(a: str, b: str) -> bool:
    ha, hb = _host(a), _host(b)
    return ha == hb or ha.endswith("." + hb) or hb.endswith("." + ha)


def _fetch(url: str) -> Optional[tuple]:
    """GET with redirect-by-redirect SSRF checks. Returns (final_url, html) or None."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_public_http_url(current):
            return None
        resp = requests.get(
            current,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            allow_redirects=False,
            stream=True,
        )
        try:
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    return None
                current = urljoin(current, location)
                continue
            if resp.status_code != 200:
                return None
            if "html" not in resp.headers.get("Content-Type", "").lower():
                return None
            raw = resp.raw.read(MAX_BYTES, decode_content=True)
            return current, raw.decode(resp.encoding or "utf-8", errors="replace")
        finally:
            resp.close()
    return None


def find_booking_link(website: Optional[str]) -> BookingInfo:
    """Look for a booking link on the facility's official website."""
    if not website:
        return BookingInfo(status="no_website")

    try:
        fetched = _fetch(website)
    except (requests.RequestException, OSError, ValueError):
        return BookingInfo(status="unreachable")

    if fetched is None:
        return BookingInfo(status="unreachable")

    final_url, html = fetched
    links = extract_booking_links(html, final_url)

    for link in links:
        if is_public_http_url(link):
            external = not _same_site(link, final_url)
            return BookingInfo(
                status="found",
                url=link,
                external_provider=external,
                provider_host=_host(link) if external else None,
            )

    return BookingInfo(status="not_found")
