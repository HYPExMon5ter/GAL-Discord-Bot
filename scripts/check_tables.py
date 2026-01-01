import sqlite3

conn = sqlite3.connect('dashboard/dashboard.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = c.fetchall()
print('\n'.join([row[0] for row in tables]))
conn.close()
