import sqlalchemy
from datetime import datetime
import pytz
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import text
def connectToDatabase():
    # First connect
    engine = sqlalchemy.create_engine("sqlite:///pso2na_eq.db")
    # conn = sqlite3.connect("pso2na_eq.db")
    conn = engine.connect()
    conn.execution_options(autocommit=False)
    # See if the tables exist
    with conn.begin():
        res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pso2na_timetable';")
        res = res.fetchall()
        if len(res) == 0:
            with open("create_eq_tables.sql", "r") as infile:
                conn.execute(infile.read())
            # engine.commit()
        res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discord_guild_table';")
        res = res.fetchall()
        if len(res) == 0:
            with open("create_discord_tables.sql", "r") as infile:
                tables = infile.read().split(";")
                for table in tables:
                    conn.execute(table+";")
    return conn

async def updateForNewEvents(conn, where="webpage"):
    if where == "webpage":
        from numpy import setdiff1d
        from scraper import getUQPages, getSomeUQDataAsync
        pages = await getUQPages()
        print("found: ", pages)
        # Get all pages from the database
        with conn.begin():
            res = conn.execute("""SELECT DISTINCT fromPage FROM pso2na_timetable ;""")
        inDB = []
        for page in res.fetchall():
            inDB.append(page)
        print("inDB: ", inDB)
        missing = setdiff1d(pages, inDB)
        print("missing:", missing)
        final = await getSomeUQDataAsync(missing)
        # print(type(final))
        while True:
            try:
                final.to_sql("pso2na_timetable",conn, if_exists="append", index=False)
                break
            except Exception as e:
                print("Failed to update db because {}".format(e))

def setDefaultTimezoneDB(conn, guild, tz):
    # Check is guild already has a default timezone
    res = getDefaultTimezoneDB(conn, guild)
    # If it does not, insert it
    if res is None:
        with conn.begin():
            conn.execute(text("INSERT INTO discord_guild_table VALUES (:guild_id, NULL, :tz)"), {"guild_id": guild, "tz": str(tz)})
    # If it does, overwrite it
    else:
        with conn.begin():
            conn.execute(
                    text("""UPDATE discord_guild_table SET timezone = :tz 
                        WHERE discord_guild_table.guild_id = :guild"""), {"tz": str(tz), "guild": guild})

def getDefaultTimezoneDB(conn, guild):
    # Check if guild is already 
    with conn.begin():
        res = conn.execute(text("SELECT timezone FROM discord_guild_table WHERE discord_guild_table.guild_id=:gid;"),
                {"gid": guild})
    res = res.fetchall()
    if len(res) == 0:
        return None
    else:
        return res[0][0]

def setDefaultChannelDB(conn, guild, channel):
    # Check is guild already has a default timezone
    res = getDefaultChannelDB(conn, guild)
    # If it does not, insert it
    if res is None:
        with conn.begin():
            conn.execute(text("INSERT INTO discord_guild_table VALUES (:guild_id, :default, NULL)"), {"guild_id": guild, "default": str(channel)})
    # If it does, overwrite it
    else:
        with conn.begin():
            conn.execute(
                    text("""UPDATE discord_guild_table SET default_channel_id = :channel 
                        WHERE discord_guild_table.guild_id = :guild"""), {"channel": str(channel), "guild": guild})

def getDefaultChannelDB(conn, guild):
    with conn.begin():
        res = conn.execute(text("SELECT guild_id, default_channel_id FROM discord_guild_table WHERE discord_guild_table.guild_id=:gid;"),
                {"gid": guild})
    res = res.fetchall()
    # print("default channel:", res)
    if len(res) == 0:
        return None
    else:
        return res[0]
    
def getToBeUpdated(conn):
    # Get datetime
    today = datetime.now()
    today = pytz.timezone("America/Detroit").localize(today)
    # Need this for comparing
    # eleven = datetime(year=today.year, month=today.month, day=today.day, hour=11, minute=0, second=0)
    # Get all guilds, timezones, and when last updated
    with conn.begin():
        res = conn.execute(text("SELECT guild_id, default_channel_id, timezone FROM discord_guild_table;"))
    res = res.fetchall()
    # Convert my datetime to all timezones
    toBeUpdated = []
    for g in res:
        guild, default_channel_id, timezone = g
        # Create a local timezone
        timezone = pytz.timezone(timezone)
        # Shift the detroit time to local time
        local_day = today.astimezone(timezone)

        # Delete the minutes and seconds
        local_day = datetime(year=local_day.year, month=local_day.month, day=local_day.day, 
                hour=local_day.hour, minute=local_day.minute, second=0)
        local_day = timezone.localize(local_day)
        eleven = datetime(year=today.year, month=today.month, day=today.day, hour=23, minute=0, second=0)
        eleven = timezone.localize(eleven)
        # If new datetime is at 11pm local time
        # if eleven == local_day:
        # print(timezone)
        # print(eleven)
        # print(local_day)
        if eleven == local_day and default_channel_id is not None:
            toBeUpdated.append(g)
    return toBeUpdated

def getAllGuilds(conn):
    # Possibly add a notifcation option where you opt in or out of it
    # So then expand this statement to include a where associated with that bool
    with conn.begin():
        res = conn.execute("""SELECT guild_id, default_channel_id FROM discord_guild_table;""")
    res = res.fetchall()
    return res

if __name__ == "__main__":
    # from scraper import getAllEQs
    conn = connectToDatabase()
    updateForNewEvents(conn, where="webpage")
