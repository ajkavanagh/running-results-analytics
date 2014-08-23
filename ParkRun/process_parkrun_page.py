## Process the parkrun page (or default results)

# The default page is
# http://www.parkrun.org.uk/newcastle/results/latestresults/
# Note that they don't like scrapers, so you have to save the page manually
# and then process the page after the fact.

# The columns pulled are:

# Pos
# parkrunner (may not be unique)
# Time
# Age Cat  - an age category
# Age Grade - the Parkrun normalisation for age vs world record holder.
# Gender (M/F)
# Gender Pos
# Club affiliation
# Total Runs

# There is other information, but this is all I'm interested in!

# The encoding of the page is normally UTF-8

from __future__ import print_function
import os.path
import re
import csv
import codecs
import cStringIO

import bs4


DEFAULT_RESULTS_PAGE = \
    "/Users/alex/Downloads/latest results   Newcastle parkrun.html"
OUT_CSV_FILE = 'parkrun_results.csv'
AGE_GROUP_FINDER = re.compile(r".*\((.+)\).*")
HEADINGS = ('Pos', 'Park Runner', 'Time', 'Age Cat', 'Age Grade', 'Gender',
            'Gender Pos', 'Club', 'Total Runs')


def open_results_page(file):
    """
    :param url: the page to open
    :returns: the unicode text of the HTML page.
    """
    file = file or DEFAULT_RESULTS_PAGE
    file = os.path.abspath(file)
    with open(file, 'r') as f:
        text = f.read()
    return text



def process_results_page(html_page):
    """ Process the ParkRun results page and give out a dictionary of
    key:value for each row in the page.

    :param html_page: The unicode HTML page.
    :returns: an iterator (via yield) that gives up each row of the table
    """
    soup = bs4.BeautifulSoup(html_page)

    # Find the id="results" table in the page
    results_table = soup.select(
        'table#results > tbody > tr')
    for tr in results_table:
        # print(tr)
        children = list(tr.children)
        row = {
            'Pos': children[0].string,
            'Park Runner': children[1].string,
            'Time': children[2].string,
            'Age Cat': children[3].string,
            'Age Grade': children[4].string,
            'Gender': children[5].string,
            'Gender Pos': children[6].string,
            'Club': children[7].string,
            'Total Runs': children[9].string,
        }
        yield row


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow(
            [UnicodeWriter.safe_s(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    @staticmethod
    def safe_s(s):
        return '' if s is None else str(s)

if __name__ == '__main__':
    html_page = open_results_page(None)
    results_gen = process_results_page(html_page)

    with open(OUT_CSV_FILE, 'w') as f:
        uw = UnicodeWriter(f)
        uw.writerow(HEADINGS)
        for row in results_gen:
            uw.writerow([row[h] for h in HEADINGS])

    # for k, v in map_name_time_to_bib.iteritems():
    #     print('{} = {}'.format(k, v))
