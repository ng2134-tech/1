# -*- coding: utf-8 -*-
# SQLite-кэш: котировки, скоринг, новости, история сигналов.
import sqlite3, json, time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "terminal.db"

def _conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS cache (
            ticker TEXT, key TEXT, value TEXT,
            ts REAL, PRIMARY KEY (ticker, key)
        );
        CREATE TABLE IF NOT EXISTS signals_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, ts REAL, score INTEGER,
            signal TEXT, upside REAL, price REAL,
            outcome TEXT DEFAULT 'OPEN'
        );
        CREATE TABLE IF NOT EXISTS news_cache (
            ticker TEXT, ts REAL, title TEXT,
            pub_date TEXT, link TEXT
        );
        """)

def cache_set(ticker: str, key: str, value):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?,?)",
            (ticker, key, json.dumps(value), time.time())
        )

def cache_get(ticker: str, key: str, ttl: float = 900):
    """Возвращает значение если не старше ttl секунд, иначе None."""
    with _conn() as c:
        row = c.execute(
            "SELECT value, ts FROM cache WHERE ticker=? AND key=?",
            (ticker, key)
        ).fetchone()
    if row and (time.time() - row["ts"]) < ttl:
        return json.loads(row["value"])
    return None

def save_signal(ticker, score, signal, upside, price):
    with _conn() as c:
        c.execute(
            "INSERT INTO signals_history (ticker,ts,score,signal,upside,price) VALUES (?,?,?,?,?,?)",
            (ticker, time.time(), score, signal, upside, price)
        )

def get_signal_history(ticker: str, limit: int = 10):
    with _conn() as c:
        return c.execute(
            "SELECT * FROM signals_history WHERE ticker=? ORDER BY ts DESC LIMIT ?",
            (ticker, limit)
        ).fetchall()

def save_news(ticker, items: list):
    with _conn() as c:
        c.execute("DELETE FROM news_cache WHERE ticker=?", (ticker,))
        for it in items:
            c.execute(
                "INSERT INTO news_cache VALUES (?,?,?,?,?)",
                (ticker, time.time(), it.get("title",""), it.get("date",""), it.get("link",""))
            )

def get_news_cache(ticker: str):
    with _conn() as c:
        rows = c.execute(
            "SELECT title,pub_date,link FROM news_cache WHERE ticker=? ORDER BY ts DESC LIMIT 5",
            (ticker,)
        ).fetchall()
    return [{"title": r["title"], "date": r["pub_date"], "link": r["link"]} for r in rows]
