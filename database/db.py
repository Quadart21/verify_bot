import sqlite3

DB_PATH = "data.db"

def create_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with create_connection() as conn:
        cursor = conn.cursor()

        # Пользователи
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            is_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Заявки на верификацию
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            doc_photo TEXT,
            selfie_photo TEXT,
            payment_proof TEXT,
            video TEXT,
            status TEXT,  -- new, docs_ok, paid_waiting, video_waiting, video_ok, rejected
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Реквизиты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS requisites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            details TEXT NOT NULL
        )
        """)

        conn.commit()

# ===================== Пользователи =====================

def add_user(telegram_id: int):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (telegram_id,))
        conn.commit()

def is_user_verified(telegram_id: int) -> bool:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_verified FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        return bool(row and row[0])

def set_user_verified(telegram_id: int):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_verified = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()

# ===================== Верификация =====================

def create_verification(user_id: int):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO verifications (user_id, status)
            VALUES (?, 'new')
        """, (user_id,))
        conn.commit()

def update_verification(user_id: int, field: str, value: str, status: str = None):
    with create_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(f"""
                UPDATE verifications
                SET {field} = ?, status = ?
                WHERE user_id = ? AND status != 'rejected'
            """, (value, status, user_id))
        else:
            cursor.execute(f"""
                UPDATE verifications
                SET {field} = ?
                WHERE user_id = ? AND status != 'rejected'
            """, (value, user_id))
        conn.commit()

def set_verification_status(user_id: int, status: str, reason: str = None):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE verifications SET status = ?, rejection_reason = ?
            WHERE user_id = ?
        """, (status, reason, user_id))
        conn.commit()

def get_verification_data(user_id: int) -> dict:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT doc_photo, selfie_photo, payment_proof, video, status, rejection_reason
            FROM verifications
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "doc_photo": row[0],
                "selfie_photo": row[1],
                "payment_proof": row[2],
                "video": row[3],
                "status": row[4],
                "reason": row[5],
            }
        return {}

def get_pending_verifications(status: str) -> list:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM verifications
            WHERE status = ?
        """, (status,))
        return [row[0] for row in cursor.fetchall()]

def get_pending_verifications_count(status: str) -> int:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM verifications WHERE status = ?", (status,))
        return cursor.fetchone()[0]

# ===================== Реквизиты =====================

def add_requisite(label: str, details: str):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO requisites (label, details) VALUES (?, ?)", (label, details))
        conn.commit()

def get_all_requisites() -> list:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, details FROM requisites")
        return cursor.fetchall()

def update_requisite(requisite_id: int, label: str, details: str):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE requisites SET label = ?, details = ?
            WHERE id = ?
        """, (label, details, requisite_id))
        conn.commit()

def delete_requisite(requisite_id: int):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM requisites WHERE id = ?", (requisite_id,))
        conn.commit()


def get_verification_status(user_id: int) -> str:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM verifications WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""
