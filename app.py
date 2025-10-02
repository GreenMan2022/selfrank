import os
import re
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for, redirect, abort
from contextlib import closing
from ai_engine import generate_seo_article
from seo_utils import generate_meta_description, format_rfc2822
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Определяем среду
IS_RENDER = os.environ.get("RENDER", False)
if IS_RENDER:
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("❌ Переменная окружения DATABASE_URL не задана! Добавьте её в Render.")
    USE_POSTGRES = True
else:
    os.makedirs(app.instance_path, exist_ok=True)
    DATABASE_URL = os.path.join(app.instance_path, "site.db")
    USE_POSTGRES = False

def get_db_connection():
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    try:
        with closing(conn.cursor() if USE_POSTGRES else conn) as cur:
            if USE_POSTGRES:
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
            if not USE_POSTGRES:
                conn.commit()
    finally:
        conn.close()

# --- Routes ---

@app.route("/")
@app.route("/<lang>/")
def index(lang=None):
    if lang and lang not in ["ru", "en"]:
        abort(404)
    lang = lang or "ru"
    conn = get_db_connection()
    try:
        with closing(conn.cursor() if USE_POSTGRES else conn) as cur:
            if USE_POSTGRES:
                cur.execute("SELECT id, title, slug FROM articles WHERE lang = %s ORDER BY created DESC", (lang,))
                articles = cur.fetchall()
            else:
                cur.execute("SELECT id, title, slug FROM articles WHERE lang = ?", (lang,))
                articles = cur.fetchall()
        return render_template("index.html", articles=articles, lang=lang)
    finally:
        conn.close()

@app.route("/article/<slug>")
@app.route("/<lang>/article/<slug>")
def article(lang, slug):
    if lang not in ["ru", "en"]:
        abort(404)
    conn = get_db_connection()
    try:
        with closing(conn.cursor() if USE_POSTGRES else conn) as cur:
            if USE_POSTGRES:
                cur.execute("SELECT * FROM articles WHERE slug = %s AND lang = %s", (slug, lang))
                art = cur.fetchone()
            else:
                cur.execute("SELECT * FROM articles WHERE slug = ? AND lang = ?", (slug, lang))
                art = cur.fetchone()
        if not art:
            abort(404)
        meta_desc = generate_meta_description(art[3] if USE_POSTGRES else art["content"])
        return render_template("article.html", article=art, meta_description=meta_desc, lang=lang)
    finally:
        conn.close()

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form["title"]
        keywords = request.form.get("keywords", "")
        lang = request.form.get("lang", "ru")
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        content = generate_seo_article(title, keywords, lang)
        
        conn = get_db_connection()
        try:
            with closing(conn.cursor() if USE_POSTGRES else conn) as cur:
                if USE_POSTGRES:
                    cur.execute(
                        "INSERT INTO articles (title, keywords, content, slug, lang) VALUES (%s, %s, %s, %s, %s)",
                        (title, keywords, content, slug, lang)
                    )
                else:
                    cur.execute(
                        "INSERT INTO articles (title, keywords, content, slug, lang) VALUES (?, ?, ?, ?, ?)",
                        (title, keywords, content, slug, lang)
                    )
                if not USE_POSTGRES:
                    conn.commit()
            return jsonify({"status": "success", "url": url_for('article', lang=lang, slug=slug)})
        except Exception as e:
            print("DB Error:", e)
            return jsonify({"status": "error", "message": "Такой URL уже существует или ошибка БД."})
        finally:
            conn.close()
    return render_template("admin.html")

@app.route("/sitemap.xml")
def sitemap():
    conn = get_db_connection()
    try:
        with closing(conn.cursor() if USE_POSTGRES else conn) as cur:
            if USE_POSTGRES:
                cur.execute("SELECT slug, lang FROM articles")
                articles = cur.fetchall()
            else:
                cur.execute("SELECT slug, lang FROM articles")
                articles = cur.fetchall()
        urls = [url_for("index", _external=True)]
        for a in articles:
            slug, lang = a[0], a[1]
            urls.append(url_for("article", lang=lang, slug=slug, _external=True))
        xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        for url in urls:
            xml += f"<url><loc>{url}</loc></url>"
        xml += "</urlset>"
        return xml, 200, {"Content-Type": "application/xml"}
    finally:
        conn.close()

@app.route("/robots.txt")
def robots():
    return f"""User-agent: *
Allow: /

Sitemap: {url_for('sitemap', _external=True)}
""", 200, {"Content-Type": "text/plain"}

@app.route("/feed.xml")
def rss_feed():
    conn = get_db_connection()
    try:
        with closing(conn.cursor() if USE_POSTGRES else conn) as cur:
            if USE_POSTGRES:
                cur.execute("SELECT title, slug, content, lang, created FROM articles ORDER BY created DESC LIMIT 20")
                articles = cur.fetchall()
            else:
                cur.execute("SELECT title, slug, content, lang, created FROM articles ORDER BY created DESC LIMIT 20")
                articles = cur.fetchall()

        feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>SelfRank Blog</title>
    <link>{url_for('index', _external=True)}</link>
    <description>Автоматически генерируемый SEO-блог</description>
    <language>ru-ru</language>
    <lastBuildDate>{format_rfc2822(datetime.utcnow())}</lastBuildDate>
"""

        for a in articles:
            title, slug, content, lang, created = a[0], a[1], a[2], a[3], a[4]
            url = url_for("article", lang=lang, slug=slug, _external=True)
            desc = generate_meta_description(content)
            pub_date = format_rfc2822(created)
            feed += f"""
    <item>
        <title>{title}</title>
        <link>{url}</link>
        <description>{desc}</description>
        <pubDate>{pub_date}</pubDate>
        <guid>{url}</guid>
    </item>
"""
        feed += """
</channel>
</rss>
"""
        return feed, 200, {"Content-Type": "application/rss+xml"}
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise

    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Запуск сервера на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
