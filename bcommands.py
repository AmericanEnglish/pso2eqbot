from discord.ext import commands, tasks
import asyncio
import discord
from datetime import datetime, timedelta, date
import pandas
import pytz

from dataHelpers import getRequestedTimezone
from dataHelpers import getTodaysEvents
from dataHelpers import getTomorrowsEvents
from dataHelpers import getNotifications
from databaseCommands import *

class TimeCommands(commands.Cog):
    def __init__(self, bot, conn):
        self.bot = bot
        self.conn = conn

    @commands.command()
    async def today(self, ctx, *args):
        # print(args)
        if "-tz" not in args:
            tz = getDefaultTimezoneDB(self.conn, ctx.guild.id)
            if tz is not None:
                args = list(args)
                args.append("-tz")
                args.append(str(tz))
        await ctx.send(getTodaysEvents(self.conn, *args))

    @commands.command()
    async def tomorrow(self, ctx, *args):
        if "-tz" not in args:
            tz = getDefaultTimezoneDB(self.conn, ctx.guild.id)
            if tz is not None:
                args = list(args)
                args.append("-tz")
                args.append(str(tz))
        await ctx.send(getTomorrowsEvents(self.conn, *args))
    
    @commands.command()
    async def set(self, ctx, *args):
        if "-tz" in args:
            await self.setDefaultTimezone(ctx, *args)
        elif "-ch" in args:
            await self.setDefaultChannel(ctx, *args)

    @commands.command()        
    async def get(self, ctx, *args):
        if "-tz" in args:
            tz = getDefaultTimezoneDB(self.conn, ctx.guild.id)
            await ctx.send("Default timezone set to {}".format(tz))
        elif "-ch" in args:
            channel = getDefaultChannelDB(self.conn, ctx.guild.id)[1]
            print(channel)
            # channel = self.bot.get_channel(int(channel[2:-1]))
            await ctx.send("Default channel set to {}".format(channel))

    async def setDefaultChannel(self, ctx, a: str, channel: discord.TextChannel, *args):
        setDefaultChannelDB(self.conn, ctx.guild.id, channel)
        await ctx.send("Default channel set to {}".format(channel))

    async def setDefaultTimezone(self, ctx, *args):
        tz = getRequestedTimezone(*args)
        setDefaultTimezoneDB(self.conn, ctx.guild.id, tz)
        await ctx.send("Default timezone set to {}".format(tz))


class ActiveBackground(commands.Cog):
    def __init__(self, bot, conn):
        self.conn = conn
        self.bot  = bot
        self.updateViaWebpage.start()
        self.dailyReminder.start()
        self.eventReminder.start()

    @tasks.loop(hours=24)
    async def updateViaWebpage(self):
        print("Updating database...")
        await updateForNewEvents(self.conn, where="webpage")
        print("Finished update")
    
    @tasks.loop(seconds=60, count=None)
    async def dailyReminder(self):
        # post tomorrows schedule
        # print("Checking daily reminder...")
        update = getToBeUpdated(self.conn)
        # print(update)
        for guild_id, default_channel_id, timezone in update:
            if default_channel_id is not None:
                channel = self.bot.get_channel(int(default_channel_id[2:-1]))
                await channel.send(getTomorrowsEvents(self.conn, *['-tz', timezone]))
        # print("Finished sending reminder.")

    @dailyReminder.before_loop
    async def beforeReminder(self):
        # print("Daily Reminder waiting...")
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60, count=None)
    async def eventReminder(self):
        # print("Reminding....")
        notifications = getNotifications(self.conn, minutesOut=60, rightNow=True)
        # print("Notifications....", notifications)
        # print("Notify:", update)
        if len(notifications) == 0:
            update = getAllGuilds(self.conn)
            for guild_id, default_channel_id in update:
                if default_channel_id is not None:
                    channel = self.bot.get_channel(int(default_channel_id[2:-1]))
                    for n in notifications:
                        await channel.send(n)
        # print("Finished reminding!")

    @eventReminder.before_loop
    async def beforeEventReminder(self):
        print("Event Reminder waiting...")
        await self.bot.wait_until_ready()

class Cleanup(commands.Cog):
    def __init__(self, bot, conn):
        self.conn = conn
        self.bot  = bot

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        # Remove them from the DB
        pass
