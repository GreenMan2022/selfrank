# В начало app.py (после импортов)
import os
import sys
from flask import Flask
from contextlib import closing

app = Flask(__name__)

# Определяем, где запущено: локально или на Render
if os.environ.get("RENDER"):
    # Render: используем PostgreSQL
    app.config["DATABASE_URL"] = os.environ["DATABASE_URL"]
    app.config["USE_POSTGRES"] = True
else:
    # Локально: SQLite
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE_URL"] = f"sqlite:///{os.path.join(app.instance_path, 'site.db')}"
    app.config["USE_POSTGRES"] = False

def get_db_connection():
    if app.config["USE_POSTGRES"]:
        import psycopg2
        conn = psycopg2.connect(app.config["DATABASE_URL"])
        conn.autocommit = True
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect(app.config["DATABASE_URL"].replace("sqlite:///", ""))
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    with closing(conn.cursor() if app.config["USE_POSTGRES"] else conn) as cur:
        if app.config["USE_POSTGRES"]:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    keywords TEXT,
                    content TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    lang TEXT DEFAULT 'ru',
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(slug, lang)
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    keywords TEXT,
                    content TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    lang TEXT DEFAULT 'ru',
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(slug, lang)
                )
            """)
        if not app.config["USE_POSTGRES"]:
            conn.commit()
    conn.close()
