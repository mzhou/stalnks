import asyncio
import calendar
import collections
import contextlib
import datetime
import os
import re
import sqlite3
import tempfile

import selenium
import selenium.webdriver

#
# Reports
#

ParsedReport = collections.namedtuple('ParsedReport', 'report used_tokens total_tokens')
PrettyReport = collections.namedtuple('PrettyReport', 'day day_part price')

class Report(collections.namedtuple('Report', 'day day_part price')):
    def pretty(self):
        return PrettyReport(day=DAY_STRS[self.day], day_part=DAY_PART_STRS[self.day_part], price=self.price)

DAY_STRS = 'Sunday Monday Tuesday Wednesday Thursday Friday Saturday'.split()
DAY_PART_STRS = 'AM PM'.split()

def match_token(candidates, token):
    for seq, candidate in enumerate(candidates):
        if token in candidate:
            return seq
    return None

def parse_report(report_str):
    DAY_CANDIDATES = [x.split() for x in [
        'sun sunday',
        'mon monday',
        'tue tues tuesday',
        'wed wednesday',
        'thu thur thurs thursday',
        'fri friday',
        'sat saturday',
    ]]
    DAY_PART_CANDIDATES = [x.split() for x in [
        'am morn morning',
        'pm arvo afternoon',
    ]]
    # split into words
    tokens = report_str.lower().split()
    used_tokens = 0
    total_tokens = len(tokens)

    price = None
    day = None
    day_part = None
    for token in tokens:
        if price is None and re.match('[0-9]+$', token):
            price = int(token, 10)
            used_tokens += 1
        if day is None:
            day = match_token(DAY_CANDIDATES, token)
            if day is not None:
                used_tokens += 1
        if day_part is None:
            day_part = match_token(DAY_PART_CANDIDATES, token)
            if day_part is not None:
                used_tokens += 1

    return ParsedReport(report=Report(day=day, day_part=day_part, price=price), used_tokens=used_tokens, total_tokens=total_tokens)

#
# Database
#

class Db(object):
    def __init__(self, fname):
        self._lock = asyncio.Lock()
        self._fname = fname
        self._connect()

    async def connect(self):
        async with self._lock:
            self._connect()

    def _connect(self):
        self._con = sqlite3.connect(self._fname)
        with self._con as cur:
            cur.execute('create table if not exists reports (user number, day number, day_part number, price number, constraint pk primary key (user, day, day_part))')
            cur.execute('create table if not exists maintenance (last_check_ts number)')
            for row in cur.execute('select last_check_ts from maintenance'):
                break
            else:
                cur.execute('insert into maintenance values(0)')

    async def close(self):
        async with self._lock:
            self._close()

    def _close(self):
        self._con.close()
        self._con = None

    async def dump(self):
        async with self._lock:
            return self._dump()

    def _dump(self):
        was_open = self._con is not None
        if was_open:
            self._close()
        try:
            with open(self._fname, 'rb') as f:
                contents = f.read()
            return contents
        finally:
            if was_open:
                self._connect()

    async def truncate(self):
        async with self._lock:
            return self._truncate()

    def _truncate(self):
        was_open = self._con is not None
        if was_open:
            self._close()
        try:
            with open(self._fname, 'wb'):
                pass
        finally:
            if was_open:
                self._connect()

    async def submit_report(self, user, report, replace):
        async with self._lock:
            return self._submit_report(user, report, replace)

    """
    @return old report
    """
    def _submit_report(self, user, report, replace):
        old = None
        with self._con as cur:
            for row in cur.execute('select price from reports where user = ? and day = ? and day_part = ?', (user, report.day, report.day_part)):
                old = Report(day=report.day, day_part=report.day_part, price=row[0])
            if old is None:
                cur.execute('insert into reports values(?, ?, ?, ?)', (user, report.day, report.day_part, report.price))
            elif replace:
                cur.execute('update reports set price = ? where user = ? and day = ? and day_part = ?', (report.price, user, report.day, report.day_part))
        return old

    async def get_user_reports(self, user):
        async with self._lock:
            return self._get_user_reports(user)

    def _get_user_reports(self, user):
        with self._con as cur:
            return [Report(*x) for x in cur.execute('select day, day_part, price from reports where user = ?', (user, ))]

    async def get_last_maintenance_time(self):
        async with self._lock:
            return self._get_last_maintenance_time()

    def _get_last_maintenance_time(self):
        for row in self._con.execute('select last_check_ts from maintenance'):
            return row[0]

    async def set_last_maintenance_time(self, ts):
        async with self._lock:
            return self._set_last_maintenance_time(ts)

    def _set_last_maintenance_time(self, ts):
        with self._con as cur:
            cur.execute('update maintenance set last_check_ts = ?', (ts, ))

#
# System
#

def current_day():
    now = datetime.datetime.now()
    day = (now.weekday() + 1) % 7
    return day

def current_day_part():
    now = datetime.datetime.now()
    day_part = int(now.hour >= 12)
    return day_part

#
# Browser
#

def reports_to_prices(reports):
    prices = [0] * 13
    for report in reports:
        index = 0 if report.day == 0 else report.day * 2 + report.day_part - 1
        prices[index] = report.price
    return '.'.join(map(str, prices))

def run_prediction(url, prices):
    driver = selenium.webdriver.Chrome()
    driver.set_window_size(1920, 5760)
    driver.implicitly_wait(10)
    try:
        driver.get(url + '?prices=' + prices)
        element = driver.find_element_by_class_name('nook-phone')
        with contextlib.closing(tempfile.NamedTemporaryFile(suffix='.png')) as tmp:
            element.screenshot(tmp.name)
            with open(tmp.name, 'rb') as f:
                content = f.read()
        return content
    finally:
        driver.quit()

