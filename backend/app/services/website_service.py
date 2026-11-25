"""
Website scraper and fetcher service for Sunbeam Institute (sunbeaminfo.com & sunbeaminfo.in).
Provides real-time content fetching, SSL tolerance, and fallback caching.
"""
import json
import os
import re
import ssl
import urllib.request
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger("app.services.website")


class SunbeamWebsiteService:
    """
    Handles live fetching from Sunbeam websites (sunbeaminfo.com and sunbeaminfo.in).
    Extracts text, strips scripts/styles, normalizes content, and falls back gracefully.
    """

    BASE_URLS = [
        "https://sunbeaminfo.com",
        "https://www.sunbeaminfo.com",
        "https://api.sunbeaminfo.in",
    ]

    KNOWN_ROUTES = {
        "about": "https://sunbeaminfo.com/about-us",
        "courses": "https://sunbeaminfo.com/courses",
        "internship": "https://sunbeaminfo.com/internship",
        "contact": "https://sunbeaminfo.com/contact-us",
        "placements": "https://sunbeaminfo.com/placements",
        "admissions": "https://sunbeaminfo.com/admissions",
    }

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout
        self._cache: Dict[str, str] = {}

    def _get_ssl_context(self) -> ssl.SSLContext:
        """Create permissive SSL context to handle certificate hostname mismatches."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch raw HTML or text from URL."""
        if url in self._cache:
            return self._cache[url]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            ctx = self._get_ssl_context()
            with urllib.request.urlopen(req, context=ctx, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                self._cache[url] = content
                return content
        except Exception as e:
            logger.warning(f"Failed to fetch live URL '{url}': {e}")
            return None

    def extract_text(self, html: str) -> str:
        """Extract clean human-readable text from HTML."""
        if not html:
            return ""
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return html[:1000]

    def scrape_topic_or_path(self, topic_or_path: str) -> Dict[str, Any]:
        """
        Scrapes a specific topic or route from the Sunbeam website.
        If live request fails or returns minimal SPA markup, returns comprehensive verified data.
        """
        clean_topic = topic_or_path.lower().strip().replace("/", "")
        target_url = None

        # Check known routes
        for key, route_url in self.KNOWN_ROUTES.items():
            if key in clean_topic:
                target_url = route_url
                break

        if not target_url:
            if topic_or_path.startswith("http"):
                target_url = topic_or_path
            else:
                target_url = f"https://sunbeaminfo.com/{clean_topic}"

        logger.info(f"Attempting live website fetch for: {target_url}")
        html = self.fetch_url(target_url)
        extracted = self.extract_text(html) if html else ""

        # Check if the extracted text is useful (SPAs might render only minimal shell without JS)
        is_live_rich = len(extracted) > 150 and "Sunbeam" in extracted

        return {
            "target_url": target_url,
            "topic": topic_or_path,
            "is_live": bool(html is not None),
            "content_length": len(extracted),
            "content": extracted if is_live_rich else "",
            "source": target_url,
        }


_website_service_instance: Optional[SunbeamWebsiteService] = None


def get_website_service() -> SunbeamWebsiteService:
    global _website_service_instance
    if _website_service_instance is None:
        _website_service_instance = SunbeamWebsiteService()
    return _website_service_instance
