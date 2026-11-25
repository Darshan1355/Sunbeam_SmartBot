import os
import ssl
import time
import urllib.request
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from ..paths import DOCUMENTS_DIR


class SunbeamAboutScraper:

    def __init__(self, driver=None, wait=None):
        self.driver = driver
        self.wait = wait

    def scrape_to_txt(self, output_path=str(DOCUMENTS_DIR / "sunbeam_about.txt")):
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        lines = []
        lines.append("PAGE: ABOUT SUNBEAM\n\n")

        # 1. Try Selenium if driver provided
        scraped_via_selenium = False
        if self.driver and self.wait:
            try:
                url = "https://sunbeaminfo.com/about-us"
                self.driver.get(url)
                time.sleep(2)

                # Look for headings or paragraphs
                paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                if paragraphs:
                    for p in paragraphs:
                        t = p.text.strip()
                        if t and len(t) > 20:
                            lines.append(t + "\n\n")
                    scraped_via_selenium = True
            except Exception as e:
                print(f"⚠️ Selenium scraping encountered issue: {e}, using HTTP fallback...")

        # 2. HTTP Fallback with SSL tolerance
        if not scraped_via_selenium or len(lines) < 2:
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(
                    "https://sunbeaminfo.com/about-us",
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html, "html.parser")
                    for s in soup(["script", "style"]):
                        s.decompose()
                    for p in soup.find_all("p"):
                        txt = p.get_text().strip()
                        if txt and len(txt) > 20:
                            lines.append(txt + "\n\n")
            except Exception as e:
                print(f"⚠️ HTTP fetch fallback note: {e}")

        # If existing file exists and has content, preserve it if scraped lines are empty
        if len(lines) <= 1 and os.path.exists(output_path):
            print(f"ℹ️ Preserving existing verified about data at {output_path}")
            return

        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"✅ About data saved to {output_path}")
