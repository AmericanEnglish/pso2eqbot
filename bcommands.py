from discord.ext import commands, tasks
from datetime import datetime, timedelta, date
import pandas
import pytz

from dataHelpers import getRequestedTimezone
from dataHelpers import getTodaysEvents
from dataHelpers import getTomorrowsEvents
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

    @commands.command()        
    async def get(self, ctx, *args):
        if "-tz" in args:
            tz = getDefaultTimezoneDB(self.conn, ctx.guild.id)
            await ctx.send("Default timezone set to {}".format(tz))

    async def setDefaultTimezone(self, ctx, *args):
        tz = getRequestedTimezone(*args)
        setDefaultTimezoneDB(self.conn, ctx.guild.id, tz)
        await ctx.send("Default timezone set to {}".format(tz))
class ActiveBackground(commands.Cog):
    def __init__(self, bot, conn):
        self.conn = conn
        self.bot  = bot
        self.updateViaWebpage.start()

    @tasks.loop(hours=24)
    async def updateViaWebpage(self):
        print("Updating database...")
        await updateForNewEvents(self.conn, where="webpage")
        print("Finished update")
