import sqlalchemy
from sqlalchemy.orm import sessionmaker
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
        res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discord_table';")
        res = res.fetchall()
        if len(res) == 0:
            with open("create_discord_tables.sql", "r") as infile:
                conn.execute(infile.read())
    return conn

def updateForNewEvents(conn, where="webpage"):
    if where == "webpage":
        from numpy import setdiff1d
        from scraper import getUQPages, getSomeUQData
        pages = getUQPages()
        # Get all pages from the database
        with conn.begin():
            res = conn.execute("""SELECT DISTINCT fromPage FROM pso2na_timetable ;""")
        inDB = []
        for page in res.fetchall():
            inDB.append(page)
        missing = setdiff1d(pages, inDB)
        final = getSomeUQData(missing)
        final.to_sql("pso2na_timetable",conn, if_exists="append", index=False)

if __name__ == "__main__":
    # from scraper import getAllEQs
    conn = connectToDatabase()
    updateForNewEvents(conn, where="webpage")
