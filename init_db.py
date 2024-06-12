import sqlite3

connection = sqlite3.connect('database.db')


with open('schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

cur.execute("INSERT INTO accounts (username, password, email, role) VALUES (?, ?, ?, ?)",
            ('test', '0ef15de6149819f2d10fc25b8c994b574245f193', 'test@test.com', 1)
            )

connection.commit()
connection.close()