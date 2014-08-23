# try to fetch all the pages on the site
# this just uses requests and then saves each page with a sequential number
# other software will try to parse the pages and get all of the results
from __future__ import print_function
import os
import os.path
import re
import random
import time

import requests
import bs4

url_template = ("http://www.greattrailchallenge.org/Results/"
                "default.aspx?r=412&bib={}")
PAGES_CACHE = './pages_cache'
page_cache_template = "./pages_cache/page_for_bib_{}.html"
PAGE_CACHE_REGEX = re.compile("page_for_bib_(\S+)\.html")

START_BIB = "13"
POSITION = 1
BIB = 2
NAME = 3
TIME = 4

TIME_DELAY = 10


def get_page(bib_str):
    filename = page_cache_template.format(bib_str)
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            return file.read().decode('UTF-8')
    return fetch_page(bib_str)


def cache_file(bib_str, data, over_write=False):
    filename = page_cache_template.format(bib_str)
    if not over_write:
        if os.path.isfile(filename):
            return
    with open(filename, 'w') as file:
        file.write(data.encode('UTF-8'))


def fetch_page(bib_str):
    delay = random.randrange(TIME_DELAY)
    print("Waiting {} seconds ...".format(delay))
    time.sleep(delay)
    print("fetching page {}".format(bib_str))
    url = url_template.format(bib_str)
    # print(url)

    r = requests.get(url)
    # Note r.text is unicode.
    return r.text


def process_page(html_data):
    soup = bs4.BeautifulSoup(html_data)

    results = []

    # we want: css path: #ctl00_SecondaryContent_ResultsGrid
    results_table = soup.select('#ctl00_SecondaryContent_ResultsGrid')

    # print(results_table)

    # print(type(results_table[0]))

    for tr in results_table[0].children:
        good = True if type(tr) is bs4.element.Tag else False
        # print("child:{} and is {}".format(type(tr), good))
        if good:
            pos = tr.contents[POSITION].string
            if pos.lower() != 'pos':
                results.append({
                    'pos': pos,
                    'bib': tr.contents[BIB].string,
                    'name': tr.contents[NAME].string,
                    'time': tr.contents[TIME].string,
                })
            # print("in child: 1st element is a {}".format(type(tr.contents[0])))
            # print("Pos:  {}".format(tr.contents[POSITION].string))
            # print("Bib:  {}".format(tr.contents[BIB].string))
            # print("Name: {}".format(tr.contents[NAME].string))
            # print("Time: {}".format(tr.contents[TIME].string))
    return results


def bib_numbers_from_pages_cache():
    pages = os.listdir(PAGES_CACHE)
    l = []
    for p in pages:
        m = PAGE_CACHE_REGEX.match(p)
        l.append(m.groups()[0])
    return l


if __name__ == '__main__':
    done_bibs = {}
    todo_bibs = {b: True for b in bib_numbers_from_pages_cache()}

    finished = False
    count = 0
    next_bib = START_BIB
    while not finished:
        count += 1
        # if count == 10:
        #     finished = True  # kill it on the first round
        data = get_page(next_bib)
        cache_file(next_bib, data)
        done_bibs[next_bib] = True
        try:
            del todo_bibs[next_bib]
        except KeyError:
            pass
        results = process_page(data)
        found_bibs = [r['bib'] for r in results]
        for bib in found_bibs:
            if bib not in done_bibs:
                todo_bibs[bib] = True
        keys_left = todo_bibs.keys()
        if len(keys_left):
            next_bib = random.choice(todo_bibs.keys())
            print("Next bib = {}".format(next_bib))
        else:
            finished = True

    print(done_bibs)
    print(todo_bibs)
    print("Total pages processed: {}".format(count))
