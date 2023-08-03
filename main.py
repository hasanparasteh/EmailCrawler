import queue
import threading
from os import getenv, path
from urllib.parse import urlparse

from dotenv import load_dotenv

from crawler import Crawler, Extractor

load_dotenv()

HTML_PATH = getenv("HTML_PATH", "html")
MAIL_PATH = getenv("MAIL_PATH", "mails.txt")

def start(url: str):
    visited_links = set()
    extracted_mails = set()
    stack = [url]
    
    while stack:
        current_url = stack.pop()
        print(current_url)
        visited_links.add(current_url)
        
        c = Crawler(current_url)
        c.load_html()

        mails = Extractor.find_emails(c.grab_html())
        if len(mails) > 0:
            with open(MAIL_PATH , "w") as f:
                for mail in mails:
                    if mail in extracted_mails:
                        continue
                    extracted_mails.add(mail)
                    f.write(mail + "\n")

        links = c.grab_links()

        c.release()

        for link in links:
            if link not in visited_links:
                stack.append(link)


if __name__ == "__main__":
    start("https://www.graphis.com/competitions/call-for-entries/")
