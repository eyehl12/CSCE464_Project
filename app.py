"""
UNListings Auction — Flask Application
=====================================
Run: python app.py
Then visit http://127.0.0.1:5005

Before first run, initialize the database:
    mysql -u root -proot < init.sql
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
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

# ─── Helpers ───────────────────────────────────────────


def clear_user_session():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)


def get_current_user():
    """Return current logged-in user info from session, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        clear_user_session()
        return None

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return user


def login_required(func):
    """Redirect anonymous users to /login."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("page_login"))
        return func(*args, **kwargs)

    return wrapped


def _time_left_str(ends_at):
    """Human-readable time remaining string."""
    if ends_at is None:
        return "N/A"
    now = datetime.now()
    diff = ends_at - now
    total_seconds = int(diff.total_seconds())
    if total_seconds <= 0:
        return "Ended"
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h left"
    if hours > 0:
        return f"{hours}h {minutes}m left"
    return f"{minutes}m left"


def listing_row_to_json(row):
    """Map a DB listing row to the JSON shape expected by the frontend."""
    current_bid_cents = row.get("current_bid_cents")
    starting = row["starting_price_cents"]
    price_cents = current_bid_cents if current_bid_cents else starting
    bid_count = row.get("bid_count", 0) or 0

    return {
        "id": row["id"],
        "title": row["title"],
        "description": row.get("description", ""),
        "image_url": row.get("image_url"),
        "category": row["category"],
        "category_label": CATEGORY_LABELS.get(row["category"], row["category"]),
        "starting_price": round(starting / 100, 2),
        "current_bid": round(current_bid_cents / 100, 2) if current_bid_cents else None,
        "price": round(price_cents / 100, 2),
        "bid_count": bid_count,
        "ends_at": row["ends_at"].isoformat() if row.get("ends_at") else None,
        "is_ended": row["ends_at"] < datetime.now() if row.get("ends_at") else False,
        "time_left": _time_left_str(row.get("ends_at")),
        "seller_id": row.get("seller_id"),
        "seller_name": row.get("seller_name", "Unknown"),
    }


# ─── Context Processor ────────────────────────────────


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


# ─── Page Routes ──────────────────────────────────────


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


@app.get("/sell")
@login_required
def page_sell():
    return render_template("sell.html")


@app.get("/listing/<int:listing_id>")
def page_listing(listing_id):
    return render_template("listing.html", listing_id=listing_id)


# ─── Auth API ─────────────────────────────────────────


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
    clear_user_session()
    return jsonify({"ok": True})


@app.post("/api/change-password")
def api_change_password():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

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
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

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

    clear_user_session()
    return jsonify({"ok": True})


# ─── Listings API ─────────────────────────────────────

LISTINGS_SELECT = """
    SELECT l.id, l.title, l.description, l.image_url, l.category,
           l.starting_price_cents, l.ends_at, l.seller_id, l.created_at,
           u.name AS seller_name,
           (SELECT MAX(b.amount_cents) FROM bids b WHERE b.listing_id = l.id) AS current_bid_cents,
           (SELECT COUNT(*)            FROM bids b WHERE b.listing_id = l.id) AS bid_count
    FROM listings l
    JOIN users u ON u.id = l.seller_id
"""


def build_listing_filter_clause(category, search_query):
    clauses = []
    params = []

    if category != "all":
        clauses.append("l.category = %s")
        params.append(category)

    if search_query:
        like_term = f"%{search_query}%"
        clauses.append("(l.title LIKE %s OR l.description LIKE %s OR u.name LIKE %s)")
        params.extend([like_term, like_term, like_term])

    if not clauses:
        return "", params

    return " WHERE " + " AND ".join(clauses), params


@app.get("/api/listings")
def api_listings():
    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, min(request.args.get("limit", 12, type=int), 50))
    category = request.args.get("category", "all")
    search_query = (request.args.get("q") or "").strip()
    offset = (page - 1) * limit

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    where_clause, filter_params = build_listing_filter_clause(category, search_query)

    cur.execute(
        "SELECT COUNT(*) AS total FROM listings l JOIN users u ON u.id = l.seller_id" + where_clause,
        tuple(filter_params),
    )
    total = cur.fetchone()["total"]

    cur.execute(
        LISTINGS_SELECT + where_clause + " ORDER BY l.ends_at ASC LIMIT %s OFFSET %s",
        tuple(filter_params + [limit, offset]),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(
        {
            "page": page,
            "limit": limit,
            "category": category,
            "query": search_query,
            "total": total,
            "listings": [listing_row_to_json(row) for row in rows],
        }
    )


@app.get("/api/listings/<int:listing_id>")
def api_listing_detail(listing_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(LISTINGS_SELECT + " WHERE l.id = %s", (listing_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify({"error": "Listing not found"}), 404

    result = listing_row_to_json(row)

    # Bid history (newest first)
    cur.execute(
        """
        SELECT b.amount_cents, b.created_at, u.name AS bidder_name
        FROM bids b
        JOIN users u ON u.id = b.bidder_id
        WHERE b.listing_id = %s
        ORDER BY b.amount_cents DESC, b.created_at DESC
        """,
        (listing_id,),
    )
    bids = cur.fetchall()
    result["bids"] = [
        {
            "bidder_name": b["bidder_name"],
            "amount": round(b["amount_cents"] / 100, 2),
            "created_at": b["created_at"].isoformat(),
        }
        for b in bids
    ]

    # If the current user is logged in, provide extra context
    current_user = get_current_user()
    if current_user:
        user_id = current_user["id"]
        result["user_is_seller"] = row["seller_id"] == user_id
        cur.execute(
            "SELECT MAX(amount_cents) AS max_bid FROM bids WHERE listing_id = %s AND bidder_id = %s",
            (listing_id, user_id),
        )
        user_bid_row = cur.fetchone()
        result["user_highest_bid"] = (
            round(user_bid_row["max_bid"] / 100, 2) if user_bid_row and user_bid_row["max_bid"] else None
        )
    else:
        result["user_is_seller"] = False
        result["user_highest_bid"] = None

    cur.close()
    conn.close()
    return jsonify(result)


@app.post("/api/listings")
def api_create_listing():
    """Create a new auction listing (login required)."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    category = data.get("category") or ""
    starting_price = data.get("starting_price")
    duration_value = data.get("duration_value", 24)

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not image_url:
        return jsonify({"error": "Image link is required"}), 400
    if category not in CATEGORY_LABELS:
        return jsonify({"error": "Invalid category"}), 400
    try:
        starting_price = float(starting_price)
        if starting_price < 0.01:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Starting price must be at least $0.01"}), 400
    try:
        if duration_value == "10s":
            auction_duration = timedelta(seconds=10)
        else:
            duration_hours = int(duration_value)
            if duration_hours < 1:
                raise ValueError
            auction_duration = timedelta(hours=duration_hours)
    except (TypeError, ValueError):
        return jsonify({"error": "Duration must be 10 seconds or at least 1 hour"}), 400

    starting_price_cents = round(starting_price * 100)
    ends_at = datetime.now() + auction_duration

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO listings (seller_id, title, description, image_url, category, starting_price_cents, ends_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (user_id, title, description, image_url, category, starting_price_cents, ends_at),
    )
    conn.commit()
    listing_id = cur.lastrowid
    cur.close()
    conn.close()

    return jsonify({"ok": True, "listing_id": listing_id}), 201


@app.delete("/api/listings/<int:listing_id>")
def api_delete_listing(listing_id):
    """Delete a listing owned by the current user."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, seller_id FROM listings WHERE id = %s", (listing_id,))
    listing = cur.fetchone()

    if not listing:
        cur.close()
        conn.close()
        return jsonify({"error": "Listing not found"}), 404

    if listing["seller_id"] != user_id:
        cur.close()
        conn.close()
        return jsonify({"error": "You can only delete your own listings"}), 403

    cur2 = conn.cursor()
    cur2.execute("DELETE FROM listings WHERE id = %s", (listing_id,))
    conn.commit()

    cur2.close()
    cur.close()
    conn.close()

    return jsonify({"ok": True})


@app.post("/api/listings/<int:listing_id>/bid")
def api_place_bid(listing_id):
    """Place a bid on a listing (login required)."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid bid amount"}), 400

    amount_cents = round(amount * 100)

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    # Fetch listing
    cur.execute("SELECT id, seller_id, starting_price_cents, ends_at FROM listings WHERE id = %s", (listing_id,))
    listing = cur.fetchone()
    if not listing:
        cur.close()
        conn.close()
        return jsonify({"error": "Listing not found"}), 404

    # Cannot bid on own listing
    if listing["seller_id"] == user_id:
        cur.close()
        conn.close()
        return jsonify({"error": "You cannot bid on your own listing"}), 403

    # Cannot bid on ended auction
    if listing["ends_at"] < datetime.now():
        cur.close()
        conn.close()
        return jsonify({"error": "This auction has ended"}), 400

    # Must be >= starting price
    if amount_cents < listing["starting_price_cents"]:
        cur.close()
        conn.close()
        return jsonify({"error": f"Bid must be at least ${listing['starting_price_cents'] / 100:.2f}"}), 400

    # Must be higher than current highest bid
    cur.execute("SELECT MAX(amount_cents) AS max_bid FROM bids WHERE listing_id = %s", (listing_id,))
    max_row = cur.fetchone()
    current_max = max_row["max_bid"] if max_row and max_row["max_bid"] else 0
    if amount_cents <= current_max:
        cur.close()
        conn.close()
        return jsonify({"error": f"Bid must be higher than ${current_max / 100:.2f}"}), 400

    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO bids (listing_id, bidder_id, amount_cents) VALUES (%s, %s, %s)",
        (listing_id, user_id, amount_cents),
    )
    conn.commit()

    cur2.close()
    cur.close()
    conn.close()

    return jsonify({"ok": True, "amount": amount, "listing_id": listing_id})


# ─── Profile Data API ─────────────────────────────────


@app.get("/api/my/listings")
def api_my_listings():
    """Get all listings created by the current user."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        LISTINGS_SELECT + " WHERE l.seller_id = %s ORDER BY l.created_at DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({"listings": [listing_row_to_json(r) for r in rows]})


@app.get("/api/my/bids")
def api_my_bids():
    """Get all listings the current user has bid on, with their highest bid."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT l.id, l.title, l.category, l.starting_price_cents, l.ends_at,
               l.seller_id, u.name AS seller_name,
               MAX(my.amount_cents) AS my_highest_cents,
               (SELECT MAX(b2.amount_cents) FROM bids b2 WHERE b2.listing_id = l.id) AS current_bid_cents,
               (SELECT COUNT(*)             FROM bids b2 WHERE b2.listing_id = l.id) AS bid_count
        FROM bids my
        JOIN listings l ON l.id = my.listing_id
        JOIN users u ON u.id = l.seller_id
        WHERE my.bidder_id = %s
        GROUP BY l.id
        ORDER BY l.ends_at ASC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for r in rows:
        item = listing_row_to_json(r)
        item["my_highest_bid"] = round(r["my_highest_cents"] / 100, 2)
        winning = r["current_bid_cents"] == r["my_highest_cents"]
        item["is_winning"] = winning
        results.append(item)

    return jsonify({"bids": results})


# ─── Main ─────────────────────────────────────────────


if __name__ == "__main__":
    print("UNListings API running at http://127.0.0.1:5005")
    print("Auction site:  http://127.0.0.1:5005/")
    print("Listings API:  http://127.0.0.1:5005/api/listings?page=1&limit=12")
    app.run(debug=True, port=5005)
