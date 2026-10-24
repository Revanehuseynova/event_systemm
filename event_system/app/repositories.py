"""Verilənlər bazası ilə işləyən qat. Bütün sorğular parametrlidir (SQL injection-dan qorunma)."""
import sqlite3
from typing import Optional

from .database import Database

EVENT_SELECT = """
    SELECT e.*, c.name AS category,
           (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered
    FROM events e JOIN categories c ON c.id = e.category_id
"""


class CategoryRepository:
    def __init__(self, db: Database):
        self.db = db

    def all(self) -> list:
        with _conn(self.db) as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM categories ORDER BY name")]

    def exists(self, category_id: int) -> bool:
        with _conn(self.db) as conn:
            return conn.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,)).fetchone() is not None


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def get(self, user_id: int) -> Optional[dict]:
        with _conn(self.db) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_by_email(self, email: str) -> Optional[dict]:
        with _conn(self.db) as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return dict(row) if row else None

    def create(self, full_name: str, email: str) -> dict:
        with _conn(self.db) as conn:
            cur = conn.execute("INSERT INTO users(full_name, email) VALUES (?, ?)", (full_name, email))
            return {"id": cur.lastrowid, "full_name": full_name, "email": email}


class EventRepository:
    def __init__(self, db: Database):
        self.db = db

    def search(self, q="", category_id=None, date_from=None, date_to=None, location="") -> list:
        sql, params = EVENT_SELECT + " WHERE 1=1", []
        if q:
            sql += " AND e.title LIKE ?"
            params.append(f"%{q}%")
        if category_id:
            sql += " AND e.category_id = ?"
            params.append(category_id)
        if date_from:
            sql += " AND e.event_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND e.event_date <= ?"
            params.append(date_to)
        if location:
            sql += " AND e.location LIKE ?"
            params.append(f"%{location}%")
        sql += " ORDER BY e.event_date, e.event_time"
        with _conn(self.db) as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    def get(self, event_id: int) -> Optional[dict]:
        with _conn(self.db) as conn:
            row = conn.execute(EVENT_SELECT + " WHERE e.id = ?", (event_id,)).fetchone()
            return dict(row) if row else None

    def create(self, d: dict) -> int:
        with _conn(self.db) as conn:
            cur = conn.execute(
                "INSERT INTO events(title, description, category_id, event_date, event_time, location, capacity) "
                "VALUES (:title, :description, :category_id, :event_date, :event_time, :location, :capacity)", d)
            return cur.lastrowid

    def update(self, event_id: int, d: dict) -> None:
        with _conn(self.db) as conn:
            conn.execute(
                "UPDATE events SET title=:title, description=:description, category_id=:category_id, "
                "event_date=:event_date, event_time=:event_time, location=:location, capacity=:capacity "
                "WHERE id=:id", {**d, "id": event_id})

    def delete(self, event_id: int) -> None:
        with _conn(self.db) as conn:
            conn.execute("DELETE FROM events WHERE id = ?", (event_id,))


class RegistrationRepository:
    def __init__(self, db: Database):
        self.db = db

    def add_if_capacity(self, event_id: int, user_id: int) -> str:
        """Atomik qeydiyyat: limit yoxlanışı və əlavə etmə eyni transaksiyada baş verir.
        Qaytarır: 'ok' | 'full' | 'duplicate'."""
        conn = self.db.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")  # yazma kilidi - yarış vəziyyətinin (race condition) qarşısı
            capacity = conn.execute("SELECT capacity FROM events WHERE id = ?", (event_id,)).fetchone()["capacity"]
            if conn.execute("SELECT 1 FROM registrations WHERE event_id = ? AND user_id = ?",
                            (event_id, user_id)).fetchone():
                conn.execute("ROLLBACK")
                return "duplicate"  # təkrar qeydiyyat limit dolu olsa belə düzgün mesaj verir
            count = conn.execute("SELECT COUNT(*) c FROM registrations WHERE event_id = ?", (event_id,)).fetchone()["c"]
            if count >= capacity:
                conn.execute("ROLLBACK")
                return "full"
            try:
                conn.execute("INSERT INTO registrations(event_id, user_id) VALUES (?, ?)", (event_id, user_id))
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return "duplicate"
            conn.execute("COMMIT")
            return "ok"
        finally:
            conn.close()

    def remove(self, event_id: int, user_id: int) -> bool:
        with _conn(self.db) as conn:
            cur = conn.execute("DELETE FROM registrations WHERE event_id = ? AND user_id = ?", (event_id, user_id))
            return cur.rowcount > 0

    def participants(self, event_id: int) -> list:
        with _conn(self.db) as conn:
            return [dict(r) for r in conn.execute(
                "SELECT u.id, u.full_name, u.email, r.created_at FROM registrations r "
                "JOIN users u ON u.id = r.user_id WHERE r.event_id = ? ORDER BY r.created_at", (event_id,))]

    def event_ids_of_user(self, user_id: int) -> list:
        with _conn(self.db) as conn:
            return [r["event_id"] for r in conn.execute(
                "SELECT event_id FROM registrations WHERE user_id = ?", (user_id,))]


class StatsRepository:
    def __init__(self, db: Database):
        self.db = db

    def totals(self) -> dict:
        with _conn(self.db) as conn:
            return {
                "total_events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                "total_registrations": conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
                "total_users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            }

    def top_events(self, limit: int = 5) -> list:
        with _conn(self.db) as conn:
            return [dict(r) for r in conn.execute(
                "SELECT e.id, e.title, e.capacity, COUNT(r.id) AS registered FROM events e "
                "LEFT JOIN registrations r ON r.event_id = e.id GROUP BY e.id "
                "ORDER BY registered DESC, e.title LIMIT ?", (limit,))]

    def by_category(self) -> list:
        with _conn(self.db) as conn:
            return [dict(r) for r in conn.execute(
                "SELECT c.name AS category, COUNT(DISTINCT e.id) AS events, COUNT(r.id) AS registrations "
                "FROM categories c LEFT JOIN events e ON e.category_id = c.id "
                "LEFT JOIN registrations r ON r.event_id = e.id GROUP BY c.id ORDER BY events DESC, c.name")]


class _conn:
    """Qısa ömürlü bağlantı üçün kontekst meneceri (avtomatik bağlanır)."""

    def __init__(self, db: Database):
        self.conn = db.connect()

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        self.conn.close()
