"""SQLite 数据层（WAL 模式）。

所有表集中在此创建与提供轻量 CRUD 助手。路径固定为项目根 data/app.db，
与基准一致：data/*.db 进 .gitignore，永不进仓库。
"""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "app.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """建表（幂等）。"""
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seed TEXT NOT NULL,
                kw TEXT NOT NULL,
                source TEXT DEFAULT 'rule',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                description TEXT,
                keywords TEXT,
                top_words TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                suggested_title TEXT,
                suggested_description TEXT,
                defects TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS backlinks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT,
                url TEXT,
                anchor TEXT,
                type TEXT DEFAULT 'guest-post',
                status TEXT DEFAULT 'planned',
                note TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT,
                date TEXT,
                indexed INTEGER DEFAULT 0,
                avg_ranking REAL DEFAULT 0,
                traffic INTEGER DEFAULT 0,
                kw_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT,
                score INTEGER DEFAULT 0,
                markdown TEXT,
                csv TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                ext TEXT,
                size INTEGER DEFAULT 0,
                text TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_conn() -> sqlite3.Connection:
    return _connect()


def insert_returning_id(conn: sqlite3.Connection, sql: str, params: tuple):
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid
