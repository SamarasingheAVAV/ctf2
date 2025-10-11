from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory, abort, Response
import os
import sqlite3
from pathlib import Path
import re

app = Flask(__name__)
app.secret_key = "dev-secret-key"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
UPLOAD_DIR = BASE_DIR / "uploads"
(UPLOAD_DIR).mkdir(exist_ok=True, parents=True)
(BASE_DIR / 'templates').mkdir(exist_ok=True)
(BASE_DIR / 'static' / 'images').mkdir(exist_ok=True, parents=True)

# NOTE: This application is intentionally vulnerable for educational purposes (TryHackMe Room)

# --- Database helpers (intentionally naive) ---

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            bio TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            image TEXT,
            stock INTEGER
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            user_id INTEGER,
            content TEXT
        );
        """
    )
    conn.commit()
    conn.close()


essential_images = [f"image{i}.jpg" for i in range(1, 10)]
for img in essential_images:
    p = BASE_DIR / 'static' / 'images' / img
    if not p.exists():
        with open(p, 'wb') as fh:
            fh.write(b'\xFF\xD8\xFF\xDBFAKEJPEGPLACEHOLDER')


def seed_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password, bio) VALUES ('alice','alice123','Loves fashion and design.')")
        cur.execute("INSERT INTO users (username, password, bio) VALUES ('bob','bob123','Streetwear enthusiast.')")
        cur.execute("INSERT INTO users (username, password, bio) VALUES ('admin','admin','Site administrator for AV Fashion')")
        cur.execute("INSERT INTO users (username, password, bio) VALUES ('windy_magon','windy123','Windy Magon, casual glam fan.')")
        cur.execute("INSERT INTO users (username, password, bio) VALUES ('james_karloe','james123','James Karloe, classic style lover.')")

    cur.execute("SELECT COUNT(*) AS c FROM products")
    if cur.fetchone()[0] == 0:
        stocks = [40, 20, 15, 32, 8, 12, 27, 5, 23]
        for i in range(1, 10):
            name = f"Dress {i}"
            desc = f"New arrival dress {i} with premium fabric and style. For buy please sign in."
            image = f"image{i}.jpg"
            stock = stocks[(i-1) % len(stocks)]
            cur.execute(
                "INSERT INTO products (name, description, image, stock) VALUES (?,?,?,?)",
                (name, desc, image, stock),
            )

    cur.execute("SELECT COUNT(*) AS c FROM comments")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO comments (product_id, user_id, content) VALUES (1,1,'Lovely color palette!')")

    conn.commit()
    conn.close()


@app.before_request
def ensure_db():
    if not DB_PATH.exists():
        init_db()
        seed_db()


# --- Routes ---

@app.route("/")
def index():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    login_flag = session.pop('show_sqli_flag', False)
    sections = [
        {"name": "Ladies Frocks", "desc": "👗 Elegant frocks for every occasion – step out in style and confidence! ✨"},
        {"name": "Formal Wear for Women & Accessories (Bags, Shoes)", "desc": "💼 Complete your chic look – stunning formal wear, handbags, and shoes to match! 👠👜"},
        {"name": "Casual Wear for Gents", "desc": "👕 Casual & comfy – effortless style for the modern gentleman! 😎"},
        {"name": "Formal Wear for Men (Watches, Belts, Accessories)", "desc": "⌚ Dress to impress – formal essentials and accessories for a polished look! 👔💼"},
        {"name": "Kids Section", "desc": "🧒 Fashion made fun – adorable styles for your little trendsetters! 🎀👕"},
        {"name": "Party Frocks", "desc": "✨ Party-ready glam – frocks that make you the star of every celebration! 💃"},
        {"name": "Sarees", "desc": "🌸 Timeless elegance – sarees that blend tradition with modern style! 👑"},
        {"name": "New Arrivals", "desc": "🆕 Fresh styles dropping weekly – be the first to rock the latest trends! 🔥"},
    ]
    cards = []
    max_len = min(len(products) - 1 if len(products) > 1 else 0, len(sections))
    for i in range(max_len):
        cards.append({"product": products[i + 1], "section": sections[i]})
    return render_template("index.html", products=products, cards=cards, login_flag=login_flag)


@app.route("/login", methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        query = f"SELECT id, username FROM users WHERE username = '{username}' AND password = '{password}'"
        conn = get_db()
        try:
            row = conn.execute(query).fetchone()
        finally:
            conn.close()
        if row:
            session["user_id"] = row[0]
            session["username"] = row[1]
            user_input = f"{username} {password}".lower()
            if re.search(r"'\s*or\s*1\s*=\s*1", user_input) or "--" in user_input or "union select" in user_input:
                session['show_sqli_flag'] = True
            return redirect(url_for("index"))
        else:
            message = "Invalid credentials"
    return render_template("login.html", message=message)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    message = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        bio = request.form.get("bio", "")
        query = f"INSERT INTO users (username, password, bio) VALUES ('{username}','{password}','{bio}')"
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(query)
            conn.commit()
            message = "Signup successful. Please login."
        except Exception as e:
            message = f"Error: {e}"
        finally:
            conn.close()
    return render_template("signup.html", message=message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# Search with SQLi/XSS pattern popups
@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = []
    trigger_flag_sqli = False
    trigger_flag_xss = False
    if q:
        query = f"SELECT * FROM products WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
        conn = get_db()
        try:
            results = conn.execute(query).fetchall()
        finally:
            conn.close()
        ql = q.lower()
        if (re.search(r"1\s*=\s*1", ql) or re.search(r"'\s*or\s*", ql) or "--" in ql or "union select" in ql):
            trigger_flag_sqli = True
        if "<script" in ql:
            trigger_flag_xss = True
    return render_template("search.html", q=q, results=results, trigger_flag_sqli=trigger_flag_sqli, trigger_flag_xss=trigger_flag_xss)


@app.route("/product/<int:product_id>", methods=["GET", "POST"])
def product_detail(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        conn.close()
        abort(404)
    message = None
    xss = request.args.get("xss")
    if request.method == "POST":
        if not session.get("user_id"):
            message = "Please login to comment."
        else:
            content = request.form.get("content", "")
            conn.execute("INSERT INTO comments (product_id, user_id, content) VALUES (?,?,?)", (product_id, session["user_id"], content))
            conn.commit()
            if "<script" in content.lower():
                conn.close()
                return redirect(url_for('product_detail', product_id=product_id, xss=1))
    comments = conn.execute("SELECT comments.*, users.username FROM comments JOIN users ON comments.user_id = users.id WHERE product_id = ? ORDER BY id DESC", (product_id,)).fetchall()
    conn.close()
    return render_template("product.html", product=product, comments=comments, message=message, xss=xss)


@app.route("/profile/<int:user_id>")
def profile(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not user:
        abort(404)
    is_other = False
    try:
        current_uid = int(session.get("user_id")) if session.get("user_id") is not None else None
        if current_uid is not None and current_uid != user_id:
            is_other = True
    except Exception:
        is_other = False
    return render_template("profile.html", user=user, show_idor_flag=is_other)


@app.route("/view")
def view_file():
    path = request.args.get("path", "")
    if not path:
        return "Provide ?path=...", 400
    file_path = (BASE_DIR / path).resolve()
    try:
        data = open(file_path, "rb").read()
    except Exception:
        return "File not found or unreadable", 404
    # If app.py requested, show flag and content in HTML for visibility
    if file_path.name == 'app.py':
        html = f"""
        <div style='padding:12px;background:#1b2b5a;color:#e6eeff;border-left:4px solid #3c5db3;'>THM{{directory_traversal_exposed_sensitive_file}}</div>
        <pre style='white-space:pre-wrap;color:#e6eeff;background:#0a1a3d;padding:12px;border-radius:6px;'>{open(file_path,'r',errors='ignore').read()}</pre>
        """
        return Response(html, mimetype='text/html')
    return data


@app.route("/upload", methods=["GET", "POST"])
def upload():
    message = None
    filename = None
    flag = None
    if request.method == "POST":
        if not session.get("user_id"):
            message = "Please login to upload."
        else:
            f = request.files.get("file")
            if f and f.filename:
                filename = f.filename
                ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                if ext in {"png", "jpg", "jpeg"}:
                    path = UPLOAD_DIR / filename
                    f.save(path)
                    message = "File uploaded successfully."
                else:
                    flag = "THM{arbitrary_file_upload_and_execute}"
                    path = UPLOAD_DIR / filename
                    f.save(path)
                    message = "Non-image file uploaded."
    return render_template("upload.html", message=message, filename=filename, flag=flag)


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(BASE_DIR / 'static' / 'images', filename)


@app.route('/flag/xss')
def flag_xss():
    return "THM{stored_xss_comment_pop_executed}"


@app.route('/flag/sqli')
def flag_sqli():
    return "THM{sqli_login_bypass_success}"


@app.route('/flag/idor')
def flag_idor():
    return "THM{insecure_direct_object_reference_profile}"


@app.route('/flag/path')
def flag_path():
    return "THM{directory_traversal_exposed_sensitive_file}"


@app.route('/flag/upload')
def flag_upload():
    return "THM{arbitrary_file_upload_and_execute}"


if __name__ == "__main__":
    init_db()
    seed_db()
    app.run(host="0.0.0.0", port=5003, debug=True)
