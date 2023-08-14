import re
from typing import List
from urllib.parse import urlparse, urlunparse, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By


class SaveProgress:
    pass

class Extractor:
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'

    @staticmethod
    def find_emails(text:str) -> List[str]:
        return re.findall(Extractor.pattern, text)

class Crawler(object):
    browser: webdriver.Firefox
    url: str

    def __init__(self, url: str) -> None:
        options = webdriver.FirefoxOptions()
        options.headless = True
        options.set_preference('permissions.default.stylesheet', 2)
        options.set_preference('permissions.default.image', 2)

        self.browser = webdriver.Firefox(options=options)
        self.url = url

    def remove_query_params_except_page(self, url: str):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'page' in query_params:
            page_param = query_params['page'][0]
            query_params = {'page': [page_param]}
        else:
            query_params = {}
        
        new_url_parts = list(parsed_url)
        new_url_parts[4] = '&'.join(f"{k}={v[0]}" for k, v in query_params.items())
        
        new_url = urlunparse(new_url_parts)
        return new_url

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

            href = re.sub(r'\#.', '', href)
            founded_links.append(self.remove_query_params_except_page(href))

        return founded_links

    def grab_html(self):
        return self.browser.page_source

    def release(self):
        self.browser.quit()

if __name__ == "__main__":
    c = Crawler("https://google.com")
    print(c.remove_query_params_except_page("https://google.com?name=mmd&page=1&feature=[123,120,234]"))
