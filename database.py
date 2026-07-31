import sqlite3

db = sqlite3.connect(
    "database.db",
    check_same_thread=False,
)

cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users(

    telegram_id INTEGER PRIMARY KEY,

    phone TEXT,

    api_id INTEGER,

    api_hash TEXT,

    session_name TEXT

)
""")


db.commit()
