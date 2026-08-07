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

cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts(

    user_id INTEGER PRIMARY KEY,

    api_id TEXT,
    api_hash TEXT,

    phone TEXT,

    session TEXT
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


def update_transfer_source(transfer_id, new_source):

    cursor.execute(
        """
        UPDATE transfers
        SET source_channel=?
        WHERE id=?
        """,
        (
            new_source,
            transfer_id,
        ),
    )

    db.commit()


def update_transfer_target(transfer_id, new_target):

    cursor.execute(
        """
        UPDATE transfers
        SET target_channel=?
        WHERE id=?
        """,
        (
            new_target,
            transfer_id,
        ),
    )

    db.commit()


def get_transfer_by_id(transfer_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM transfers
        WHERE id = ?
        """,
        (transfer_id,),
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)


# ================= ADVERTISING GROUPS =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS advertising_groups(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    group_username TEXT,
    group_id INTEGER,
    title TEXT,
    interval_minutes INTEGER DEFAULT 10,
    enabled INTEGER DEFAULT 0,
    message_type TEXT DEFAULT 'text',
    message_text TEXT,
    forward_chat_id INTEGER,
    forward_message_id INTEGER
)
""")

db.commit()


def add_advertising_group(
    telegram_id,
    group_username,
    group_id=None,
    title=None,
):

    cursor.execute(
        """
        INSERT INTO advertising_groups
        (
            telegram_id,
            group_username,
            group_id,
            title
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            telegram_id,
            group_username,
            group_id,
            title,
        ),
    )

    db.commit()

    return cursor.lastrowid


def get_advertising_groups(telegram_id):

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            group_username,
            group_id,
            title,
            interval_minutes,
            enabled,
            message_type,
            message_text,
            forward_chat_id,
            forward_message_id
        FROM advertising_groups
        WHERE telegram_id = ?
        ORDER BY id DESC
        """,
        (telegram_id,),
    )

    return cursor.fetchall()


def get_advertising_group(group_id):

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            group_username,
            group_id,
            title,
            interval_minutes,
            enabled,
            message_type,
            message_text,
            forward_chat_id,
            forward_message_id
        FROM advertising_groups
        WHERE id = ?
        """,
        (group_id,),
    )

    return cursor.fetchone()


def delete_advertising_group(group_id):

    cursor.execute(
        """
        DELETE FROM advertising_groups
        WHERE id = ?
        """,
        (group_id,),
    )

    db.commit()


def update_ad_interval(
    group_id,
    minutes,
):

    cursor.execute(
        """
        UPDATE advertising_groups
        SET interval_minutes = ?
        WHERE id = ?
        """,
        (
            minutes,
            group_id,
        ),
    )

    db.commit()


def update_ad_enabled(
    group_id,
    enabled,
):

    cursor.execute(
        """
        UPDATE advertising_groups
        SET enabled = ?
        WHERE id = ?
        """,
        (
            enabled,
            group_id,
        ),
    )

    db.commit()


def update_ad_message(
    group_id,
    message_type,
    message_text=None,
    forward_chat_id=None,
    forward_message_id=None,
):

    cursor.execute(
        """
        UPDATE advertising_groups
        SET
            message_type = ?,
            message_text = ?,
            forward_chat_id = ?,
            forward_message_id = ?
        WHERE id = ?
        """,
        (
            message_type,
            message_text,
            forward_chat_id,
            forward_message_id,
            group_id,
        ),
    )

    db.commit()


def save_advertising_group_message(group_id, chat_id, message_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE advertising_groups
        SET source_chat_id = ?, source_message_id = ?
        WHERE id = ?
        """,
        (chat_id, message_id, group_id),
    )

    conn.commit()
    conn.close()


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def update_ad_status(group_id, status):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE advertising_groups
        SET enabled = ?
        WHERE id = ?
        """,
        (
            status,
            group_id,
        ),
    )

    conn.commit()
    conn.close()


def set_advertising_group_enabled(group_id, enabled):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE advertising_groups
        SET enabled=?
        WHERE id=?
        """,
        (
            1 if enabled else 0,
            group_id,
        ),
    )

    conn.commit()
    conn.close()


def save_api_id(user_id, api_id):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
    INSERT OR IGNORE INTO accounts(user_id)
    VALUES(?)
    """,
        (user_id,),
    )

    cur.execute(
        """
    UPDATE accounts
    SET api_id=?
    WHERE user_id=?
    """,
        (api_id, user_id),
    )

    conn.commit()
    conn.close()


def save_api_hash(user_id, api_hash):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
    UPDATE accounts
    SET api_hash=?
    WHERE user_id=?
    """,
        (api_hash, user_id),
    )

    conn.commit()
    conn.close()


def save_phone(user_id, phone):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
    UPDATE accounts
    SET phone=?
    WHERE user_id=?
    """,
        (phone, user_id),
    )

    conn.commit()
    conn.close()


def get_account(user_id):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
    SELECT *
    FROM accounts
    WHERE user_id=?
    """,
        (user_id,),
    )

    row = cur.fetchone()

    conn.close()

    return row
