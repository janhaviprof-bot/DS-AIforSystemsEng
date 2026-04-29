# Python
#check rows in db file
import sqlite3, pandas as pd
db = sqlite3.connect("data/traffic.db")
print(pd.read_sql("SELECT * FROM traffic", db))
db.close()