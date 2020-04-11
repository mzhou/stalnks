import asyncio
import calendar
import collections
import datetime
import re
import sqlite3

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
        async with self._locks:
            self._connect()

    def _connect(self):
        self._con = sqlite3.connect(self._fname)
        self._con.execute('create table if not exists reports (user number, day number, day_part number, price number, constraint pk primary key (user, day, day_part))')
        self._con.execute('create table if not exists maintenance (last_check_ts number)')

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
        self._close()
        try:
            with open(fname, 'rb') as f:
                contents = f.read()
            return contents
        finally:
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
            return [lambda x: Report(*x) for x in cur.execute('select day, day_part, price from reports where user = ?', (user, ))]

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
