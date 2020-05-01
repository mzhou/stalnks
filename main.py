#!/usr/bin/env python3

import asyncio
import collections
import datetime
import io
import sys
import time

import discord

import cfg
import stalnks

class Client(discord.Client):
    def __init__(self, db):
        super().__init__()
        self._db = db
        self._lock = asyncio.Lock()
        self._predict_tasks = asyncio.Queue()

    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        async with self._lock:
            return await self._on_message(message)

    async def _on_message(self, message):
        # only care about channel
        if message.channel.id != cfg.CHANNEL_ID:
            return
        # don't respond to ourselves
        if message.author == self.user:
            return

        # dump
        if message.content == 'dump':
            await self._dump()
            return

        print(repr(message))
        print(repr(message.content))
        # <Message id=698391425347485717 channel=<TextChannel id=698387890102861915 name='bot-sandbox' position=6 nsfw=False news=False category_id=692322326796042311> type=<MessageType.default: 0> author=<Member id=129173256417574912 name='mz' discriminator='5687' bot=False nick=None guild=<Guild id=692322326796042310 name='animal crossing circlejerk' shard_id=None chunked=True member_count=16>> flags=<MessageFlags value=0>>

        input_report, used_tokens, total_tokens = stalnks.parse_report(message.content)
        print(repr(input_report))

        # probably not a report if there's too much other crap
        if total_tokens - used_tokens >= 3:
            return

        # no price no deal
        if input_report.price is None:
            return

        report = input_report

        # sunday is always am
        if report.day == 0:
            if report.day_part is not None and report.day_part != 0:
                return
            report = report._replace(day_part=0)

        print(repr(report))
        day_specified = report.day is not None
        day_part_specified = report.day_part is not None
        day_consistent = day_specified == day_part_specified
        if not day_consistent:
            return

        replace = day_specified

        # fill in date if needed
        if not day_specified:
            report = report._replace(day=stalnks.current_day(), day_part=stalnks.current_day_part())

        # sunday is always am, again
        if report.day == 0:
            if report.day_part is not None and report.day_part != 0:
                return
            report = report._replace(day_part=0)

        print('submit_report({})'.format(report))
        old = await self._db.submit_report(message.author.id, report, replace=replace)
        if old is None:
            first_line = message.channel.send('Recorded {price} bells at {day} {day_part}'.format(**report.pretty()._asdict()))
        elif replace:
            first_line = message.channel.send('{day} {day_part} updated from {old_price} to {price}'.format(**report.pretty()._asdict(), old_price=old.price))
        else:
            return

        # do the table
        user_reports = await self._db.get_user_reports(message.author.id)
        prices = stalnks.reports_to_prices(user_reports)

        # run the web page in background
        async def predict():
            return await stalnks.run_prediction(cfg.WEBROOT, prices)
        # function to run in order of requested prediction
        async def reply(png):
            await first_line
            await message.channel.send(file=discord.File(io.BytesIO(png), 'prediction.png'))
            await message.channel.send('https://turnipprophet.io/?prices=' + prices)
        await self._predict_tasks.put((self.loop.create_task(predict()), reply))

    async def _dump(self):
        db_bin = await self._db.dump()
        await self.get_channel(cfg.CHANNEL_ID).send(file=discord.File(io.BytesIO(db_bin), 'db.sqlite3'))

    async def background_task(self):
        await self.wait_until_ready()
        while True:
            async with self._lock:
                await self._background_work()
            await asyncio.sleep(60)

    async def _background_work(self):
        now_ts = time.time()
        last_ts = await self._db.get_last_maintenance_time()
        if last_ts == 0:
            await self._db.set_last_maintenance_time(now_ts)
            return

        now_day = (datetime.datetime.fromtimestamp(now_ts).weekday() + 1) % 7
        last_day = (datetime.datetime.fromtimestamp(last_ts).weekday() + 1) % 7
        if now_day == 0 and last_day != 0:
            await self._rollover()

        await self._db.set_last_maintenance_time(now_ts)

    async def predict_replier(self):
        await self.wait_until_ready()
        while True:
            task, reply = await self._predict_tasks.get()
            png = await task
            async with self._lock:
                await reply(png)

    async def _rollover(self):
        await self._db.close()
        await self.get_channel(cfg.CHANNEL_ID).send('Rolling over database for new week')
        await self._dump()
        await self._db.truncate()
        await self._db.connect()

def main(argv):
    db = stalnks.Db(cfg.DB)
    client = Client(db)
    client.loop.create_task(client.background_task())
    client.loop.create_task(client.predict_replier())
    client.run(cfg.TOKEN)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

