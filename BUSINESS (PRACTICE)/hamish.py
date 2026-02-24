import sqlite3

db = sqlite3.connect('Business.db')

query = 'Select * From Orders'

cursor = db.cursor()

cursor.execute(query)

print(cursor.fetchall())