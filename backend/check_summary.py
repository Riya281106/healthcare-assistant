import sqlite3

con = sqlite3.connect('healthcare.db')
rows = con.execute("SELECT * FROM conversation_summaries").fetchall()
print(rows)
con.close()