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

        # Таблица запросов на реквизиты
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            status TEXT DEFAULT 'waiting',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def get_all_verifications():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, status FROM verifications
        WHERE status != 'rejected'
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": row[0], "status": row[1]} for row in rows]


def delete_verification(user_id: int):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM verifications WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM requests WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


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

def set_verification_status(user_id, status, reason=None, is_direct=False):
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM verifications WHERE user_id = ?", (user_id,))
    verification = cursor.fetchone()

    if not verification:
        conn.close()
        return

    # сохраняем, что заявка без видео
    if is_direct:
        cursor.execute("UPDATE verifications SET status = ?, rejection_reason = ?, video = 'SKIP' WHERE user_id = ?", (status, reason, user_id))
    else:
        cursor.execute("UPDATE verifications SET status = ?, rejection_reason = ? WHERE user_id = ?", (status, reason, user_id))

    conn.commit()
    conn.close()

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
    
    

def get_pending_verifications(stage: str) -> list:
    conn = create_connection()
    cursor = conn.cursor()

    if stage == "new":
        cursor.execute("""
            SELECT user_id FROM verifications
            WHERE status = 'new' AND doc_photo IS NOT NULL AND selfie_photo IS NOT NULL
        """)
    elif stage == "paid_waiting":
        cursor.execute("""
            SELECT user_id FROM verifications
            WHERE status = 'paid_waiting' AND payment_proof IS NOT NULL AND payment_proof != ''
        """)

    elif stage == "video_waiting":
        cursor.execute("""
            SELECT user_id FROM verifications
            WHERE status = 'video_waiting' AND video IS NOT NULL
        """)
    elif stage == "docs_ok":
        cursor.execute("""
            SELECT user_id FROM verifications
            WHERE status = 'docs_ok'
        """)
    else:
        cursor.execute("""
            SELECT user_id FROM verifications
            WHERE status = ?
        """, (stage,))

    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_pending_requisites_count_manual() -> int:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'waiting'")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_pending_verifications_count(stage: str) -> int:
    conn = create_connection()
    cursor = conn.cursor()

    if stage == "new":
        cursor.execute("""
            SELECT COUNT(*) FROM verifications
            WHERE status = 'new' AND doc_photo IS NOT NULL AND selfie_photo IS NOT NULL
        """)
    elif stage == "paid_waiting":
        cursor.execute("""
            SELECT COUNT(*) FROM verifications
            WHERE status = 'paid_waiting' AND payment_proof IS NOT NULL
        """)
    elif stage == "video_waiting":
        cursor.execute("""
            SELECT COUNT(*) FROM verifications
            WHERE status = 'video_waiting' AND video IS NOT NULL
        """)
    elif stage == "docs_ok":
        cursor.execute("""
            SELECT COUNT(*) FROM verifications
            WHERE status = 'docs_ok'
        """)
    else:
        cursor.execute("SELECT COUNT(*) FROM verifications WHERE status = ?", (stage,))

    count = cursor.fetchone()[0]
    conn.close()
    return count


def is_verified(user_id: int) -> bool:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_verified FROM users WHERE telegram_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0])
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
    cursor.execute("SELECT status FROM verifications WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

#===== Реквизиты (отдельные заявки) =====

def create_requisite_request(user_id: int) -> bool:
    conn = create_connection()
    cursor = conn.cursor()

    # Проверка на активную заявку
    cursor.execute("""
        SELECT 1 FROM requests
        WHERE user_id = ? AND status = 'waiting'
    """, (user_id,))
    exists = cursor.fetchone()

    if exists:
        conn.close()
        return False  # Уже есть активная заявка

    # Создание новой заявки
    cursor.execute("""
        INSERT OR REPLACE INTO requests (user_id, status, created_at)
        VALUES (?, 'waiting', CURRENT_TIMESTAMP)
    """, (user_id,))
    conn.commit()
    conn.close()
    return True

def get_pending_requisite_requests() -> list:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM requests WHERE status = 'waiting'")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def mark_requisite_request_done(user_id: int):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE requests SET status = 'done' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
