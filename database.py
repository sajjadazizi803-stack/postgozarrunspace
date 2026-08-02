import sqlite3

DB_PATH = "database.db"

db = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = db.cursor()

# ================= USERS =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    telegram_id INTEGER PRIMARY KEY,
    phone TEXT,
    api_id INTEGER,
    api_hash TEXT,
    session_name TEXT
)
""")

# ================= TRANSFERS =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS transfers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    source_channel TEXT,
    target_channel TEXT,
    enabled INTEGER DEFAULT 1,
    sent_count INTEGER DEFAULT 0,
    last_send TEXT,
    remove_last_lines INTEGER DEFAULT 0,
    append_last_lines TEXT DEFAULT ''
)
""")

db.commit()


# ================= add Transfers =================


def add_transfer(telegram_id, source_channel, target_channel):

    cursor.execute(
        """
        INSERT INTO transfers
        (telegram_id, source_channel, target_channel)
        VALUES (?, ?, ?)
        """,
        (
            telegram_id,
            source_channel,
            target_channel,
        ),
    )

    db.commit()

    return cursor.lastrowid


# ------------------- get user transfers ------------------


def get_user_transfers(telegram_id):

    cursor.execute(
        """
        SELECT
            id,
            source_channel,
            target_channel,
            enabled,
            sent_count,
            last_send,
            remove_last_lines,
            append_last_lines
        FROM transfers
        WHERE telegram_id=?
        ORDER BY id DESC
        """,
        (telegram_id,),
    )

    return cursor.fetchall()


# ------------------- get all transfers ------------------


def get_all_transfers():
    cursor.execute("""
        SELECT
            id,
            telegram_id,
            source_channel,
            target_channel,
            enabled
        FROM transfers
    """)
    return cursor.fetchall()


# ------------------- delete transfer ------------------


def delete_transfer(transfer_id):
    cursor.execute(
        "DELETE FROM transfers WHERE id=?",
        (transfer_id,),
    )
    db.commit()


# ------------------- set tranfer enabled ------------------


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


# ------------------- set remove last lines ------------------


def set_remove_last_lines(
    transfer_id,
    count,
):

    cursor.execute(
        """
        UPDATE transfers
        SET remove_last_lines=?
        WHERE id=?
        """,
        (
            count,
            transfer_id,
        ),
    )

    db.commit()


# ------------------- get remove last lines ------------------


def get_remove_last_lines(transfer_id):

    cursor.execute(
        """
        SELECT remove_last_lines
        FROM transfers
        WHERE id=?
        """,
        (transfer_id,),
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0


# ------------------- increase sent count ------------------
def increase_sent_count(transfer_id):
    cursor.execute(
        """
        UPDATE transfers
SET sent_count = sent_count + 1,
    last_send = datetime('now', '+3 hours', '+30 minutes')
WHERE id=?
        """,
        (transfer_id,),
    )
    db.commit()


# ================= User =================


def get_user(telegram_id):
    cursor.execute(
        """
        SELECT
            telegram_id,
            phone,
            api_id,
            api_hash,
            session_name
        FROM users
        WHERE telegram_id=?
        """,
        (telegram_id,),
    )
    return cursor.fetchone()


# ------------------- set append last lines ------------------


def set_append_last_lines(
    transfer_id,
    text,
):
    cursor.execute(
        """
        UPDATE transfers
        SET append_last_lines=?
        WHERE id=?
        """,
        (
            text,
            transfer_id,
        ),
    )

    db.commit()


# ------------------- get append last lines ------------------


def get_append_last_lines(transfer_id):

    cursor.execute(
        """
        SELECT append_last_lines
        FROM transfers
        WHERE id=?
        """,
        (transfer_id,),
    )

    result = cursor.fetchone()

    if result:
        return result[0] or ""

    return ""


# ================= SUPPORT =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS support_messages(
    admin_message_id INTEGER PRIMARY KEY,
    user_id INTEGER
)
""")

db.commit()


def add_support_message(admin_message_id, user_id):

    cursor.execute(
        """
        INSERT OR REPLACE INTO support_messages
        (admin_message_id, user_id)
        VALUES (?, ?)
        """,
        (
            admin_message_id,
            user_id,
        ),
    )

    db.commit()


def get_support_user(admin_message_id):

    cursor.execute(
        """
        SELECT user_id
        FROM support_messages
        WHERE admin_message_id=?
        """,
        (admin_message_id,),
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    return None
