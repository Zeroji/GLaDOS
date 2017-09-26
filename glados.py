#!/usr/bin/env python
import asyncio
import datetime
import discord
from utils import *


interaction_cool_down = datetime.timedelta(seconds=120)
neurotoxin_cool_down = datetime.timedelta(seconds=180)


# noinspection PyUnresolvedReferences
class GlaDOS(discord.Client):
    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)
        self.interactions = {}  # CID:{UID:timestamp} mapping of last interactions
        self.neurotoxin = {}  # CID:timestamp mapping of when to stop

    async def on_member_join(self, member: discord.Member):
        server: discord.Server = member.server
        text = format_line('welcome', user_mention=member.mention, server=server.name)
        text += '\n' + format_line('about-self', client=server.me.display_name)
        text += '\n' + get_line('about-welcome')
        if server.verification_level in (discord.VerificationLevel.medium, discord.VerificationLevel.high):
            if server.verification_level == discord.VerificationLevel.medium:
                key = 'welcome-verification-medium'
                wait = datetime.timedelta(seconds=5*60) - (datetime.datetime.utcnow() - member.created_at)
            else:
                key = 'welcome-verification-high'
                wait = datetime.timedelta(seconds=10*60) - (datetime.datetime.utcnow() - member.joined_at)
            if wait.total_seconds() > 0:
                text += ' ' + format_line(key, time=human_duration(wait.total_seconds()))
                text += ' ' + get_line('welcome-verification-account')
        await self.send_message(server.default_channel, text)

    async def on_ready(self):
        print('Logged in as %s' % self.user.name)

    def interact(self, message: discord.Message):
        if len(message.mentions) > 0:
            allow = self.user in message.mentions  # block if another mention is present
        else:
            allow = self.is_allowed(message) or contains_list(message.content, 'name')
        (self.inter_allow if allow else self.inter_block)(message)
        return allow

    def is_allowed(self, message: discord.Message):
        chan = message.channel.id
        if chan in self.interactions:
            user = message.author.id
            if user in self.interactions.get(chan):
                return message.timestamp - self.interactions.get(chan).get(user) <= interaction_cool_down
        return False

    def inter_block(self, message: discord.Message):
        chan = message.channel.id
        if chan not in self.interactions:
            return
        if message.author.id in self.interactions.get(chan):
            self.interactions.get(chan).pop(message.author.id)

    def inter_allow(self, message: discord.Message):
        chan = message.channel.id
        if chan not in self.interactions:
            self.interactions[chan] = {}
        self.interactions.get(chan)[message.author.id] = message.timestamp

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        def send(*args, **kwargs):  # makes things nicer and a tiny bit faster maybe
            if len(args) > 0 and isinstance(args[0], str) and len(args[0]) == 0:
                return
            self.loop.create_task(self.send_message(message.channel, *args, **kwargs))

        if message.channel.id in self.neurotoxin:
            cid = message.channel.id
            if message.timestamp > self.neurotoxin.get(cid) + neurotoxin_cool_down:
                self.neurotoxin.pop(cid)
                send(get_line("neurotoxin-disabled"))
            else:
                self.loop.create_task(delay(random.randint(1, 5), self.delete_message(message)))
                return

        if not self.interact(message):
            return

        def contains(w_list):
            return contains_list(message.content, w_list)

        tell = contains('tell')
        question = contains('question') and '?' in message.content[-5:]
        channel_names = {}
        for cid in C:
            chan = self.get_channel(cid)
            if chan is not None:
                channel_names[cid] = chan
                channel_names[chan.name] = chan
        bot_names = {}
        for uid in B:
            bot = message.server.get_member(uid)
            if bot is not None and bot.bot:
                bot_names[uid] = bot
                bot_names[bot.name] = bot
                if bot.nick is not None:
                    bot_names[bot.nick] = bot

        if contains('greeting'):
            send(format_line('greeting', message))
        elif contains('help'):
            send(format_line('about-self', client=message.server.me.display_name) + '\n' + get_line('about-help'))
        elif tell or question:
            channels = set()
            bots = set()
            if len(message.channel_mentions) > 0:
                channels.update(message.channel_mentions)
            if len(message.mentions) > 0:
                bots.update(message.mentions)
            for word in message.content.split():
                for name, chan in channel_names.items():
                    if lev_close(word.strip('#'), name):
                        channels.add(chan)
                for name, bot in bot_names.items():
                    if lev_close(word.strip('@'), name):
                        bots.add(bot)
            text = ''
            if len(channels) == 0 and contains('channel'):
                text += '\n' + get_line('channels-list')
                channels = {self.get_channel(cid) for cid in C}
            channels = list(channels)
            channels.sort(key=lambda channel: channel.position)
            for chan in channels:
                if chan is None or chan.id not in C:
                    continue
                if chan.server == message.server:
                    text += '\n' + chan.mention + ' ' + get_line(chan.id, src=C)
            bot_text = len(bots) == 0 and contains('bots')
            if bot_text:
                text += '\n' + get_line('bot-list')
                bots = {message.server.get_member(uid) for uid in B}
            for bot in bots:
                if bot is None or not bot.bot or bot.id not in B:
                    continue
                text += '\n' + bot.mention + ' ' + get_line(bot.id, src=B)
                prefixes = B.get(bot.id).get('prefix', [])
                if len(prefixes) > 0:
                    text += ' (prefix%s: %s)' % ('es' if len(prefixes) > 1 else '', pretty(prefixes, formatting='`%s`'))
            if len(bots) > 0:
                text += '\n' + format_line('bot-hosted',
                                           bot_list=pretty([bot.mention for bot in bots if bot is not None
                                                            and bot.id in B and B.get(bot.id).get('hosted')]))
            send(text.strip())
        elif contains('neurotoxin') and ('manage_messages', True) in message.channel.permissions_for(message.author):
            self.neurotoxin[message.channel.id] = message.timestamp
            send(get_line("neurotoxin"))
        elif contains('stop'):
            self.inter_block(message)
            return
        elif contains('name') or self.user in message.mentions:
            send(format_line('greeting', message))
        else:
            if len(message.content) >= 8:
                send(format_line('unknown', message))

async def delay(seconds, coro):
    await asyncio.sleep(seconds)
    await coro

if __name__ == '__main__':
    GlaDOS().run(open('data/secret/token').read().strip())
