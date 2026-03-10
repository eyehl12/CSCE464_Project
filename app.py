"""
CampusBid Auction — Flask Application
=====================================
Run: python app.py
Then visit http://127.0.0.1:5005

Before first run, initialize the database:
    mysql -u root -proot < init.sql
"""

import os
import secrets
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_conn

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"
CORS(app)

CATEGORY_LABELS = {
    "educational-items": "Educational Items",
    "university-merch": "University Merch",
    "dorm-essentials": "Dorm Essentials",
    "general-auction": "General Auction",
}

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
NUM_IMAGES = len([name for name in os.listdir(IMAGE_DIR) if name.lower().endswith(".jpg")])


def get_guest_key():
    """Get or create a guest session key stored in the Flask session."""
    if "guest_key" not in session:
        session["guest_key"] = secrets.token_hex(16)
    return session["guest_key"]


def get_or_create_cart_id(guest_key):
    """Return the DB cart id for the current guest, creating it if needed."""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id FROM carts WHERE guest_key = %s", (guest_key,))
    row = cur.fetchone()
    if row:
        cart_id = row["id"]
    else:
        cur.execute("INSERT INTO carts (guest_key) VALUES (%s)", (guest_key,))
        conn.commit()
        cart_id = cur.lastrowid

    cur.close()
    conn.close()
    return cart_id


def get_current_user():
    """Return current logged-in user info from session, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return {
        "id": user_id,
        "name": session.get("user_name"),
        "email": session.get("user_email"),
    }


def login_required(func):
    """Redirect anonymous users to /login."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("page_login"))
        return func(*args, **kwargs)

    return wrapped


def product_row_to_json(row):
    """Map a DB product row to the JSON shape expected by the current frontend."""
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "category_label": CATEGORY_LABELS.get(row["category"], row["category"]),
        "price": round(row["price_cents"] / 100, 2),
        "rating": float(row["rating"]),
        "reviews": row["reviews"],
        "bid_count": row["bid_count"],
        "time_left": f"{row['time_left_hours']}h left",
        "image_url": f"/api/products/{row['id']}/image",
    }


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


@app.get("/")
def page_index():
    return render_template("index.html")


@app.get("/register")
def page_register():
    return render_template("register.html")


@app.get("/login")
def page_login():
    return render_template("login.html")


@app.get("/profile")
@login_required
def page_profile():
    return render_template("profile.html")


@app.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or not password or not name:
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Email already registered"}), 409

    password_hash = generate_password_hash(password)
    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)",
        (email, password_hash, name),
    )
    conn.commit()
    user_id = cur2.lastrowid

    session["user_id"] = user_id
    session["user_name"] = name
    session["user_email"] = email

    cur2.close()
    cur.close()
    conn.close()
    return jsonify({"ok": True, "user": {"id": user_id, "name": name}}), 201


@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, email, name, password_hash FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return jsonify({"ok": True, "user": {"id": user["id"], "name": user["name"]}})


@app.post("/api/logout")
def api_logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    return jsonify({"ok": True})


@app.post("/api/change-password")
def api_change_password():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row or not check_password_hash(row["password_hash"], old_password):
        cur.close()
        conn.close()
        return jsonify({"error": "Incorrect password"}), 401

    new_hash = generate_password_hash(new_password)
    cur2 = conn.cursor()
    cur2.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
    conn.commit()

    cur2.close()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/delete-account")
def api_delete_account():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        cur.close()
        conn.close()
        return jsonify({"error": "Invalid password"}), 401

    cur2 = conn.cursor()
    cur2.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()

    cur2.close()
    cur.close()
    conn.close()

    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    return jsonify({"ok": True})


@app.get("/api/products")
def api_products():
    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, min(request.args.get("limit", 12, type=int), 50))
    category = request.args.get("category", "all")
    offset = (page - 1) * limit

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    if category != "all":
        cur.execute("SELECT COUNT(*) AS total FROM products WHERE category = %s", (category,))
        total = cur.fetchone()["total"]
        cur.execute(
            "SELECT id, name, category, price_cents, rating, reviews, bid_count, time_left_hours "
            "FROM products WHERE category = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (category, limit, offset),
        )
    else:
        cur.execute("SELECT COUNT(*) AS total FROM products")
        total = cur.fetchone()["total"]
        cur.execute(
            "SELECT id, name, category, price_cents, rating, reviews, bid_count, time_left_hours "
            "FROM products ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(
        {
            "page": page,
            "limit": limit,
            "category": category,
            "total": total,
            "products": [product_row_to_json(row) for row in rows],
        }
    )


@app.get("/api/products/<int:product_id>")
def api_product_detail(product_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, name, category, price_cents, rating, reviews, bid_count, time_left_hours "
        "FROM products WHERE id = %s",
        (product_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product_row_to_json(row))


@app.get("/api/products/<int:product_id>/image")
def api_product_image(product_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Product not found"}), 404
    if NUM_IMAGES == 0:
        return jsonify({"error": "No images available"}), 404

    image_index = ((product_id - 1) % NUM_IMAGES) + 1
    return send_from_directory(IMAGE_DIR, f"product_{image_index}.jpg")


@app.get("/api/cart")
def api_cart():
    guest_key = get_guest_key()
    cart_id = get_or_create_cart_id(guest_key)

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT ci.product_id, ci.quantity, p.name, p.price_cents
        FROM cart_items ci
        JOIN products p ON p.id = ci.product_id
        WHERE ci.cart_id = %s
        ORDER BY p.name
        """,
        (cart_id,),
    )
    items = cur.fetchall()
    cur.close()
    conn.close()

    total_items = sum(item["quantity"] for item in items)
    total_price = round(sum((item["price_cents"] / 100) * item["quantity"] for item in items), 2)
    cart = [
        {
            "product_id": item["product_id"],
            "name": item["name"],
            "price": round(item["price_cents"] / 100, 2),
            "quantity": item["quantity"],
        }
        for item in items
    ]
    return jsonify({"total_items": total_items, "total_price": total_price, "cart": cart})


@app.post("/api/cart")
def api_cart_add():
    guest_key = get_guest_key()
    cart_id = get_or_create_cart_id(guest_key)
    data = request.get_json(silent=True) or {}
    product_id = int(data.get("product_id", 0))

    if product_id <= 0:
        return jsonify({"error": "Missing product_id"}), 400

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    if not product:
        cur.close()
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    cur2 = conn.cursor()
    cur2.execute(
        """
        INSERT INTO cart_items (cart_id, product_id, quantity)
        VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE quantity = quantity + 1
        """,
        (cart_id, product_id),
    )
    conn.commit()

    cur2.close()
    cur.close()
    conn.close()

    cart_data = api_cart().get_json()
    cart_data["message"] = "Added to bid list"
    return jsonify(cart_data)


@app.delete("/api/cart/<int:product_id>")
def api_cart_remove(product_id):
    guest_key = get_guest_key()
    cart_id = get_or_create_cart_id(guest_key)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart_items WHERE cart_id = %s AND product_id = %s", (cart_id, product_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(api_cart().get_json())


if __name__ == "__main__":
    print("CampusBid API running at http://127.0.0.1:5005")
    print("Auction site:  http://127.0.0.1:5005/")
    print("Listings:      http://127.0.0.1:5005/api/products?page=1&limit=12")
    app.run(debug=True, port=5005)
