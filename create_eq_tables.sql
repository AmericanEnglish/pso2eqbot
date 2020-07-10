-- Timezone will always be PDT
-- Datatypes should be changed when moving to a new database besides sqlite3
CREATE TABLE pso2na_timetable (
    datetime DATETIME,
    event    TEXT,
    category TEXT,
    hex      TEXT,
    duration INTEGER,
    fromPage TEXT,
    PRIMARY KEY (datetime, event)
);
