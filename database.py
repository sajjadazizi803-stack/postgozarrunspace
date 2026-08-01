import sqlite3
import os

# =========================
# مسیر دیتابیس در پوشه موقت (برای سرور)
# =========================

# برای اینکه دیگه هیچ خطای "file not defined" نگیری
DB_PATH = "database.db"

db = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = db.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    telegram_id INTEGER PRIMARY KEY,
    phone TEXT,
    api_id INTEGER,
    api_hash TEXT,
    session_name TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS transfers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    source_channel TEXT,
    target_channel TEXT,
    enabled INTEGER DEFAULT 1
)""")

db.commit()


def add_transfer(telegram_id, source_channel, target_channel):
    cursor.execute(
        """
        INSERT INTO transfers
        (telegram_id, source_channel, target_channel)
        VALUES (?, ?, ?)
        """,
        (telegram_id, source_channel, target_channel),
    )
    db.commit()


def get_user_transfers(telegram_id):
    cursor.execute(
        """
        SELECT id, source_channel, target_channel, enabled
        FROM transfers
        WHERE telegram_id=?
        """,
        (telegram_id,),
    )
    return cursor.fetchall()


def get_all_transfers():
    cursor.execute("""
        SELECT telegram_id,
               source_channel,
               target_channel,
               enabled
        FROM transfers
        """)
    return cursor.fetchall()


def delete_transfer(transfer_id):
    cursor.execute(
        """
        DELETE FROM transfers
        WHERE id=?
        """,
        (transfer_id,),
    )
    db.commit()


def set_transfer_enabled(transfer_id, enabled):
    cursor.execute(
        """
        UPDATE transfers
        SET enabled=?
        WHERE id=?
        """,
        (enabled, transfer_id),
    )
    db.commit()


# -------------------- get user -----------------------


def get_user(telegram_id):
    cursor.execute(
        """
        SELECT telegram_id,
               phone,
               api_id,
               api_hash,
               session_name
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )
    return cursor.fetchone()
