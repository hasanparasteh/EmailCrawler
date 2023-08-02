import logging
import os
import re
import threading
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from dotenv import load_dotenv
from time import sleep

# Set up the logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s'
)

URL = "https://www.graphis.com/competitions/call-for-entries/"
ENABLE_PROXY = False

class StaticEmailCrawler:
    pattern = r'[\w.+-]+@[\w-]+\.[\w.-]+'
    visited = []

    def __init__(self):
        pass

    def insert_mail(self, mail: str) -> None:
        with open(os.getenv("MAIL_PATH","mails.txt"), "a") as f:
            f.write(mail + "\n")

    def insert_html(self, url: str, html_content: str) -> None:
        url = url.replace(URL, "")
        
        if url.startswith('/'):
            url = url[1:]

        if url == "":
            url = "index"
        
        if url.endswith('/'):
            url = url[:-1]
        
        file_path = "html/" + url + ".html"
        dir_path, file_name = os.path.split(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(html_content)

    def find_all_links(self, soup: BeautifulSoup) -> List[str]:
        links = soup.find_all('a')
        internal_links = []

        for link in links:
            href = link.get('href')
            if href is not None:
                if href.startswith('/'):
                    internal_links.append(urljoin(URL, href))
                elif URL in href:
                    internal_links.append(href)
        return internal_links

    def fetch_website(self, link: str) -> BeautifulSoup:
        logging.info("Visiting %s", url)
        response = requests.get(URL)
        if response.status_code != 200:
            raise Exception("Failed to get " + link)
        return BeautifulSoup(response.content, 'html.parser')

    def extract_emails(self, text: str):
        return re.findall(self.pattern, text)


    def loop(self, url: str = URL):
        self.visited.append(url)
        html = self.fetch_website(url)
        self.insert_html(url, html.prettify())
        mails = self.extract_emails(html.get_text())

        for mail in mails:
            self.insert_mail(mail)
        
        links = self.find_all_links(html)
        for link in links:
            if link in self.visited:
                continue
            self.loop(link)
    

class DynamicEmailCrawler(StaticEmailCrawler):
    def fetch_website(self, link: str) -> BeautifulSoup:
        options = webdriver.FirefoxOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--headless")
        options.add_argument('--disable-dev-shm-usage')

        browser = webdriver.Firefox(options=options)
        browser.get(link)
        
        logging.info("Waiting to load: %s", link)
        # Wait for all images to load
        wait = WebDriverWait(browser, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
        wait.until(lambda driver: driver.execute_script("return document.readyState") == 'complete')
        wait.until(lambda driver: driver.execute_script("return Object.values(document.images).every(img => img.complete)"))
        logging.info("Finished Waiting for: %s", link)

        html = browser.page_source

        browser.quit()
        return BeautifulSoup(html, 'html.parser')


class ThreadedEmailCrawler(DynamicEmailCrawler):
    semaphore: threading.Semaphore
    lock: threading.Lock

    def __init__(self,thread_count: int = 4):
        self.semaphore = threading.Semaphore(thread_count)
        self.lock = threading.Lock()

    def load_visited_links(self, visited_links_path: str, ):
        if not os.path.exists(visited_links_path):
            return False

        with open(visited_links_path, "r") as visited_links_file:
            for line in visited_links_file.readlines():
                self.visited.append(line.strip().replace("\n", ""))
        return True
        

    def insert_mail(self, mail: str) -> None:
        self.lock.acquire()
        with open(os.getenv("MAIL_PATH","mails.txt"), "a") as f:
            f.write(mail + "\n")
        self.lock.release()
    
    def loop(self, url: str = URL):
        self.visited.append(url)
        html = self.fetch_website(url)
        self.insert_html(url, html.prettify())
        mails = self.extract_emails(html.get_text())

        for mail in mails:
            self.insert_mail(mail)
        
        threads = []
        links = self.find_all_links(html)
        for link in links:
            if link in self.visited:
                continue
            t = threading.Thread(target=self.loop, args=[link])
            threads.append(t)
            try:
                t.start()
            except Exception as e:
                logging.error("FAILED TO START THREAD %s", e.args)
                threads.pop()
                self.loop(link)


        for t in threads:
            t.join()
        
    def fetch_website(self, link: str) -> BeautifulSoup:
        self.semaphore.acquire()

        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080');
        
        if ENABLE_PROXY:
            proxy = Proxy({
                'proxyType': ProxyType.MANUAL,
                'socksProxy': os.getenv("PROXY_URL", '127.0.0.1'),
                'socksProxyPort': int(os.getenv("PROXY_PORT", '1358')),
                'socksVersion': 5
            })
            options.proxy = proxy

        browser = webdriver.Firefox(options=options)
        logging.info("Visiting: %s", link)
        browser.get(link)
        
        logging.info("Waiting to load: %s", link)
        # Wait website fully loaded
        sleep(5)
        # wait = WebDriverWait(browser, 10)
        # wait.until(lambda driver: driver.execute_script("return document.readyState") == 'complete')
        logging.info("Finished Waiting for: %s", link)

        html = browser.page_source

        browser.quit()
        self.semaphore.release()
        return BeautifulSoup(html, 'html.parser')
        
if __name__ == "__main__":
    print("Starting...")
    load_dotenv()
    thread_count = int(os.getenv("THREAD_COUNT", "4"))
    visited_links_path = os.getenv("VISITED_LINKS_PATH", "visited.txt")
    # crawler = ThreadedEmailCrawler(thread_count=thread_count)
    crawler = DynamicEmailCrawler()
    crawler.load_visited_links(visited_links_path=visited_links_path)
    try: 
        crawler.loop(URL)
    except KeyboardInterrupt:
        print("Bye")
    finally:
        with open(visited_links_path, "w") as visited_links_file:
            for link in crawler.visited:
                visited_links_file.write(link + "\n")
        
