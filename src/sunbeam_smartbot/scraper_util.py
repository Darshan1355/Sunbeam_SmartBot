from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from .scrapers.sunbeam_about import SunbeamAboutScraper
from .scrapers.sunbeam_internship import SunbeamInternshipScraper


class ScraperManager:

    def __init__(self):
        self.driver = None
        self.wait = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
        except Exception as e:
            print(f"⚠️ Chrome webdriver initialization skipped ({e}). Using direct HTTP scraper fallback.")

    def scrape_all_to_txt(self):
        SunbeamAboutScraper(self.driver, self.wait).scrape_to_txt()
        SunbeamInternshipScraper(self.driver, self.wait).scrape_to_txt()

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
