## Process all of the 11k pages into flat CSV results file that we can use
## to do analysis.
# The main items that we want for each person are:
# - Name
# - Position
# - Bib number
# - Time
# - Gender
# - Age group
# - KOM Time (King of the Mountain)
# - DD Time (Demon Descent)

# We will denormalise all of the data (i.e. Age group) as we don't know
# what age groups there are.  We will process each bib page, extract all the
# data, hold it in memory and then write it to the csv file

# All of the page files are in UTF-8 encoding, and we need to decode them into
# unicode before processing.  We will write the CSV file in UTF-8 as well.

from __future__ import print_function
import os.path
import re
import random
import csv
import codecs
import cStringIO

import bs4

# Seed data (i.e. known gender information)
# We have to match the gender by comparing a known set of Genders
# So what we do is grab all the 'same' genders from a page and store them
# against the page record, and then post process the whole lot via bib numbers
# Note that we have to store a look up of 'name-time' strings to bib numbers
# as that's all we have in each page as a reference.
GENDERS = {u'2154': 'M', u'2155': 'F'}
MALE_BIB = u'2154'
FEMALE_BIB = u'2155'
MALE_LABEL = 'M'
FEMALE_LABEL = 'F'

PAGES_CACHE = './pages_11k_cache'
page_cache_template = "./pages_11k_cache/page_for_bib_{}.html"
OUT_CSV_FILE = "results_11k.csv"
HEADINGS = ('position', 'bib', 'name', 'time', 'age-group',
            'KOM', 'DD', 'pos-age', 'pos-gender', 'gender')

PAGE_CACHE_REGEX = re.compile("page_for_bib_(\S+)\.html")
AGE_GROUP_FINDER = re.compile(r".*\((.+)\).*")

POSITION = 0
BIB = 1
NAME = 2
TIME = 3
AGE_POSITION = 0
GENDER_POS = 1
GENDER_NAME = 2
GENDER_TIME = 3


def load_page(bib_str):
    filename = page_cache_template.format(bib_str)
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            return file.read().decode('UTF-8')
    raise Exception('File {} not found'.format(filename))


def bib_numbers_from_pages_cache_iter():
    """Fetch an array of bib numbers from the pages cache

    :returns array-of-strings: the bib numbers found
    """
    pages = os.listdir(PAGES_CACHE)
    for p in pages:
        m = PAGE_CACHE_REGEX.match(p)
        yield m.groups()[0]


def bib_numbers_from_pages_cache():
    return list(bib_numbers_from_pages_cache_iter())


def process_page(html_page, bib_str):
    """Process a page and extract the following information for the page
    - name-time, name, position, bib, time, age-group(string), KOM, DD,
      pos-age, pos-gender,
      same-genders-name-time([array of same gender name-time keys])

    These are ALL unicode strings

    :param html_page: the HMTL in unicode
    :param bib_str: the bib_str for the page - to verify the code works!
    :return dict-of-keys: as above.

    """
    soup = bs4.BeautifulSoup(html_page)
    result = {}

    # First we want to find the selected Name which is our page.
    # This is the CSS selector:
    # #ctl00_SecondaryContent_ResultsGrid > tbody > tr.selected
    our_hero = soup.select(
        '#ctl00_SecondaryContent_ResultsGrid > tr.selected > td')
    # print(our_hero, type(our_hero))
    # for td in our_hero:
    #     print(type(td), td)
    result['position'] = our_hero[POSITION].string
    result['bib'] = our_hero[BIB].string
    result['name'] = our_hero[NAME].string
    result['time'] = our_hero[TIME].string
    assert result['bib'] == bib_str
    result['name-time'] = '{}={}'.format(result['name'], result['time'])

    # Now look in the Age Group results
    our_hero_age = soup.select(
        '#ctl00_SecondaryContent_AgeGroupGrid > tr.selected > td')
    result['pos-age'] = our_hero_age[AGE_POSITION].string
    assert result['name'] == our_hero_age[1].string
    assert result['time'] == our_hero_age[2].string

    # Get the Age Group string
    age_group_str = (soup.select(
        '#ctl00_SecondaryContent_PanelAgeGroupResults > div > div > h2')[0]
        .string
        .strip())
    age_group_str = age_group_str.replace("\n", "")
    age_group_str = age_group_str.replace("\t", "")
    m = AGE_GROUP_FINDER.match(age_group_str)
    result['age-group'] = m.groups()[0]

    # Get the split times - this is four spans (we want the 2nd and 4th)
    # The 2nd is the King of the Mountain
    # <class 'bs4.element.Tag'> [<b>King of the Mountain </b>, u'00:13:46']
    # The 4th is the Demon Descent
    # <class 'bs4.element.Tag'> [<b>King of the Mountain </b>, u'00:13:46']
    split_els = soup.select(
        '#split-times > span')
    result['KOM'] = list(split_els[1].children)[1]
    result['DD'] = list(split_els[3].children)[1]

    # And finally, get a list of the same gender name-time strings
    tr_same_genders = soup.select(
        '#ctl00_SecondaryContent_GenderGroupGrid > tr')
    name_time_list = []
    for tr in tr_same_genders:
        # print(type(tr), tr)
        gender_pos = tr.contents[GENDER_POS].string
        if gender_pos == 'Pos':
            continue
        name = tr.contents[GENDER_NAME].string
        time = tr.contents[GENDER_TIME].string
        # print("'{}' : '{}' : '{}'".format(gender_pos, name, time))
        if name == result['name']:
            result['pos-gender'] = gender_pos
        else:
            name_time_list.append("{}={}".format(name, time))
    result['same-genders-name-time'] = name_time_list

    return result


class GenderMatcher(object):
    """Works out which gender everybody is

    Does loads of processing to match genders based on same genders
    """

    def __init__(self, male_bib, female_bib):
        self.male_bib = male_bib
        self.female_bib = female_bib
        self.bib_to_gender = {}
        self.name_time_to_bid = {}
        self.groups = []
        self.male = None
        self.female = None
        self.male_name_time = None
        self.female_name_time = None

    def add(self, bib, name_time, same_genders_name_time):
        """Adds a bib, name_time and a set of matched genders

        :param name_time: a name=time unique string for a bib
        :param bib: the bib number attached to the name=time string
        :param same_genders_name_time: a list of same genders

        """
        print("Adding {}, {}, ".format(bib, name_time), end="")
        self.name_time_to_bid[name_time] = bib
        if bib == self.male_bib:
            self.male_name_time = name_time
        if bib == self.female_bib:
            self.female_name_time = name_time
        same_set = [name_time] + same_genders_name_time
        add_to = None
        for g in range(len(self.groups)):
            for s in same_set:
                if s in self.groups[g]:
                    add_to = g
                    break
        d = {a: True for a in same_set}
        if add_to is None:
            print("Adding a new group")
            self.groups.append(d)
        else:
            print("Adding to group {}".format(add_to))
            self.groups[add_to].update(d)

    def finalise_groups(self):
        """Try to rationalise it down to only two groups"""
        print("Finalising: {} groups".format(len(self.groups)))
        while len(self.groups) > 2:
            g1 = random.randrange(0, len(self.groups))
            g2 = random.randrange(0, len(self.groups))
            print("Trying to join {} and {}".format(g1, g2))
            if g1 == g2:
                continue
            # see if we can pair the groups together.
            for x in self.groups[g1]:
                if x in self.groups[g2]:
                    self.groups[g1].update(self.groups[g2])
                    self.groups = self.groups[:g2]+self.groups[g2+1:]
                    break
        # now we only have two unique groups (in theory!)
        if self.male_name_time in self.groups[0]:
            self.male = 0
            self.female = 1
        else:
            assert self.female_name_time in self.groups[0]
            self.male = 1
            self.female = 0
        # Do the males first
        print("Male is {}, Female is {}".format(self.male, self.female))
        for x in self.groups[self.male]:
            self.bib_to_gender[self.name_time_to_bid[x]] = MALE_LABEL
        # now the females
        for y in self.groups[self.female]:
            self.bib_to_gender[self.name_time_to_bid[y]] = FEMALE_LABEL

    def gender_for_bib(self, bib):
        return self.bib_to_gender[bib]


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
        self.writer.writerow([s.encode("utf-8") for s in row])
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


if __name__ == '__main__':
    map_bib_to_result = {}
    map_name_time_to_bib = {}
    gender_matcher = GenderMatcher(MALE_BIB, FEMALE_BIB)
    for bib_str in bib_numbers_from_pages_cache_iter():
        page = load_page(bib_str)
        result = process_page(page, bib_str)
        map_bib_to_result[result['bib']] = result
        map_name_time_to_bib[result['name-time']] = result['bib']
        gender_matcher.add(
            result['bib'],
            result['name-time'],
            result['same-genders-name-time'])

    gender_matcher.finalise_groups()
    males = 0
    females = 0
    for bib, result in map_bib_to_result.iteritems():
        print("matching gender for bib:{}".format(bib))
        result['gender'] = gender_matcher.gender_for_bib(bib)
        if result['gender'] == MALE_LABEL:
            males += 1
        else:
            females += 1
        del result['same-genders-name-time']

    with open(OUT_CSV_FILE, 'w') as f:
        uw = UnicodeWriter(f)
        uw.writerow(HEADINGS)
        for k, v in map_bib_to_result.iteritems():
            print('{}, {} is {}'.format(k, v['name'], v['gender']))
            uw.writerow([v[h] for h in HEADINGS])
        print("{} males, {} females: total={}".format(males, females, males + females))

    # for k, v in map_name_time_to_bib.iteritems():
    #     print('{} = {}'.format(k, v))
