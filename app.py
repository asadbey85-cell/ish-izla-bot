import hmac
import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash


ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "data" / "platform.db"
SUBJECTS = ("Ingliz tili", "Matematika", "Tarix")
SEED = {
    "Ingliz tili": (
        ("I ___ a student.", ("am", "is", "are", "be"), 0),
        ("What is the plural of ‘child’?", ("childs", "children", "childes", "childrens"), 1),
        ("Choose the past form of ‘go’.", ("goed", "gone", "went", "going"), 2),
    ),
    "Matematika": (
        ("17 + 25 nechaga teng?", ("40", "42", "43", "45"), 1),
        ("9 × 8 nechaga teng?", ("64", "72", "81", "69"), 1),
        ("144 ning kvadrat ildizi nechaga teng?", ("11", "12", "13", "14"), 1),
    ),
    "Tarix": (
        ("Ikkinchi jahon urushi qaysi yilda tugagan?", ("1943", "1944", "1945", "1946"), 2),
        ("Qadimgi Misr qaysi daryo bo‘yida rivojlangan?", ("Nil", "Dajla", "Volga", "Amudaryo"), 0),
        ("Buyuk Ipak yo‘li asosan nimani bog‘lagan?", ("Sharq va G‘arbni", "Amerikalarni", "Faqat orollarni", "Afrika va Avstraliyani"), 0),
    ),
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)


def calculate_change(total, paid):
    total = float(total or 0)
    paid = float(paid or 0)
    if paid >= total:
        return round(paid - total, 2), 0
    return 0, round(total - paid, 2)


def build_receipt(items, payment_amount, total, change):
    return {
        "items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "line_total": item["line_total"],
            }
            for item in items
        ],
        "payment_amount": round(float(payment_amount or 0), 2),
        "total": round(float(total or 0), 2),
        "change": round(float(change or 0), 2),
    }


def db():
    if "db" not in g:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def initialize():
    connection = db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            full_name TEXT NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY, subject TEXT NOT NULL, prompt TEXT NOT NULL,
            a TEXT NOT NULL, b TEXT NOT NULL, c TEXT NOT NULL, d TEXT NOT NULL,
            answer INTEGER NOT NULL CHECK(answer BETWEEN 0 AND 3)
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            subject TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            photo_url TEXT,
            works TEXT NOT NULL,
            result TEXT NOT NULL,
            notes TEXT,
            likes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            employer_name TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            age TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT NOT NULL,
            description TEXT NOT NULL,
            salary TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    for subject, items in SEED.items():
        if not connection.execute(
            "SELECT 1 FROM questions WHERE subject = ? LIMIT 1", (subject,)
        ).fetchone():
            connection.executemany(
                "INSERT INTO questions (subject, prompt, a, b, c, d, answer) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(subject, prompt, *options, answer) for prompt, options, answer in items],
            )
    if not connection.execute("SELECT 1 FROM jobs LIMIT 1").fetchone():
        connection.executemany(
            "INSERT INTO jobs (employer_name, title, category, age, location, phone, description, salary) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("Oila market", "Sotuvchi", "Savdo", "18-30", "Toshkent", "+998901234567", "Do'kon ichida mahsulot sotish, mijozlarga xizmat ko'rsatish.", "2 500 000 so'm"),
                ("Navoiy qurilish", "Quruvchi", "Qurilish", "20-40", "Navoiy", "+998905554433", "Qurilish ishlari, betonga ishlash, ishchi guruhiga qo'shilish.", "3 000 000 so'm"),
            ],
        )
    if not connection.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        connection.executemany(
            "INSERT INTO products (code, name, price, stock) VALUES (?, ?, ?, ?)",
            [
                ("1001", "Non", 4500, 12),
                ("1002", "Suv", 3000, 18),
                ("1003", "Qahva", 8000, 9),
                ("1004", "Yog'", 12000, 7),
                ("1005", "Piyoz", 5500, 14),
            ],
        )
    connection.commit()


with app.app_context():
    initialize()


@app.before_request
def prepare_request():
    user_id = session.get("user_id")
    g.user = db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone() if user_id else None
    if request.method == "POST":
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400)
    if request.endpoint not in {"setup", "static", "usta", "like_usta", "masters", "like_master", "jobs", "game"}:
        has_admin = db().execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone()
        if not has_admin:
            return redirect(url_for("setup"))


@app.context_processor
def template_context():
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    return {"current_user": g.get("user"), "csrf_token": session["csrf_token"]}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    if g.user is None:
        return redirect(url_for("usta"))
    return redirect(url_for("admin" if g.user["role"] == "admin" else "dashboard"))


@app.route("/game")
def game():
    return render_template("game.html")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    connection = db()
    if connection.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone():
        return redirect(url_for("login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirmation", "")
        if len(username) < 3 or not name:
            flash("Ism va kamida 3 belgili login kiriting.", "error")
        elif len(password) < 10:
            flash("Admin paroli kamida 10 belgidan iborat bo‘lsin.", "error")
        elif password != confirm:
            flash("Parollar mos kelmadi.", "error")
        else:
            cursor = connection.execute(
                "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (username, name, generate_password_hash(password)),
            )
            connection.commit()
            session.clear()
            session["user_id"] = cursor.lastrowid
            flash("Admin akkaunti yaratildi.", "success")
            return redirect(url_for("admin"))
    return render_template("index.html", view="setup", title="Admin sozlamasi")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirmation", "")
        if len(username) < 3 or not name:
            flash("Ism va kamida 3 belgili login kiriting.", "error")
        elif len(password) < 8:
            flash("Parol kamida 8 belgidan iborat bo‘lsin.", "error")
        elif password != confirm:
            flash("Parollar mos kelmadi.", "error")
        else:
            try:
                db().execute(
                    "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, 'student')",
                    (username, name, generate_password_hash(password)),
                )
                db().commit()
            except sqlite3.IntegrityError:
                flash("Bu login band. Boshqasini tanlang.", "error")
            else:
                flash("Akkaunt yaratildi. Endi login qiling.", "success")
                return redirect(url_for("login"))
    return render_template("index.html", view="register", title="O‘quvchi akkaunti")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
        flash("Login yoki parol noto‘g‘ri.", "error")
    return render_template("index.html", view="login", title="Login")


@app.route("/usta", methods=["GET", "POST"])
def usta():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        photo_url = request.form.get("photo_url", "").strip()
        works = request.form.get("works", "").strip()
        result = request.form.get("result", "").strip()
        notes = request.form.get("notes", "").strip()
        photo_file = request.files.get("photo")
        photo_url = photo_url if photo_url.startswith(("https://", "http://")) else ""

        if not name or not phone or not location or not works or not result:
            flash("Ism, telefon, joy, qaysi ish qiladi va natija maydonlarini to‘ldiring.", "error")
        elif photo_file and photo_file.filename:
            extension = Path(secure_filename(photo_file.filename)).suffix.lower()
            if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
                flash("Rasm JPG, PNG yoki WEBP formatida bo‘lishi kerak.", "error")
            else:
                filename = f"master-{secrets.token_hex(12)}{extension}"
                upload_dir = ROOT / "static" / "uploads"
                upload_dir.mkdir(parents=True, exist_ok=True)
                photo_file.save(upload_dir / filename)
                photo_url = url_for("static", filename=f"uploads/{filename}")
                db().execute(
                    "INSERT INTO masters (name, phone, location, photo_url, works, result, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, phone, location, photo_url, works, result, notes),
                )
                db().commit()
                flash("Usta ma’lumotlari saqlandi.", "success")
                return redirect(url_for("usta"))
        else:
            db().execute(
                "INSERT INTO masters (name, phone, location, photo_url, works, result, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, phone, location, photo_url or "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=900&q=80", works, result, notes),
            )
            db().commit()
            flash("Usta ma’lumotlari saqlandi.", "success")
            return redirect(url_for("usta"))

    search_query = request.args.get("q", "").strip()
    search_location = request.args.get("location", "").strip()
    conditions = []
    parameters = []
    if search_query:
        pattern = f"%{search_query}%"
        conditions.append("(name LIKE ? OR works LIKE ? OR result LIKE ? OR notes LIKE ?)")
        parameters.extend([pattern] * 4)
    if search_location:
        conditions.append("location LIKE ?")
        parameters.append(f"%{search_location}%")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    master_rows = db().execute(
        f"SELECT * FROM masters {where_clause} ORDER BY likes DESC, id DESC", parameters
    ).fetchall()
    return render_template(
        "index.html",
        view="masters",
        masters=master_rows,
        query=search_query,
        location=search_location,
    )


@app.route("/masters", methods=["GET", "POST"])
def masters():
    return redirect(url_for("usta"))


@app.route("/usta/<int:master_id>/like", methods=["POST"])
def like_usta(master_id):
    db().execute("UPDATE masters SET likes = likes + 1 WHERE id = ?", (master_id,))
    db().commit()
    return redirect(url_for("usta"))


@app.route("/masters/<int:master_id>/like", methods=["POST"])
def like_master(master_id):
    return redirect(url_for("like_usta", master_id=master_id), code=307)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if g.user["role"] != "student":
        return redirect(url_for("admin"))
    counts = {row["subject"]: row["n"] for row in db().execute(
        "SELECT subject, COUNT(*) n FROM questions GROUP BY subject"
    )}
    recent = db().execute(
        "SELECT * FROM results WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (g.user["id"],),
    ).fetchall()
    return render_template("index.html", view="dashboard", subjects=SUBJECTS, counts=counts, recent=recent)


@app.route("/quiz/<subject>", methods=["GET", "POST"])
@login_required
def quiz(subject):
    if g.user["role"] != "student":
        abort(403)
    if subject not in SUBJECTS:
        abort(404)
    questions = db().execute("SELECT * FROM questions WHERE subject = ? ORDER BY id", (subject,)).fetchall()
    if request.method == "POST":
        score = 0
        for question in questions:
            try:
                answer = int(request.form.get(f"answer-{question['id']}", "-1"))
            except ValueError:
                answer = -1
            score += answer == question["answer"]
        cursor = db().execute(
            "INSERT INTO results (user_id, subject, score, total) VALUES (?, ?, ?, ?)",
            (g.user["id"], subject, score, len(questions)),
        )
        db().commit()
        return redirect(url_for("result", result_id=cursor.lastrowid))
    return render_template("index.html", view="quiz", subject=subject, questions=questions)


@app.route("/result/<int:result_id>")
@login_required
def result(result_id):
    row = db().execute(
        "SELECT results.*, users.username, users.full_name FROM results JOIN users ON users.id = results.user_id WHERE results.id = ?",
        (result_id,),
    ).fetchone()
    if row is None:
        abort(404)
    if g.user["role"] != "admin" and row["user_id"] != g.user["id"]:
        abort(403)
    percent = round(row["score"] * 100 / row["total"])
    return render_template("index.html", view="result", result=row, percent=percent)


@app.route("/leaderboard")
@login_required
def leaderboard():
    rows = db().execute(
        """SELECT users.id, users.username, users.full_name,
                  SUM(results.score) points, SUM(results.total) total,
                  COUNT(results.id) tests
           FROM users JOIN results ON results.user_id = users.id
           WHERE users.role = 'student' GROUP BY users.id
           ORDER BY 1.0 * SUM(results.score) / SUM(results.total) DESC,
                    SUM(results.score) DESC LIMIT 100"""
    ).fetchall()
    return render_template("index.html", view="leaderboard", rows=rows)


@app.route("/jobs", methods=["GET", "POST"])
def jobs():
    connection = db()
    if request.method == "POST":
        action = request.form.get("action", "search")

        if action == "post_job":
            employer = request.form.get("employer_name", "").strip()
            title = request.form.get("title", "").strip()
            category = request.form.get("category", "").strip()
            age = request.form.get("age", "").strip()
            location = request.form.get("location", "").strip()
            phone = request.form.get("phone", "").strip()
            description = request.form.get("description", "").strip()
            salary = request.form.get("salary", "").strip()

            if not all([employer, title, category, age, location, phone, description]):
                flash("Barcha kerakli maydonlarni to‘ldiring.", "error")
            else:
                connection.execute(
                    "INSERT INTO jobs (employer_name, title, category, age, location, phone, description, salary) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (employer, title, category, age, location, phone, description, salary or "Kelishuv asosida"),
                )
                connection.commit()
                flash("Ish e’loningiz saqlandi.", "success")
            return redirect(url_for("jobs"))

        search_query = request.form.get("search_query", "").strip()
        search_location = request.form.get("search_location", "").strip()
        search_category = request.form.get("search_category", "").strip()
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        if search_query:
            query += " AND (title LIKE ? OR description LIKE ? OR employer_name LIKE ? OR category LIKE ?)"
            like = f"%{search_query}%"
            params.extend([like, like, like, like])
        if search_location:
            query += " AND location LIKE ?"
            params.append(f"%{search_location}%")
        if search_category:
            query += " AND category LIKE ?"
            params.append(f"%{search_category}%")
        query += " ORDER BY created_at DESC"
        jobs_rows = connection.execute(query, params).fetchall()
        return render_template("index.html", view="jobs", jobs=jobs_rows, query=search_query, location=search_location, category=search_category)

    jobs_rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return render_template("index.html", view="jobs", jobs=jobs_rows)


@app.route("/cashier", methods=["GET", "POST"])
@admin_required
def cashier():
    connection = db()
    cart = session.get("cashier_cart", {})
    products = connection.execute("SELECT * FROM products ORDER BY name").fetchall()

    if request.method == "POST":
        action = request.form.get("action", "add_item")

        if action == "add_item":
            code = request.form.get("product_code", "").strip()
            try:
                quantity = int(request.form.get("quantity", "1") or 1)
            except ValueError:
                quantity = 1
            if quantity < 1:
                quantity = 1

            product = connection.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
            if product is None:
                flash("Bunday barcode/QR kod topilmadi.", "error")
            elif product["stock"] < quantity:
                flash(f"{product['name']} uchun yetarli mahsulot qolmadi.", "error")
            else:
                cart = session.setdefault("cashier_cart", {})
                product_key = str(product["id"])
                cart[product_key] = cart.get(product_key, 0) + quantity
                session["cashier_cart"] = cart
                flash(f"{product['name']} savatga qo‘shildi.", "success")

        elif action == "clear_cart":
            session.pop("cashier_cart", None)
            flash("Savat tozalandi.", "success")

        elif action == "checkout":
            cart = session.get("cashier_cart", {})
            if not cart:
                flash("Oldin mahsulot qo‘shing.", "error")
            else:
                total = 0.0
                cart_entries = []
                for product_id, quantity in cart.items():
                    product = connection.execute("SELECT * FROM products WHERE id = ?", (int(product_id),)).fetchone()
                    if product is None:
                        continue
                    total += float(product["price"]) * int(quantity)
                    cart_entries.append((product, int(quantity)))

                if not cart_entries:
                    flash("Savatda yaroqli mahsulot yo‘q.", "error")
                else:
                    try:
                        payment_amount = float(request.form.get("payment_amount", "0") or 0)
                    except ValueError:
                        payment_amount = 0
                    change, debt = calculate_change(total, payment_amount)

                    if debt > 0:
                        flash(f"To‘lov yetarli emas. Qolgan summa: {debt:.0f} so‘m.", "error")
                    else:
                        checkout_items = [
                            {
                                "name": product["name"],
                                "quantity": quantity,
                                "price": float(product["price"]),
                                "line_total": round(float(product["price"]) * quantity, 2),
                            }
                            for product, quantity in cart_entries
                        ]
                        for product, quantity in cart_entries:
                            connection.execute(
                                "UPDATE products SET stock = stock - ? WHERE id = ?",
                                (quantity, product["id"]),
                            )
                        connection.commit()
                        receipt = build_receipt(checkout_items, payment_amount, total, change)
                        session["last_receipt"] = receipt
                        session.pop("cashier_cart", None)
                        flash(f"Hisob bajarildi. Qaytim: {change:.0f} so‘m.", "success")

        return redirect(url_for("cashier"))

    cart_rows = []
    cart_total = 0.0
    for product_id, quantity in session.get("cashier_cart", {}).items():
        product = connection.execute("SELECT * FROM products WHERE id = ?", (int(product_id),)).fetchone()
        if product is None:
            continue
        line_total = float(product["price"]) * int(quantity)
        cart_total += line_total
        cart_rows.append({
            "id": product["id"],
            "name": product["name"],
            "code": product["code"],
            "price": product["price"],
            "quantity": int(quantity),
            "line_total": round(line_total, 2),
        })

    return render_template(
        "index.html",
        view="cashier",
        products=products,
        cart_rows=cart_rows,
        cart_total=round(cart_total, 2),
        last_receipt=session.get("last_receipt"),
    )


@app.route("/receipt")
@admin_required
def receipt():
    receipt_data = session.get("last_receipt")
    if receipt_data is None:
        flash("Chek mavjud emas. Avval hisob qilish kerak.", "error")
        return redirect(url_for("cashier"))
    return render_template("receipt.html", receipt=receipt_data)


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    connection = db()
    if request.method == "POST":
        subject = request.form.get("subject", "")
        prompt = request.form.get("prompt", "").strip()
        options = [request.form.get(f"option_{key}", "").strip() for key in "abcd"]
        try:
            answer = int(request.form.get("answer", "-1"))
        except ValueError:
            answer = -1
        if subject not in SUBJECTS or not prompt or any(not option for option in options):
            flash("Fan, savol va barcha variantlarni to‘ldiring.", "error")
        elif answer not in range(4):
            flash("To‘g‘ri javobni belgilang.", "error")
        else:
            connection.execute(
                "INSERT INTO questions (subject, prompt, a, b, c, d, answer) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (subject, prompt, *options, answer),
            )
            connection.commit()
            flash("Test savoli qo‘shildi.", "success")
            return redirect(url_for("admin"))
    questions = connection.execute("SELECT * FROM questions ORDER BY subject, id DESC").fetchall()
    student_count = connection.execute("SELECT COUNT(*) n FROM users WHERE role = 'student'").fetchone()["n"]
    return render_template("index.html", view="admin", subjects=SUBJECTS, questions=questions, student_count=student_count)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)