from datetime import datetime, date, timedelta
from fuzzywuzzy import process
import pandas
import pytz

pandas.set_option('colheader_justify', 'center')

from scraper import getAllEQs
eqs = getAllEQs()

def query(args, eqFrame):
    from datetime import datetime, date, timedelta
    import pytz
    import pandas
    arg = " ".join(args)
    # First select all unique events

    events = unique(eqFrame["event"])
    # Then fuzzy match using input
    eventMatches = process.extract(arg, events)
    _, p = tuple(zip(*eventMatches))
    m = max(p)
    # Gather all matches
    matches = []
    for item in eventMatches:
        if item[1] == m:
            matches.append(item[0])
    
    # Return a nicely formatting table...?
    d = eqFrame.copy()
    d = d.loc[d.event.isin(matches)]
    # Limit it for today 
    # Should return today at 00:00
    today = datetime.combine(date.today(), datetime.min.time())
    today = pytz.timezone("America/Detroit").localize(today)
    d = d.loc[(today + timedelta(days=1) >= d["datetime"]) & (d["datetime"] >= today)]
    d = pandas.DataFrame(d.to_numpy()[:,:-1], columns=["Date & Time", "Event Type", "Event", "Duration"])
    return "```\n{}\n```".format(d.to_string(index=False))

def getTodaysEvents(*args):
    tz = getRequestedTimezone(*args)
    # Get server today
    today = pytz.timezone("America/Detroit").localize(datetime.now())
    # Get requested timezone today
    today = today.astimezone(tz)
    # 1/2 before right now will give us currently happening events
    before = today - timedelta(minutes=30)
    # Till the end of today -- make a today+ which displays into tomorrow near end of day
    end    = datetime(year=today.year, month=today.month, day=(today + timedelta(days=1)).day, hour=0, minute=0, second=0, microsecond=0)
    end    = tz.localize(end)
    # This is a string
    events = getEvents(before, end, tz)
    return events

def getTomorrowsEvents(*args):
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
    events = getEvents(before, end, tz)
    return events

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
        return "```\n{}\n```".format(d.to_string(index=False))
    else:
        return "No events schedule from {} to {}".format(
                before.strftime("%b, %d %I:%M%p %Z"),
                end.strftime("%b, %d %I:%M%p %Z"))

def addDateAndTimeString(row, tz):
    row["date"] = row["datetime"].astimezone(tz).strftime("%b, %d")
    row["time"] = row["datetime"].astimezone(tz).strftime("%I:%M%p")
    return row
