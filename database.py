import os
import sqlite3

import config

# =========================
# PERSISTENT DATABASE PATH
# =========================

DB_PATH = config.DATABASE_PATH


# اطمینان از وجود پوشه
os.makedirs(
    os.path.dirname(DB_PATH),
    exist_ok=True,
)


db = sqlite3.connect(
    DB_PATH,
    check_same_thread=False,
)

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
    append_last_lines TEXT DEFAULT '',
    account_type TEXT DEFAULT 'bot'
)
""")

# ----------------------------- db.comit --------------------------------

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


columns = [row[1] for row in cursor.execute("PRAGMA table_info(transfers)").fetchall()]

if "account_type" not in columns:
    cursor.execute("ALTER TABLE transfers ADD COLUMN account_type TEXT DEFAULT 'bot'")
    db.commit()


# ================= GROUPS =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS registered_groups(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    group_id INTEGER NOT NULL,

    access_hash INTEGER,

    title TEXT,

    username TEXT,

    group_link TEXT,

    enabled INTEGER DEFAULT 0,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()

# ================= GROUP MESSAGES =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS group_messages(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    registered_group_id INTEGER UNIQUE NOT NULL,

    user_id INTEGER NOT NULL,

    message_type TEXT NOT NULL,

    message_text TEXT,

    caption TEXT,

    file_path TEXT,

    forward_chat_id INTEGER,

    forward_message_id INTEGER,

    schedule_minutes INTEGER,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    quote_text TEXT,

    entities_json TEXT
)
""")

db.commit()

columns = [
    row[1] for row in cursor.execute("PRAGMA table_info(group_messages)").fetchall()
]

if "quote_text" not in columns:
    cursor.execute("ALTER TABLE group_messages ADD COLUMN quote_text TEXT")
    db.commit()

if "entities_json" not in columns:
    cursor.execute("ALTER TABLE group_messages ADD COLUMN entities_json TEXT")
    db.commit()

# ================= add Transfers =================


def add_transfer(
    telegram_id,
    source_channel,
    target_channel,
    account_type="bot",
):

    cursor.execute(
        """
        INSERT INTO transfers
        (
            telegram_id,
            source_channel,
            target_channel,
            account_type
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            telegram_id,
            source_channel,
            target_channel,
            account_type,
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


# ------------------- get user transfer count ------------------


def get_user_transfer_count(
    telegram_id,
    account_type,
):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM transfers
        WHERE telegram_id=?
        AND account_type=?
        """,
        (
            telegram_id,
            account_type,
        ),
    )

    count = cur.fetchone()[0]

    conn.close()

    return count


# ------------------- get all transfers ------------------


def get_all_transfers():
    cursor.execute("""
        SELECT
            id,
            telegram_id,
            source_channel,
            target_channel,
            enabled,
            account_type
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


def save_session(user_id, session):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE accounts
        SET session=?
        WHERE user_id=?
        """,
        (
            session,
            user_id,
        ),
    )

    conn.commit()
    conn.close()


# ================= GROUP FUNCTIONS =================


def add_registered_group(
    user_id,
    group_id,
    access_hash,
    title,
    username,
    group_link,
):

    cursor.execute(
        """
        INSERT INTO registered_groups
        (
            user_id,
            group_id,
            access_hash,
            title,
            username,
            group_link
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            group_id,
            access_hash,
            title,
            username,
            group_link,
        ),
    )

    db.commit()

    return cursor.lastrowid


def get_user_groups(user_id):

    cursor.execute(
        """
        SELECT
            id,
            group_id,
            access_hash,
            title,
            username,
            group_link,
            enabled,
            created_at
        FROM registered_groups
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (user_id,),
    )

    return cursor.fetchall()


def delete_registered_group(
    group_db_id,
    user_id,
):
    import os

    # اول فایل پیام/بنر ذخیره‌شده را پیدا می‌کنیم
    cursor.execute(
        """
        SELECT file_path
        FROM group_messages
        WHERE registered_group_id=?
        AND user_id=?
        """,
        (
            group_db_id,
            user_id,
        ),
    )

    result = cursor.fetchone()

    file_path = result[0] if result else None

    # حذف پیام/بنر ذخیره‌شده
    cursor.execute(
        """
        DELETE FROM group_messages
        WHERE registered_group_id=?
        AND user_id=?
        """,
        (
            group_db_id,
            user_id,
        ),
    )

    # حذف خود گروه
    cursor.execute(
        """
        DELETE FROM registered_groups
        WHERE id=?
        AND user_id=?
        """,
        (
            group_db_id,
            user_id,
        ),
    )

    db.commit()

    # اگر فایل رسانه‌ای ذخیره شده بود، آن را هم حذف کن
    if file_path:

        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:

            pass


# ================= GROUP MESSAGE FUNCTIONS =================


def save_group_message(
    registered_group_id,
    user_id,
    message_type,
    message_text=None,
    caption=None,
    file_path=None,
    forward_chat_id=None,
    forward_message_id=None,
    quote_text=None,
    entities_json=None,
):

    cursor.execute(
        """
        DELETE FROM group_messages
        WHERE registered_group_id=?
        """,
        (registered_group_id,),
    )

    cursor.execute(
        """
        INSERT INTO group_messages
        (
            registered_group_id,
            user_id,
            message_type,
            message_text,
            caption,
            file_path,
            forward_chat_id,
            forward_message_id,
            quote_text,
            entities_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?)
        """,
        (
            registered_group_id,
            user_id,
            message_type,
            message_text,
            caption,
            file_path,
            forward_chat_id,
            forward_message_id,
            quote_text,
            entities_json,
        ),
    )

    db.commit()

    return cursor.lastrowid


def get_group_message(
    registered_group_id,
    user_id,
):

    cursor.execute(
        """
        SELECT
            id,
            registered_group_id,
            user_id,
            message_type,
            message_text,
            caption,
            file_path,
            forward_chat_id,
            forward_message_id,
            schedule_minutes,
            created_at,
            updated_at,
            quote_text,
            entities_json
        FROM group_messages
        WHERE registered_group_id=?
        AND user_id=?
        LIMIT 1
        """,
        (
            registered_group_id,
            user_id,
        ),
    )

    return cursor.fetchone()


def set_group_schedule(
    registered_group_id,
    user_id,
    minutes,
):

    cursor.execute(
        """
        UPDATE group_messages
        SET
            schedule_minutes=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE registered_group_id=?
        AND user_id=?
        """,
        (
            minutes,
            registered_group_id,
            user_id,
        ),
    )

    db.commit()


def set_group_enabled(
    registered_group_id,
    user_id,
    enabled,
):

    cursor.execute(
        """
        UPDATE registered_groups
        SET enabled=?
        WHERE id=?
        AND user_id=?
        """,
        (
            1 if enabled else 0,
            registered_group_id,
            user_id,
        ),
    )

    db.commit()


def get_all_active_group_ads():

    cursor.execute("""
        SELECT
            user_id,
            id
        FROM registered_groups
        WHERE enabled=1
        ORDER BY id ASC
        """)

    return cursor.fetchall()


# ================= ADMIN STATISTICS =================


def get_admin_statistics():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # تعداد کاربران
    cur.execute("""
        SELECT COUNT(*)
        FROM users
    """)

    users_count = cur.fetchone()[0]

    # تعداد اکانت‌های متصل
    # فقط اکانت‌هایی که session دارند
    cur.execute("""
        SELECT COUNT(*)
        FROM accounts
        WHERE session IS NOT NULL
        AND session != ''
    """)

    connected_accounts = cur.fetchone()[0]

    # تعداد انتقال‌های کانال
    # هر رکورد یک مبدا + مقصد محسوب می‌شود
    cur.execute("""
        SELECT COUNT(*)
        FROM transfers
    """)

    transfers_count = cur.fetchone()[0]

    # تعداد گروه‌های تبلیغاتی ثبت‌شده
    cur.execute("""
        SELECT COUNT(*)
        FROM registered_groups
    """)

    groups_count = cur.fetchone()[0]

    conn.close()

    return {
        "users": users_count,
        "accounts": connected_accounts,
        "transfers": transfers_count,
        "groups": groups_count,
    }
