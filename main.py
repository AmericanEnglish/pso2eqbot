import discord
import logging
from scraper import getAllEQs

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

if __name__ == "__main__":
    from discord.ext import commands
    from bcommands import today, tomorrow
    # client = discord.Client()
    bot = commands.Bot(command_prefix='::')

    bot.add_command(today)
    bot.add_command(tomorrow)
    with open("token.txt", "r") as infile:
        bot.run(infile.read())
