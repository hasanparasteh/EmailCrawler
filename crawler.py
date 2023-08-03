import re
from typing import List
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By


class SaveProgress:
    pass

class Extractor:
    pattern = r"[\w.+-]+@[\w-]+\.[\w.-]+"

    @staticmethod
    def find_emails(text:str) -> List[str]:
        return re.findall(Extractor.pattern, text)

class Crawler(object):
    browser: webdriver.Firefox
    url: str

    def __init__(self, url: str) -> None:
        options = webdriver.FirefoxOptions()
        options.headless = False

        self.browser = webdriver.Firefox(options=options)
        self.url = url

    def _is_internal_link(self, link: str):
        base_parsed = urlparse(self.url)
        href_parsed = urlparse(link)

        return base_parsed.netloc == href_parsed.netloc

    def load_html(self):
        self.browser.get(self.url)
        self.browser.implicitly_wait(1)

    def grab_links(self):
        links = self.browser.find_elements(by=By.TAG_NAME, value="a")
        founded_links = []
        for link in links:
            href = link.get_attribute("href")
            if href is None:
                continue
            if not self._is_internal_link(href):
                continue
            founded_links.append(href)

        return founded_links

    def grab_html(self):
        return self.browser.page_source

    def release(self):
        self.browser.quit()