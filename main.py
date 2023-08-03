import logging
import queue
import threading
from os import getenv, path
from urllib.parse import urlparse

from dotenv import load_dotenv

from crawler import Crawler, Extractor

load_dotenv()

MAIL_PATH = getenv("MAIL_PATH", "mails.txt")

file_lock = threading.Lock()
visited_links_lock = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

global visited_links
visited_links = set()
extracted_mails = set()
shared_queue = queue.Queue()

def crawl_url():
    global shared_queue
    global visited_links
    global file_lock

    while True:
        url = shared_queue.get()
        if url is None:
            break

        c = Crawler(url)

        is_html_loaded = True
        try:
            c.load_html()
        except:
            is_html_loaded = False
            shared_queue.put(url)

        if is_html_loaded:
            mails = Extractor.find_emails(c.grab_html())
            links = c.grab_links()
            c.release()

            logging.info("Found %s links and %s mails from %s", len(links), len(mails), url)

            if len(mails) > 0:
                with file_lock:
                    mail_file = open(MAIL_PATH, "a+")
                    for mail in mails:
                        if mail in extracted_mails:
                            continue
                        
                        mail_file.write(mail + "\n")
                        extracted_mails.add(mail)
                    mail_file.close()
            
            with visited_links_lock:
                for link in links:
                    if link not in visited_links:
                        visited_links.add(link)
                        shared_queue.put(link)

def start(url: str):
    global shared_queue
    global visited_links

    shared_queue.put(url)

    num_threads = 8
    threads = []

    # Create and start the threads
    for _ in range(num_threads):
        thread = threading.Thread(target=crawl_url)
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    try:
        start("https://www.graphis.com/competitions/call-for-entries/")
    except KeyboardInterrupt:
        print("Exit")
