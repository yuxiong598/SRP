import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chemical_management.db")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _expires_at(hours=12):
    return (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row):
    return dict(row) if row is not None else None


def normalize_card_no(card_no):
    return "".join(str(card_no or "").strip().split()).upper()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        method, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if method != "pbkdf2_sha256":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return secrets.compare_digest(check.hex(), digest)


def _ensure_column(cursor, table, column, definition):
    columns = [row["name"] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'operator',
            department TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            employee_no TEXT UNIQUE,
            department TEXT,
            phone TEXT,
            role TEXT DEFAULT 'operator',
            status TEXT DEFAULT 'active',
            face_image_path TEXT,
            registered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_no TEXT NOT NULL UNIQUE,
            person_id INTEGER,
            card_type TEXT DEFAULT 'ic',
            status TEXT DEFAULT 'active',
            remark TEXT,
            registered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_seen_at TEXT,
            FOREIGN KEY(person_id) REFERENCES people(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chemicals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            alias TEXT,
            cas_no TEXT,
            category TEXT,
            specification TEXT,
            stock REAL DEFAULT 0,
            unit TEXT DEFAULT 'bottle',
            min_stock REAL DEFAULT 0,
            max_stock REAL,
            hazard TEXT,
            hazard_class TEXT,
            danger_level INTEGER DEFAULT 1,
            is_hazardous INTEGER DEFAULT 0,
            control_level TEXT DEFAULT 'normal',
            storage_requirement TEXT,
            location TEXT,
            manufacturer TEXT,
            project_name TEXT,
            owner TEXT,
            image_path TEXT,
            ocr_text TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    for column, definition in {
        "code": "TEXT UNIQUE",
        "category": "TEXT",
        "min_stock": "REAL DEFAULT 0",
        "max_stock": "REAL",
        "hazard_class": "TEXT",
        "danger_level": "INTEGER DEFAULT 1",
        "is_hazardous": "INTEGER DEFAULT 0",
        "control_level": "TEXT DEFAULT 'normal'",
        "storage_requirement": "TEXT",
        "owner": "TEXT",
        "status": "TEXT DEFAULT 'active'",
    }.items():
        _ensure_column(cursor, "chemicals", column, definition)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_no TEXT NOT NULL UNIQUE,
            transaction_type TEXT NOT NULL,
            chemical_id INTEGER NOT NULL,
            chemical_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT DEFAULT 'bottle',
            before_stock REAL,
            after_stock REAL,
            applicant_id INTEGER,
            applicant_name TEXT,
            handler_id INTEGER,
            handler_name TEXT,
            card_no TEXT,
            project_name TEXT,
            purpose TEXT,
            status TEXT DEFAULT 'completed',
            approval_id INTEGER,
            remark TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chemical_id) REFERENCES chemicals(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_no TEXT NOT NULL UNIQUE,
            request_type TEXT NOT NULL,
            chemical_id INTEGER NOT NULL,
            chemical_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT DEFAULT 'bottle',
            applicant_id INTEGER,
            applicant_name TEXT,
            card_no TEXT,
            project_name TEXT,
            purpose TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            reviewer_id INTEGER,
            reviewer_name TEXT,
            reviewed_at TEXT,
            review_note TEXT,
            transaction_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chemical_id) REFERENCES chemicals(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            person_id INTEGER,
            person_name TEXT,
            card_no TEXT,
            chemical_id INTEGER,
            chemical_name TEXT,
            before_weight REAL,
            after_weight REAL,
            usage_weight REAL,
            unit TEXT DEFAULT 'g',
            ocr_text TEXT,
            chemical_image_path TEXT,
            face_image_path TEXT,
            transaction_id INTEGER,
            raw_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    _ensure_column(cursor, "usage_records", "transaction_id", "INTEGER")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            actor_id INTEGER,
            actor_name TEXT,
            target_type TEXT,
            target_id TEXT,
            detail TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chemicals_name ON chemicals(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_card_no ON cards(card_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created ON inventory_transactions(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approval_requests(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)")

    conn.commit()
    conn.close()
    seed_default_data()


def seed_default_data():
    create_user(
        username="admin",
        password="admin123",
        name="系统管理员",
        role="admin",
        department="安全管理",
        allow_existing=True,
    )

    defaults = [
        {
            "code": "CHEM-H2SO4",
            "name": "硫酸",
            "alias": "sulfuric acid; sulphuric acid; H2SO4",
            "cas_no": "7664-93-9",
            "category": "酸类",
            "specification": "500ml",
            "stock": 3,
            "unit": "瓶",
            "min_stock": 1,
            "hazard": "腐蚀性",
            "hazard_class": "8",
            "danger_level": 4,
            "is_hazardous": 1,
            "control_level": "strict",
            "storage_requirement": "耐腐蚀柜，远离碱类",
            "location": "A1",
            "project_name": "公共库存",
        },
        {
            "code": "CHEM-NAOH",
            "name": "氢氧化钠",
            "alias": "sodium hydroxide; caustic soda; NaOH",
            "cas_no": "1310-73-2",
            "category": "碱类",
            "specification": "100g",
            "stock": 5,
            "unit": "瓶",
            "min_stock": 2,
            "hazard": "腐蚀性",
            "hazard_class": "8",
            "danger_level": 3,
            "is_hazardous": 1,
            "control_level": "strict",
            "storage_requirement": "密封保存，远离酸类",
            "location": "B2",
            "project_name": "公共库存",
        },
        {
            "code": "CHEM-ETOH",
            "name": "乙醇",
            "alias": "ethanol; ethyl alcohol; C2H5OH",
            "cas_no": "64-17-5",
            "category": "有机溶剂",
            "specification": "500ml",
            "stock": 2,
            "unit": "瓶",
            "min_stock": 1,
            "hazard": "易燃",
            "hazard_class": "3",
            "danger_level": 3,
            "is_hazardous": 1,
            "control_level": "approval",
            "storage_requirement": "防火柜，远离火源",
            "location": "C3",
            "project_name": "公共库存",
        },
    ]
    for item in defaults:
        if not get_chemical_by_code(item["code"]):
            upsert_chemical(item)


def create_user(username, password, name, role="operator", department=None, phone=None, status="active", allow_existing=False):
    now = _now()
    existing = get_user_by_username(username)
    if existing:
        if allow_existing:
            return existing
        raise ValueError("username already exists")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (username, password_hash, name, role, department, phone, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (username, hash_password(password), name, role, department, phone, status, now, now),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_user(user_id)


def get_user(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, name, role, department, phone, status, created_at, updated_at, last_login_at FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_user_by_username(username, include_password=False):
    conn = get_connection()
    columns = "*" if include_password else "id, username, name, role, department, phone, status, created_at, updated_at, last_login_at"
    row = conn.execute(f"SELECT {columns} FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def authenticate_user(username, password):
    user = get_user_by_username(username, include_password=True)
    if not user or user["status"] != "active":
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    conn = get_connection()
    conn.execute("UPDATE users SET last_login_at=?, updated_at=? WHERE id=?", (_now(), _now(), user["id"]))
    conn.commit()
    conn.close()
    return get_user(user["id"])


def create_session(user_id, hours=12):
    token = secrets.token_urlsafe(32)
    now = _now()
    expires = _expires_at(hours)
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now, expires),
    )
    conn.commit()
    conn.close()
    return {"token": token, "expires_at": expires}


def get_user_by_token(token):
    if not token:
        return None
    conn = get_connection()
    row = conn.execute(
        """
        SELECT s.expires_at, u.id, u.username, u.name, u.role, u.department, u.phone, u.status
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token=?
        """,
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    data = _row_to_dict(row)
    if data["expires_at"] < _now() or data["status"] != "active":
        delete_session(token)
        return None
    return data


def delete_session(token):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()


def create_person(name, employee_no=None, department=None, phone=None, role="operator", face_image_path=None, status="active"):
    now = _now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO people (name, employee_no, department, phone, role, status, face_image_path, registered_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(employee_no) DO UPDATE SET
            name=excluded.name,
            department=excluded.department,
            phone=excluded.phone,
            role=excluded.role,
            status=excluded.status,
            face_image_path=COALESCE(excluded.face_image_path, people.face_image_path),
            updated_at=excluded.updated_at
        """,
        (name, employee_no, department, phone, role, status, face_image_path, now, now),
    )
    person_id = cursor.lastrowid
    if employee_no:
        cursor.execute("SELECT id FROM people WHERE employee_no=?", (employee_no,))
        person_id = cursor.fetchone()["id"]
    conn.commit()
    conn.close()
    return get_person(person_id)


def list_people(keyword=""):
    conn = get_connection()
    like = f"%{keyword}%"
    rows = conn.execute(
        """
        SELECT * FROM people
        WHERE ?='' OR name LIKE ? OR employee_no LIKE ? OR department LIKE ?
        ORDER BY id DESC
        """,
        (keyword, like, like, like),
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def get_person(person_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_person_by_employee_no(employee_no):
    conn = get_connection()
    row = conn.execute("SELECT * FROM people WHERE employee_no=?", (employee_no,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def register_card(card_no, person_id=None, person=None, card_type="ic", status="active", remark=None):
    card_no = normalize_card_no(card_no)
    if not card_no:
        raise ValueError("card_no is required")
    if person_id is None and person:
        created = create_person(**person)
        person_id = created["id"]

    now = _now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO cards (card_no, person_id, card_type, status, remark, registered_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(card_no) DO UPDATE SET
            person_id=excluded.person_id,
            card_type=excluded.card_type,
            status=excluded.status,
            remark=excluded.remark,
            updated_at=excluded.updated_at
        """,
        (card_no, person_id, card_type, status, remark, now, now),
    )
    conn.commit()
    conn.close()
    return get_card(card_no)


def get_card(card_no):
    card_no = normalize_card_no(card_no)
    conn = get_connection()
    row = conn.execute(
        """
        SELECT c.*, p.name AS person_name, p.employee_no, p.department, p.role AS person_role
        FROM cards c
        LEFT JOIN people p ON p.id = c.person_id
        WHERE c.card_no=?
        """,
        (card_no,),
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_cards(keyword=""):
    conn = get_connection()
    like = f"%{keyword}%"
    rows = conn.execute(
        """
        SELECT c.*, p.name AS person_name, p.employee_no, p.department, p.role AS person_role
        FROM cards c
        LEFT JOIN people p ON p.id = c.person_id
        WHERE ?='' OR c.card_no LIKE ? OR p.name LIKE ? OR p.employee_no LIKE ?
        ORDER BY c.id DESC
        """,
        (keyword, like, like, like),
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def touch_card(card_no):
    card_no = normalize_card_no(card_no)
    conn = get_connection()
    conn.execute("UPDATE cards SET last_seen_at=?, updated_at=? WHERE card_no=?", (_now(), _now(), card_no))
    conn.commit()
    conn.close()


def verify_card(card_no):
    card_no = normalize_card_no(card_no)
    card = get_card(card_no)
    if not card:
        return {"valid": False, "reason": "card_not_registered", "card_no": card_no}
    if card["status"] != "active":
        return {"valid": False, "reason": "card_inactive", "card": card}
    if not card["person_id"]:
        return {"valid": False, "reason": "card_not_bound", "card": card}
    touch_card(card_no)
    return {"valid": True, "card": get_card(card_no)}


def _chemical_fields(data):
    return {
        "code": data.get("code"),
        "name": data.get("name"),
        "alias": data.get("alias"),
        "cas_no": data.get("cas_no"),
        "category": data.get("category"),
        "specification": data.get("specification"),
        "stock": float(data.get("stock") or 0),
        "unit": data.get("unit", "瓶"),
        "min_stock": float(data.get("min_stock") or 0),
        "max_stock": data.get("max_stock"),
        "hazard": data.get("hazard"),
        "hazard_class": data.get("hazard_class"),
        "danger_level": int(data.get("danger_level") or 1),
        "is_hazardous": 1 if data.get("is_hazardous") in (True, 1, "1", "true", "True") else 0,
        "control_level": data.get("control_level", "normal"),
        "storage_requirement": data.get("storage_requirement"),
        "location": data.get("location"),
        "manufacturer": data.get("manufacturer"),
        "project_name": data.get("project_name"),
        "owner": data.get("owner"),
        "image_path": data.get("image_path"),
        "ocr_text": data.get("ocr_text"),
        "status": data.get("status", "active"),
    }


def upsert_chemical(data):
    now = _now()
    chemical_id = data.get("id")
    fields = _chemical_fields(data)
    if not fields["name"]:
        raise ValueError("chemical name is required")

    if fields["max_stock"] in ("", None):
        fields["max_stock"] = None
    else:
        fields["max_stock"] = float(fields["max_stock"])

    conn = get_connection()
    cursor = conn.cursor()
    values = list(fields.values())
    if chemical_id:
        cursor.execute(
            """
            UPDATE chemicals SET
                code=?, name=?, alias=?, cas_no=?, category=?, specification=?, stock=?, unit=?, min_stock=?, max_stock=?,
                hazard=?, hazard_class=?, danger_level=?, is_hazardous=?, control_level=?, storage_requirement=?,
                location=?, manufacturer=?, project_name=?, owner=?, image_path=?, ocr_text=?, status=?, updated_at=?
            WHERE id=?
            """,
            (*values, now, chemical_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO chemicals
            (code, name, alias, cas_no, category, specification, stock, unit, min_stock, max_stock,
             hazard, hazard_class, danger_level, is_hazardous, control_level, storage_requirement,
             location, manufacturer, project_name, owner, image_path, ocr_text, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*values, now, now),
        )
        chemical_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_chemical(chemical_id)


def get_chemical(chemical_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM chemicals WHERE id=?", (chemical_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_chemical_by_code(code):
    if not code:
        return None
    conn = get_connection()
    row = conn.execute("SELECT * FROM chemicals WHERE code=?", (code,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_chemicals(keyword="", hazardous_only=False):
    conn = get_connection()
    like = f"%{keyword}%"
    rows = conn.execute(
        """
        SELECT * FROM chemicals
        WHERE (?='' OR name LIKE ? OR alias LIKE ? OR cas_no LIKE ? OR location LIKE ? OR project_name LIKE ?)
          AND (?=0 OR is_hazardous=1 OR danger_level>=3 OR control_level!='normal')
        ORDER BY is_hazardous DESC, danger_level DESC, id DESC
        """,
        (keyword, like, like, like, like, like, 1 if hazardous_only else 0),
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def delete_chemical(chemical_id):
    conn = get_connection()
    conn.execute("UPDATE chemicals SET status='disabled', updated_at=? WHERE id=?", (_now(), chemical_id))
    conn.commit()
    conn.close()


def find_chemical_candidates():
    return list_chemicals("")


def is_controlled_chemical(chemical):
    if not chemical:
        return False
    return bool(
        chemical.get("is_hazardous")
        or int(chemical.get("danger_level") or 1) >= 3
        or chemical.get("control_level") in ("approval", "strict", "special")
    )


def _next_no(prefix):
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.randbelow(1000):03d}"


def create_inventory_transaction(
    transaction_type,
    chemical_id,
    quantity,
    applicant=None,
    handler=None,
    card_no=None,
    project_name=None,
    purpose=None,
    remark=None,
    approval_id=None,
    status="completed",
):
    quantity = float(quantity or 0)
    if quantity <= 0 and transaction_type != "adjust":
        raise ValueError("quantity must be greater than 0")

    conn = get_connection()
    cursor = conn.cursor()
    chemical = cursor.execute("SELECT * FROM chemicals WHERE id=?", (chemical_id,)).fetchone()
    if not chemical:
        conn.close()
        raise ValueError("chemical not found")

    chemical = _row_to_dict(chemical)
    before_stock = float(chemical.get("stock") or 0)
    if transaction_type in ("inbound", "return"):
        after_stock = before_stock + quantity
    elif transaction_type == "outbound":
        if before_stock < quantity:
            conn.close()
            raise ValueError("insufficient stock")
        after_stock = before_stock - quantity
    elif transaction_type == "adjust":
        after_stock = quantity
    else:
        conn.close()
        raise ValueError("unsupported transaction type")

    transaction_no = _next_no({"inbound": "IN", "outbound": "OUT", "return": "RET", "adjust": "ADJ"}.get(transaction_type, "TX"))
    now = _now()
    cursor.execute(
        """
        INSERT INTO inventory_transactions
        (transaction_no, transaction_type, chemical_id, chemical_name, quantity, unit, before_stock, after_stock,
         applicant_id, applicant_name, handler_id, handler_name, card_no, project_name, purpose, status, approval_id, remark, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction_no,
            transaction_type,
            chemical_id,
            chemical["name"],
            quantity,
            chemical.get("unit"),
            before_stock,
            after_stock,
            (applicant or {}).get("id"),
            (applicant or {}).get("name"),
            (handler or {}).get("id"),
            (handler or {}).get("name"),
            normalize_card_no(card_no),
            project_name,
            purpose,
            status,
            approval_id,
            remark,
            now,
        ),
    )
    transaction_id = cursor.lastrowid
    cursor.execute("UPDATE chemicals SET stock=?, updated_at=? WHERE id=?", (after_stock, now, chemical_id))
    if approval_id:
        cursor.execute(
            "UPDATE approval_requests SET transaction_id=?, status='completed' WHERE id=?",
            (transaction_id, approval_id),
        )
    conn.commit()
    conn.close()
    return get_inventory_transaction(transaction_id)


def get_inventory_transaction(transaction_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM inventory_transactions WHERE id=?", (transaction_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_inventory_transactions(keyword="", limit=200):
    conn = get_connection()
    like = f"%{keyword}%"
    rows = conn.execute(
        """
        SELECT * FROM inventory_transactions
        WHERE ?='' OR transaction_no LIKE ? OR chemical_name LIKE ? OR applicant_name LIKE ? OR card_no LIKE ? OR project_name LIKE ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (keyword, like, like, like, like, like, limit),
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def create_approval_request(data):
    chemical = get_chemical(data["chemical_id"])
    if not chemical:
        raise ValueError("chemical not found")
    request_no = _next_no("APP")
    now = _now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO approval_requests
        (request_no, request_type, chemical_id, chemical_name, quantity, unit, applicant_id, applicant_name,
         card_no, project_name, purpose, reason, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
        (
            request_no,
            data.get("request_type", "outbound"),
            chemical["id"],
            chemical["name"],
            float(data.get("quantity") or 0),
            chemical.get("unit"),
            data.get("applicant_id"),
            data.get("applicant_name"),
            normalize_card_no(data.get("card_no")),
            data.get("project_name"),
            data.get("purpose"),
            data.get("reason"),
            now,
        ),
    )
    approval_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_approval(approval_id)


def get_approval(approval_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM approval_requests WHERE id=?", (approval_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_approvals(status="", keyword=""):
    conn = get_connection()
    like = f"%{keyword}%"
    rows = conn.execute(
        """
        SELECT * FROM approval_requests
        WHERE (?='' OR status=?)
          AND (?='' OR request_no LIKE ? OR chemical_name LIKE ? OR applicant_name LIKE ? OR card_no LIKE ?)
        ORDER BY id DESC
        """,
        (status, status, keyword, like, like, like, like),
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def review_approval(approval_id, approved, reviewer, review_note=None):
    approval = get_approval(approval_id)
    if not approval:
        raise ValueError("approval not found")
    if approval["status"] != "pending":
        raise ValueError("approval has already been reviewed")

    status = "approved" if approved else "rejected"
    conn = get_connection()
    conn.execute(
        """
        UPDATE approval_requests
        SET status=?, reviewer_id=?, reviewer_name=?, reviewed_at=?, review_note=?
        WHERE id=?
        """,
        (status, (reviewer or {}).get("id"), (reviewer or {}).get("name"), _now(), review_note, approval_id),
    )
    conn.commit()
    conn.close()

    if approved and approval["request_type"] == "outbound":
        transaction = create_inventory_transaction(
            "outbound",
            approval["chemical_id"],
            approval["quantity"],
            applicant={"id": approval["applicant_id"], "name": approval["applicant_name"]},
            handler=reviewer,
            card_no=approval["card_no"],
            project_name=approval["project_name"],
            purpose=approval["purpose"],
            remark=f"审批通过: {review_note or ''}",
            approval_id=approval_id,
        )
        return {"approval": get_approval(approval_id), "transaction": transaction}
    return {"approval": get_approval(approval_id), "transaction": None}


def insert_usage_record(data):
    now = _now()
    timestamp = data.get("timestamp") or now
    chemical = data.get("chemical") or {}
    person = data.get("person") or data.get("person_name")
    card_no = data.get("card_no")
    person_id = data.get("person_id")

    if card_no and not person_id:
        card = get_card(card_no)
        if card:
            person_id = card.get("person_id")
            person = person or card.get("person_name")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO usage_records
        (timestamp, person_id, person_name, card_no, chemical_id, chemical_name, before_weight,
         after_weight, usage_weight, unit, ocr_text, chemical_image_path, face_image_path, transaction_id, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            person_id,
            person,
            normalize_card_no(card_no),
            chemical.get("id") or data.get("chemical_id"),
            chemical.get("name") or data.get("chemical_name"),
            data.get("beforeWeight") or data.get("before_weight"),
            data.get("afterWeight") or data.get("after_weight"),
            data.get("usage") or data.get("usage_weight"),
            data.get("unit", "g"),
            data.get("ocr_text") or chemical.get("ocr_text"),
            data.get("chemical_image_path"),
            data.get("face_image_path"),
            data.get("transaction_id"),
            data.get("raw_json"),
            now,
        ),
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_all_measurements(limit=100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM usage_records ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def dashboard_summary():
    conn = get_connection()
    total_chemicals = conn.execute("SELECT COUNT(*) AS c FROM chemicals WHERE status='active'").fetchone()["c"]
    hazardous_count = conn.execute(
        "SELECT COUNT(*) AS c FROM chemicals WHERE status='active' AND (is_hazardous=1 OR danger_level>=3 OR control_level!='normal')"
    ).fetchone()["c"]
    low_stock_count = conn.execute(
        "SELECT COUNT(*) AS c FROM chemicals WHERE status='active' AND stock <= min_stock"
    ).fetchone()["c"]
    pending_approvals = conn.execute("SELECT COUNT(*) AS c FROM approval_requests WHERE status='pending'").fetchone()["c"]
    today_transactions = conn.execute(
        "SELECT COUNT(*) AS c FROM inventory_transactions WHERE date(created_at)=date('now', 'localtime')"
    ).fetchone()["c"]
    conn.close()
    return {
        "total_chemicals": total_chemicals,
        "hazardous_count": hazardous_count,
        "low_stock_count": low_stock_count,
        "pending_approvals": pending_approvals,
        "today_transactions": today_transactions,
    }


def hazard_summary():
    chemicals = list_chemicals(hazardous_only=True)
    pending = list_approvals(status="pending")
    strict_count = len([item for item in chemicals if item.get("control_level") in ("strict", "special")])
    return {
        "hazardous_count": len(chemicals),
        "strict_count": strict_count,
        "pending_approvals": len(pending),
        "chemicals": chemicals,
        "pending": pending,
    }


def log_action(action, actor=None, target_type=None, target_id=None, detail=None):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO audit_logs (action, actor_id, actor_name, target_type, target_id, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (action, (actor or {}).get("id"), (actor or {}).get("name"), target_type, str(target_id or ""), detail, _now()),
    )
    conn.commit()
    conn.close()


def list_audit_logs(limit=200):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def register_operator(operator_id, name, face_image_path=None):
    return create_person(name=name, employee_no=str(operator_id), face_image_path=face_image_path)


def get_operator(operator_id):
    return get_person_by_employee_no(str(operator_id))


def operator_exists(operator_id):
    return get_operator(operator_id) is not None
