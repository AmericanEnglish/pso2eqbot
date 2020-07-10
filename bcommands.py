from discord.ext import commands
from datetime import datetime, timedelta, date
import pandas
import pytz


from dataHelpers import getTodaysEvents
from dataHelpers import getTomorrowsEvents

@commands.command()
async def today(ctx, *args):
    await ctx.send(getTodaysEvents(*args))

@commands.command()
async def tomorrow(ctx, *args):
    await ctx.send(getTomorrowsEvents(*args))
