from bs4 import BeautifulSoup
from math import sqrt
import pandas
import pytz
# Replace urllib with aiohttp 
import urllib.request
import webcolors
from itertools import product
from datetime import datetime
from numpy.linalg import norm
# Do something with this because globals are naughty
base = "https://pso2.com/news/urgent-quests"
async def getUQPages():
    # def getUQPages():
    from re import match
    import aiohttp
    chars = "(),'"

    # What if the request fails?
    # r = urllib.request.urlopen(base)
    print("Fetching UQ pages...")
    async with aiohttp.ClientSession() as session:
        r = await fetch(session, base)
    print("Fetched!")
    # soup = BeautifulSoup(r.read(), features="html.parser")
    soup = BeautifulSoup(r, features="html.parser")
    lines = soup.findAll("a", {"class": "read-more"})
    # In general get onclick returns (ShowDetails("nextpage", "category"))
    # So we are looking for  (ShowDetails("uqMONTHYEARpartX", "emergency"))
    lines = list(map(lambda line: removeChars(line.get("onclick"), chars).split(), lines))
    # Isolate only the emergency quest schedule
    lines = list(filter(lambda line: line[-1] == "emergency", lines))
    # Take out the uqMONTHYEARpartX piece
    lines = list(map(lambda line: line[1], lines))
    # print(lines)
    # Get rid of anything that doesn't fit the eqMONTHYEARpartX format like.... "about"
    # lines = list(filter(lambda line: bool(match("^uq\\w+\\d+\\w+", line)), lines))
    # lines.extend(list(filter(lambda line: bool(match("^urgentquestschedule\\d+", line)), lines)))
    # Just say whatever and use try: for parsing the pages, if it fails assume it wasn't an eq page....
    print("Scraped {} pages!".format(len(lines)))
    return lines
    
def parseLargeTableHeader(allRows):
    # Determine the size of the header:
    head = 0
    for row in allRows:
        weeks = 0
        times = 0
        # Week or Time should mean auto skip...
        for td in row.findAll("td"):
            if "week" in str(td).lower():
                weeks += 1
            elif "time" in str(td).lower():
                times += 1
        if weeks != 0 or times != 0:
            # print("Weeks",weeks)
            # print("Times", times)
            head += 1
        if times != 0:
            break
    return head, times

def parseLargeTable(table):
    allRows = table.findAll("tr")[:]
    head, times = parseLargeTableHeader(allRows)       
    # Skip the table header and column header
    # print("Header rows:", head)
    # print("Time columns:", times)
    for row in allRows[head:]:
        # print("Row type:", type(row))
        elements = row.findAll("td")[:]
        # print("Elements type:", type(elements))
        # print("Elements len?:", len(elements))
        # print("Elements to list?", len(elements[:]))
        # for element in row.findAll("td")[1:]:
        # Puts the color into non-time columns
        for element in elements[times:]:
            if "background" in element['style']:
                # print(element['style'])
                # print(element['style'].split(";"))
                for s in element['style'].split(";"):
                    m = "background:"
                    if s[:len(m)] == m:
                        q = s.split(":")[1].strip()
                        q = removeChars(q, "(),").strip().split()
                        h = getColor(q).upper()
                        # They randomly label cells white.... why!
                        if h != "#FFFFFF":
                            # print(h)
                            element.string = h
    return table

def parseSmallTable(table):
    for row in table.findAll("tr"):
        # The color label tables only need data in the first column
        element = row.findAll("td")[0]
        if "background" in element['style']:
            # print(element)
            for s in element['style'].split(";"):
                m = "background:"
                if s[:len(m)] == m:
                    q = s.split(":")[1].strip()
                    q = removeChars(q, "(),").strip().split()
                    h = getColor(q).upper()
                    element.string = h
    return table


def getColor(args):
    if "rgb" in args:
        index = args.index("rgb") + 1
        rgbs = [int(x) for x in args[index:index+3]]
        color = webcolors.rgb_to_hex(rgbs)
    elif len(args) == 1:
        if args[0][0] == "#":
            color = args[0]
        else:
            # Name?
            try:
                color = webcolors.name_to_hex(args[0])
            # No idea what it is then...
            except:
                color = None
    else:
        # Multiple things in the background line surely one of them is hex or a word
        for a in args:
            if "#" == a[0]:
                try: 
                    # To confirm it is a real hex, convert to RGB and back
                    color = webcolors.rgb_to_hex(
                        webcolors.hex_to_rgb(a))
                    break
                except:
                    pass
            else:
                try:
                    color = webcolors.name_to_hex(a)
                    break
                except:
                    pass
                color = None
    return color

def getEventPages(events):
    # What happens if urllib fails?
    page_open = lambda page: urllib.request.urlopen("{}/{}".format(base, page))
    pages = list(map(lambda page: page_open(page), events))
    pages = list(map(lambda page: page.read(), pages))
    # for i, page in enumerate(pages):
        # with open(events[i], "wb") as outfile:
            # outfile.write(page)
    # Now download all the HTML pages associated with the given eqs
    return pages

def getTables(pages):
    soups = list(map(lambda page: BeautifulSoup(page, features="html.parser"), pages))
    tables = list(map(lambda soup: soup.findAll("table"), soups))
    # Insert the cell color into the large tables
    # The website goes
    # big table
    # small table
    # big table
    # small table
    # I guess we'll trust this for now
    for i, subtables in enumerate(tables):
        for j, subtable in enumerate(subtables):
            try:
                if j % 2 == 0:
                    # Big table
                    tables[i][j] = parseLargeTable(subtable)
                    # print(tables[i][j])
                else:
                    # Small table
                    tables[i][j] = parseSmallTable(subtable)
            except Exception as e:
                print("Failed to parse {}".format(j//2, ))
                print("Exception: ", e)
    # # Insert the color into the small tables
    # print(len(tables), len(tables[0]))
    return tables

def removeChars(s, chars):
    for c in chars:
        s = s.replace(c, " ")
    return s

def pageTablesToDataframes(tables):
    for i, subtables in enumerate(tables):
        for j, subtable in enumerate(subtables):
            # Big table
            if j % 2 == 0:
                t = pandas.read_html(subtable.prettify(), flavor="bs4")[0].fillna("")
                # Drop all time columns that are not empty or PDT
                times = t.iloc[2,:]
                toDrop = []
                for ind, col in enumerate(times):
                    if "Time" in col and "PDT" not in col:
                        toDrop.append(ind)
                # Empty lists are falsey
                if toDrop:
                    # print(t)
                    t.drop(t.columns[toDrop],axis=1,inplace=True)
                    # In this case we need to reset row/col index so later function do not break
                    t.reset_index(drop=True,inplace=True)
                    t.columns = range(t.shape[1])
                tables[i][j] = t
                # print(t)
            # Little table
            else:
                t = pandas.read_html(subtable.prettify(), flavor="bs4")[0].fillna("")
                # print("--- New Table ---")
                # print(t)
                # print("IS THIS REALLY BROKEN?")
                # print(t.iloc[0,1])
                if t.shape[0] == 1:
                    t = pandas.DataFrame(splitEQCategoryLine(t.iloc[0,:].copy())).T
                else:
                    t = t.apply(splitEQCategoryLine, axis=1)
                t = pandas.DataFrame(t.to_numpy(), columns=["hex", "category", "event", "duration"])
                t = t.apply(lambda row: row.apply(lambda x: x.strip()), axis=1)
                tables[i][j] = t
    return tables 

def splitEQCategoryLine(row):
    # print("THAT ROW")
    # print(row)
    cell = row[1].lower()
    cell = cell.split(":")
    if len(cell) == 1:
        print("splitEQCategoryLine imploded?")
        exit()
    category = cell[0]
    event = cell[1:]
    # event = removeChars(":".join(event), "()")
    event = ":".join(event)
    event = [x.strip() for x in event.split()]
    if "minutes)" in event:
        duration = event[-2:]
        event = event[:-2]
        event = [x.strip() for x in event]
        # duration = " ".join(event[-2:])
        duration = [removeChars(x, "()").strip() for x in duration]
        duration = " ".join(duration)
        event = " ".join(event)

        row[1] = category.title()
        row[2] = event.title()
        row[3] = duration
    else:
        event = " ".join(event)
        row[1] = category.title()
        row[2] = event.title()
        row[3] = ""
    return row

def assembleBetterTable(pageName, schedule, legend):
    columns = ["datetime", "hex"]# "category", "event", "duration", "hex"]
    year = pageName.split("part")[0][-4:]
    days  = schedule.iloc[0,1:].to_list()
    days  = [day.strip() for day in days]
    d = pandas.DataFrame({}, columns=columns)
    for i, row in schedule.iloc[3:,:].iterrows():
        for j, col in row.iloc[1:].iteritems():
            # Is there an event here? Should be a hex value if so
            if bool(col):
                # print(col)
                # print(row)
                # print(j)
                # Hex
                h = col
                # Date
                # j returned from iteritems() counts the first ignored column
                date = days[j-1]
                # Time
                tyme = row.iloc[0]
                # print(tyme)
                # Datetime
                dt = getDatetime([date, year, tyme])
                d = d.append({"datetime":dt, "hex":h, "fromPage": pageName}, ignore_index=True)
    
    # Use dataframe join to merge legend on hex
    # First determine what hexs in d are not in the legend...
    ud = pandas.Index(pandas.unique(d["hex"]))
    # We assume the legend is unique or we have nothing in this world we can trust
    badColors = ud.difference(legend["hex"])
    if len(badColors) != 0:
        goodColors = legend["hex"]
        fixedColors = []
        for badColor in badColors:
            goodColor = getClosestColor(badColor, goodColors)
            fixedColors.append(goodColor)
            w = d.copy()
            d.loc[d["hex"] == badColor, "hex"] = goodColor
        print("Naughty colors...", list(zip(badColors, fixedColors)), w, legend)
    d = d.join(legend.set_index("hex"), on="hex")
    # print(d)
    return d.drop_duplicates()

def getDatetime(args):
    # Expect 3 arguments for time
    # "%m/%d", "%y", "%I:%M %p"
    v = args[0].split("/")
    v.append(args[1])
    v.extend(args[2][:-2].split(":"))
    v.append(args[2][-2:])
    # If this fails, just assume the event was for this year,
    # Most likely failed because they didn't bother putting the year 
    # in the url
    try:
        value = "{:02d}/{:02d}/{} {:02d}:{:02d}{}".format(
                int(v[0]), int(v[1]), int(v[2]), int(v[3]), int(v[4]), v[5])
        value = datetime.strptime(value, '%m/%d/%Y %I:%M%p')
    except ValueError:
        value = "{:02d}/{:02d}/{} {:02d}:{:02d}{}".format(
                int(v[0]), int(v[1]), datetime.now().year, int(v[3]), int(v[4]), v[5])
        value = datetime.strptime(value, '%m/%d/%Y %I:%M%p')

    value = pytz.timezone("America/Los_Angeles").localize(value)
    return value

def getClosestColor(badColor, goodColors):
    # Get RGB
    badRGB =   webcolors.hex_to_rgb(badColor)
    goodRGBs = [webcolors.hex_to_rgb(x) for x in goodColors]
    distance = [euc(badRGB, RGB) for RGB in goodRGBs]
    match = goodRGBs[distance.index(min(distance))]
    match = webcolors.rgb_to_hex(match).upper()
    return match

def euc(v1, v2):
    return sqrt(sum(list(map(lambda i: (v1[i]-v2[i])**2, range(len(v1))))))

def combineAllFrames(eqs, allFrames):
    d = pandas.DataFrame({}, columns=["datetime", "category", "event", "duration", "hex"])
    for i, subframes in enumerate(allFrames):
        for j in range(0, len(subframes), 2):
            d = pandas.concat([d, assembleBetterTable(eqs[i], subframes[j], subframes[j+1])])
            d.reset_index()
    d.sort_values(by=["datetime", "category"], inplace=True, ascending=False)
    return d

# This function will go away once things transition to live updates and a database
def getAllEQs():
    uqEntries = getUQPages()
    pages = getEventPages(uqEntries)
    tables = getTables(pages)
    frames = pageTablesToDataframes(tables)
    final = combineAllFrames(uqEntries, frames)
    return final

def getSomeUQData(pageNames):
    pages = getEventPages(pageNames)
    tables = getTables(pages)
    frames = pageTablesToDataframes(tables)
    final = combineAllFrames(pageNames, frames)
    return final

# Figure out how to use aiohttp here...
# https://stackoverflow.com/questions/35879769/fetching-multiple-urls-with-aiohttp-in-python-3-5
async def getSomeUQDataAsync(pageNames):
    pages = await getEventPagesAsync(pageNames)
    tables = getTables(pages)
    frames = pageTablesToDataframes(tables)
    final = combineAllFrames(pageNames, frames)
    return final 

async def fetch(session, url):
    print("Fetching |{}| ...".format(url))
    async with session.get(url) as response:
        if response.status != 200:
            response.raise_for_status()
        return await response.text()

async def fetch_all(session, urls):
    import asyncio
    tasks = []
    for url in urls:
        task = asyncio.create_task(fetch(session, url))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return results

# async compatible
async def getEventPagesAsync(events):
    # What happens if urllib fails?
    import aiohttp
    pages = list(map(lambda page: "{}/{}".format(base, page), events))
    async with aiohttp.ClientSession() as session:
        pages = await fetch_all(session, pages) 
    return pages

if __name__ == "__main__":
    uqEntries = getUQPages()
    lines = uqEntries
    for i, line in enumerate(lines):
        print("{:02d} :: {}".format(i, line))
    pages = getEventPages(lines)
    tables = getTables(pages)
    frames = pageTablesToDataframes(tables)
   
    # for body in tables[0][0]:
        # body.unwrap()
    print(final)
    final.iloc[:,:-1].to_html("eqs.html", index=False)
