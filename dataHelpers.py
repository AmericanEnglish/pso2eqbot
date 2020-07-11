from datetime import datetime, date, timedelta
from fuzzywuzzy import process
import pandas
import pytz
from sqlalchemy.sql.expression import text
pandas.set_option('colheader_justify', 'center')

def getTodaysEvents(db=None, *args):
    tz = getRequestedTimezone(*args)
    today = pytz.timezone("America/Detroit").localize(datetime.now())
    # Get the range in the user's timezone
    today = today.astimezone(tz)
    # 1/2 before right now will give us currently happening events
    before = today - timedelta(minutes=30)
    # Till the end of today -- make a today+ which displays into tomorrow near end of day
    end    = datetime(year=today.year, month=today.month, day=(today + timedelta(days=1)).day, hour=0, minute=0, second=0, microsecond=0)
    end    = tz.localize(end)
    d = getEventsDB(before, end, tz, db)
    if d.shape[0] != 0:
        # print(d)
        d = pandas.DataFrame(d[["date", "time", "event"]].to_numpy(), columns=["Date", "Time", "Event"])
        return "```\nTimezone: {}\n{}\n```".format(tz, d.to_string(index=False))
    else:
        return "No events schedule from {} to {}".format(
                before.strftime("%b, %d %I:%M%p %Z"),
                end.strftime("%b, %d %I:%M%p %Z"))

def getTomorrowsEvents(db=None, *args):
    tz = getRequestedTimezone(*args)
    today = pytz.timezone("America/Detroit").localize(datetime.now())
    today = today.astimezone(tz)
    tomorrow = today + timedelta(days=1)
    tomorrow = datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, 
            hour=0, minute=0, second=0, microsecond=0)
    before = tz.localize(tomorrow)
    end = datetime(year=tomorrow.year, month=tomorrow.month, day=(tomorrow + timedelta(days=1)).day, 
            hour=0, minute=0, second=0, microsecond=0)
    end = tz.localize(end)
    events = getEventsDB(before, end, tz, db)
    if events.shape[0] != 0:
        # print(d)
        events = pandas.DataFrame(events[["date", "time", "event"]].to_numpy(), columns=["Date", "Time", "Event"])
        return "```\nTimezone: {}\n{}\n```".format(tz, events.to_string(index=False))
    else:
        return "No events schedule from {} to {}".format(
                before.strftime("%b, %d %I:%M%p %Z"),
                end.strftime("%b, %d %I:%M%p %Z"))

def getEventsDB(before, end, tz, db):
    # Expects before and end to be in user's preferred tz
    # Given the "day range" in the users timezone we now need to convert BACK to PDT
    # so that we can search the database
    startPDT = before.astimezone(pytz.timezone("America/Los_Angeles"))
    endPDT =   end.astimezone(pytz.timezone("America/Los_Angeles"))
    # Search the DB
    with db.begin():
        res = db.execute(text("""
                SELECT datetime(datetime), event 
                FROM pso2na_timetable 
                WHERE :afterTime >= pso2na_timetable.datetime 
                AND   :beforeTime <= pso2na_timetable.datetime"""),
                {"beforeTime": startPDT, "afterTime": endPDT})
    res = res.fetchall()
    # Convert all time strings to datetime
    times = []
    for tyme in res:
        event = tyme[1]
        tyme = tyme[0]
        tyme = datetime.strptime(tyme, "%Y-%m-%d %H:%M:%S")
        tyme = pytz.timezone("America/Los_Angeles").localize(tyme)
        times.append((tyme, event))
    # Now chop them up and do the dataframe thing    
    d = pandas.DataFrame(times, columns=["datetime", "event"])
    # Now convert all times to the user's preferred zone
    d = d.apply(lambda row: addDateAndTimeString(row, tz), axis=1)
    return d

def getRequestedTimezone(*args):
    # Maintain a lazy list for easy reference
    shortcuts = {"PDT": "America/Los_Angeles",
            "PST": "America/Los_Angeles",
            "EDT": "America/Detroit",
            "CDT": "America/Chicago",
            "CST": "America/Chicago",
            "MDT": "MST"}
    if "-tz" in args:
        tz = "_".join(args[args.index("-tz")+1:])
    else:
        tz = shortcuts["PDT"]

    if tz in pytz.all_timezones:
        tz = pytz.timezone(tz)
    elif tz in shortcuts.keys():
        tz = pytz.timezone(shortcuts[tz])
    else:
        tz = pytz.timezone(shortcuts["PDT"])
    return tz

def getEvents(startTime, endTime, tz):
    # Now get info from the dataframe
    d = eqs.copy()
    # print(d)
    d = d.loc[(endTime >= d["datetime"]) & (d["datetime"] >= startTime)]
    # print(d)
    d = d.apply(lambda row: addDateAndTimeString(row, tz), axis=1)
    if d.shape[0] > 0:
        d = d[["date", "time", "event"]]
        d = pandas.DataFrame(d.to_numpy(), columns=["Date", "Time", "Event"])
        return "```\nTimezone: {}\n{}\n```".format(tz, d.to_string(index=False))
    else:
        return "No events schedule from {} to {}".format(
                before.strftime("%b, %d %I:%M%p %Z"),
                end.strftime("%b, %d %I:%M%p %Z"))

def addDateAndTimeString(row, tz):
    row["date"] = row["datetime"].astimezone(tz).strftime("%b, %d")
    row["time"] = row["datetime"].astimezone(tz).strftime("%I:%M%p")
    return row

def getNotifications(conn, minutesOut=60, rightNow=True):
    now = datetime.now()
    now = pytz.timezone("America/Detroit").localize(now)
    now = now.astimezone(pytz.timezone("America/Los_Angeles"))
    if rightNow:
        start = now - timedelta(minutes=30)
    else:
        start = now
    end = now + timedelta(minutes=minutesOut)
    with conn.begin():
        res = conn.execute(text(
            """SELECT datetime(datetime), event, category FROM pso2na_timetable 
            WHERE :end >= pso2na_timetable.datetime
            AND pso2na_timetable.datetime >= :start;"""),
                {"end": end, "start": start})
    res = res.fetchall()
    # If you want customizble intervals this section has to change 
    interval = [60, 15, 0]
    base = "The {} {} is happenning {}"
    # print(start)
    # print(now)
    # print(end)
    # print(res)
    toSend = []
    for dt, event, category in res:
        tyme = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        lnow = datetime(year=now.year, month=now.month, day=now.day, hour=now.hour, minute=now.minute, second=0)
        diff = tyme - lnow
        # print(diff, type(diff))
        # print(timedelta(minutes=30) == timedelta(minutes=30))
        if diff == timedelta(minutes=interval[0]):
            toSend.append(base.format(category, event, "in {} minutes!".format(interval[0])))
        elif diff == timedelta(minutes=interval[1]):
            toSend.append(base.format(category, event, "in {} minutes!".format(interval[1])))
        elif diff == timedelta(minutes=interval[2]):
            toSend.append(base.format(category, event, "now!"))
    # print(toSend)
    return toSend[::-1]
