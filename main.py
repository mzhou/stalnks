#!/usr/bin/env python3

import sys

import discord

import cfg
import stalnks

class Client(discord.Client):
    def __init__(self, db):
        super().__init__()
        self._db = db

    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        # only care about channel
        if message.channel.id != cfg.CHANNEL_ID:
            return
        # don't respond to ourselves
        if message.author == self.user:
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
            await message.channel.send('Recorded {price} bells at {day} {day_part}'.format(**report.pretty()._asdict()))
        elif replace:
            await message.channel.send('{day} {day_part} updated from {old_price} to {price}'.format(**report.pretty()._asdict(), old_price=old.price))

def main(argv):
    db = stalnks.Db(cfg.DB)
    client = Client(db)
    client.run(cfg.TOKEN)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

