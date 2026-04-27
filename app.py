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

CAMPUS_LOCATIONS = [
    "Abel",
    "Sandoz",
    "Harper",
    "Smith",
    "Schramm",
    "Suites",
    "Villages",
    "Courtyards",
    "Academy",
    "Livred",
    "Latitude",
    "8n",
    "Atmosphere",
    "50/50s",
    "Bottoms",
    "Other",
]

CANONICAL_LOCATION_LOOKUP = {location.lower(): location for location in CAMPUS_LOCATIONS}

# ─── Helpers ───────────────────────────────────────────


def clear_user_session():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)


def normalize_campus_location(value):
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    direct_match = CANONICAL_LOCATION_LOOKUP.get(cleaned.lower())
    if direct_match:
        return direct_match

    lowered = cleaned.lower()
    keyword_map = {
        "abel": "Abel",
        "sandoz": "Sandoz",
        "harper": "Harper",
        "smith": "Smith",
        "schramm": "Schramm",
        "suite": "Suites",
        "village": "Villages",
        "courtyard": "Courtyards",
        "academy": "Academy",
        "livred": "Livred",
        "latitude": "Latitude",
        "8n": "8n",
        "atmosphere": "Atmosphere",
        "50/50": "50/50s",
        "bottom": "Bottoms",
        "other": "Other",
    }

    for keyword, canonical in keyword_map.items():
        if keyword in lowered:
            return canonical

    return None


def parse_selected_locations(raw_locations, allow_empty=False):
    if not raw_locations:
        return list(CAMPUS_LOCATIONS)

    selected = []
    seen = set()
    for raw_value in raw_locations:
        normalized = normalize_campus_location(raw_value)
        if normalized and normalized not in seen:
            selected.append(normalized)
            seen.add(normalized)

    if selected:
        return selected

    if allow_empty:
        return []

    return list(CAMPUS_LOCATIONS)


def get_current_user():
    """Return current logged-in user info from session, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, email, campus_location FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        clear_user_session()
        return None

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    session["user_campus_location"] = user["campus_location"]
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
        "seller_campus_location": row.get("seller_campus_location"),
        "pickup_location": row.get("pickup_location"),
    }


# ─── Context Processor ────────────────────────────────


@app.context_processor
def inject_user():
    return {"current_user": get_current_user(), "campus_locations": CAMPUS_LOCATIONS}


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


@app.get("/seller/<int:seller_id>")
def page_seller(seller_id):
    return render_template("seller.html", seller_id=seller_id)


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
    session["user_campus_location"] = None

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


@app.post("/api/profile")
def api_update_profile():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json(silent=True) or {}
    campus_location = normalize_campus_location(data.get("campus_location"))

    if data.get("campus_location") and campus_location is None:
        return jsonify({"error": "Please choose a valid campus location"}), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET campus_location = %s WHERE id = %s", (campus_location, current_user["id"]))
    conn.commit()
    cur.close()
    conn.close()

    session["user_campus_location"] = campus_location
    return jsonify({"ok": True, "campus_location": campus_location})


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
           l.pickup_location,
           u.name AS seller_name,
           u.campus_location AS seller_campus_location,
           (SELECT MAX(b.amount_cents) FROM bids b WHERE b.listing_id = l.id) AS current_bid_cents,
           (SELECT COUNT(*)            FROM bids b WHERE b.listing_id = l.id) AS bid_count
    FROM listings l
    JOIN users u ON u.id = l.seller_id
"""

PUBLIC_LISTING_VISIBILITY_CLAUSE = "DATE_ADD(l.ends_at, INTERVAL 2 MINUTE) > NOW()"


def build_listing_filter_clause(category, search_query, seller_locations=None):
    clauses = []
    params = []

    if category != "all":
        clauses.append("l.category = %s")
        params.append(category)

    if search_query:
        like_term = f"%{search_query}%"
        clauses.append("(l.title LIKE %s OR l.description LIKE %s OR u.name LIKE %s)")
        params.extend([like_term, like_term, like_term])

    if seller_locations == []:
        clauses.append("1 = 0")
    elif seller_locations and len(seller_locations) < len(CAMPUS_LOCATIONS):
        placeholders = ", ".join(["%s"] * len(seller_locations))
        clauses.append(f"u.campus_location IN ({placeholders})")
        params.extend(seller_locations)

    if not clauses:
        return "", params

    return " WHERE " + " AND ".join(clauses), params


def build_public_listing_filter_clause(category, search_query, seller_locations):
    where_clause, params = build_listing_filter_clause(category, search_query, seller_locations)

    if where_clause:
        return where_clause + f" AND {PUBLIC_LISTING_VISIBILITY_CLAUSE}", params

    return f" WHERE {PUBLIC_LISTING_VISIBILITY_CLAUSE}", params


@app.get("/api/listings")
def api_listings():
    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, min(request.args.get("limit", 12, type=int), 50))
    category = request.args.get("category", "all")
    search_query = (request.args.get("q") or "").strip()
    sort = request.args.get("sort", "default")
    location_mode = request.args.get("location_mode", "all")
    selected_locations = parse_selected_locations(
        request.args.getlist("location"),
        allow_empty=location_mode == "none",
    )
    offset = (page - 1) * limit

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    where_clause, filter_params = build_public_listing_filter_clause(category, search_query, selected_locations)

    cur.execute(
        "SELECT COUNT(*) AS total FROM listings l JOIN users u ON u.id = l.seller_id" + where_clause,
        tuple(filter_params),
    )
    total = cur.fetchone()["total"]

    if sort == "hot":
        order_clause = " ORDER BY CASE WHEN l.ends_at > NOW() THEN 0 ELSE 1 END ASC, bid_count DESC, l.ends_at ASC"
    else:
        order_clause = " ORDER BY CASE WHEN l.ends_at > NOW() THEN 0 ELSE 1 END ASC, l.ends_at ASC"

    cur.execute(
        LISTINGS_SELECT + where_clause + order_clause + " LIMIT %s OFFSET %s",
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
            "locations": selected_locations,
            "query": search_query,
            "sort": sort,
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

    # Winner info for ended auctions
    if result["is_ended"] and bids:
        result["winner_name"] = bids[0]["bidder_name"]
        result["winner_amount"] = round(bids[0]["amount_cents"] / 100, 2)
    else:
        result["winner_name"] = None
        result["winner_amount"] = None

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

    # Watchlist status
    if current_user:
        cur.execute(
            "SELECT id FROM watchlist WHERE user_id = %s AND listing_id = %s",
            (current_user["id"], listing_id),
        )
        result["user_watching"] = cur.fetchone() is not None
    else:
        result["user_watching"] = False

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
    pickup_location = (data.get("pickup_location") or "").strip() or None

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
        "INSERT INTO listings (seller_id, title, description, image_url, category, starting_price_cents, pickup_location, ends_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (user_id, title, description, image_url, category, starting_price_cents, pickup_location, ends_at),
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

    # Must be higher than current highest bid (minimum $0.25 increment)
    cur.execute("SELECT MAX(amount_cents) AS max_bid FROM bids WHERE listing_id = %s", (listing_id,))
    max_row = cur.fetchone()
    current_max = max_row["max_bid"] if max_row and max_row["max_bid"] else 0

    # Cannot outbid yourself if you are already the highest bidder
    if current_max > 0:
        cur.execute(
            "SELECT bidder_id FROM bids WHERE listing_id = %s ORDER BY amount_cents DESC, created_at DESC LIMIT 1",
            (listing_id,),
        )
        top_row = cur.fetchone()
        if top_row and top_row["bidder_id"] == user_id:
            cur.close()
            conn.close()
            return jsonify({"error": "You are already the highest bidder"}), 400

    min_next_bid = current_max + 25  # $0.25 minimum increment
    if amount_cents < min_next_bid:
        cur.close()
        conn.close()
        return jsonify({"error": f"Bid must be at least ${min_next_bid / 100:.2f} ($0.25 minimum increment)"}), 400

    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO bids (listing_id, bidder_id, amount_cents) VALUES (%s, %s, %s)",
        (listing_id, user_id, amount_cents),
    )

    # Auto-extend auction by 15 seconds if bid placed in the last 2 minutes
    time_remaining = (listing["ends_at"] - datetime.now()).total_seconds()
    if time_remaining <= 120:
        cur2.execute(
            "UPDATE listings SET ends_at = ends_at + INTERVAL 15 SECOND WHERE id = %s",
            (listing_id,),
        )

    conn.commit()

    cur2.close()
    cur.close()
    conn.close()

    return jsonify({"ok": True, "amount": amount, "listing_id": listing_id})


# ─── User Profile API ─────────────────────────────────


@app.get("/api/users/<int:user_id>")
def api_user_profile(user_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, campus_location, created_at FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404
    cur.execute("SELECT COUNT(*) AS cnt FROM listings WHERE seller_id = %s AND ends_at > NOW()", (user_id,))
    active = cur.fetchone()["cnt"]
    cur.execute("SELECT COUNT(*) AS cnt FROM listings WHERE seller_id = %s", (user_id,))
    total = cur.fetchone()["cnt"]
    cur.close()
    conn.close()
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "campus_location": user["campus_location"],
        "created_at": user["created_at"].isoformat(),
        "active_listings": active,
        "total_listings": total,
    })


@app.get("/api/users/<int:user_id>/listings")
def api_user_listings(user_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        LISTINGS_SELECT + " WHERE l.seller_id = %s"
        " ORDER BY CASE WHEN l.ends_at > NOW() THEN 0 ELSE 1 END ASC, l.ends_at ASC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"listings": [listing_row_to_json(r) for r in rows]})


# ─── General Chat API ─────────────────────────────────


@app.get("/api/chat/general")
def api_chat_general_get():
    since = request.args.get("since", 0, type=int)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    if since == 0:
        cur.execute(
            """SELECT gc.id, gc.user_id, gc.message, gc.created_at, u.name AS user_name
               FROM general_chat gc JOIN users u ON u.id = gc.user_id
               ORDER BY gc.id DESC LIMIT 50"""
        )
        rows = list(reversed(cur.fetchall()))
    else:
        cur.execute(
            """SELECT gc.id, gc.user_id, gc.message, gc.created_at, u.name AS user_name
               FROM general_chat gc JOIN users u ON u.id = gc.user_id
               WHERE gc.id > %s ORDER BY gc.id ASC""",
            (since,),
        )
        rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({
        "messages": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "user_name": r["user_name"],
                "message": r["message"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    })


@app.post("/api/chat/general")
def api_chat_general_post():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if len(message) > 1000:
        return jsonify({"error": "Message too long"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO general_chat (user_id, message) VALUES (%s, %s)", (current_user["id"], message))
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    return jsonify({"ok": True, "id": new_id}), 201


# ─── Conversations API ────────────────────────────────


@app.get("/api/conversations")
def api_conversations_list():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT c.id, c.user1_id, c.user2_id, c.listing_id,
               u1.name AS user1_name, u2.name AS user2_name,
               l.title AS listing_title,
               (SELECT COUNT(*) FROM messages m
                WHERE m.conversation_id = c.id AND m.sender_id != %s AND m.is_read = 0) AS unread_count,
               (SELECT m2.body FROM messages m2
                WHERE m2.conversation_id = c.id ORDER BY m2.id DESC LIMIT 1) AS last_body,
               (SELECT m2.created_at FROM messages m2
                WHERE m2.conversation_id = c.id ORDER BY m2.id DESC LIMIT 1) AS last_msg_at
        FROM conversations c
        JOIN users u1 ON u1.id = c.user1_id
        JOIN users u2 ON u2.id = c.user2_id
        LEFT JOIN listings l ON l.id = c.listing_id
        WHERE c.user1_id = %s OR c.user2_id = %s
        ORDER BY last_msg_at DESC, c.created_at DESC
        """,
        (user_id, user_id, user_id),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for r in rows:
        other_id = r["user2_id"] if r["user1_id"] == user_id else r["user1_id"]
        other_name = r["user2_name"] if r["user1_id"] == user_id else r["user1_name"]
        result.append({
            "id": r["id"],
            "other_user": {"id": other_id, "name": other_name},
            "listing_title": r["listing_title"],
            "unread_count": r["unread_count"] or 0,
            "last_message": {
                "body": r["last_body"],
                "created_at": r["last_msg_at"].isoformat() if r["last_msg_at"] else None,
            } if r["last_body"] else None,
        })
    return jsonify({"conversations": result})


@app.post("/api/conversations")
def api_conversations_create():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]
    data = request.get_json(silent=True) or {}
    other_user_id = data.get("other_user_id")
    listing_id = data.get("listing_id") or None
    if not other_user_id or other_user_id == user_id:
        return jsonify({"error": "Invalid user"}), 400
    u1 = min(user_id, other_user_id)
    u2 = max(user_id, other_user_id)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM users WHERE id = %s", (other_user_id,))
    other_user = cur.fetchone()
    if not other_user:
        cur.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404
    listing_title = None
    if listing_id:
        cur.execute("SELECT title FROM listings WHERE id = %s", (listing_id,))
        lr = cur.fetchone()
        listing_title = lr["title"] if lr else None
    cur.execute("SELECT id FROM conversations WHERE user1_id = %s AND user2_id = %s", (u1, u2))
    existing = cur.fetchone()
    if existing:
        conv_id = existing["id"]
        if listing_id:
            cur2 = conn.cursor()
            cur2.execute("UPDATE conversations SET listing_id = %s WHERE id = %s", (listing_id, conv_id))
            conn.commit()
            cur2.close()
        created = False
    else:
        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO conversations (user1_id, user2_id, listing_id) VALUES (%s, %s, %s)",
            (u1, u2, listing_id),
        )
        conn.commit()
        conv_id = cur2.lastrowid
        cur2.close()
        created = True
    cur.close()
    conn.close()
    return jsonify({
        "ok": True,
        "conversation_id": conv_id,
        "created": created,
        "other_user_name": other_user["name"],
        "listing_title": listing_title,
    }), 201 if created else 200


@app.get("/api/conversations/unread")
def api_conversations_unread():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"total_unread": 0})
    user_id = current_user["id"]
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT COUNT(*) AS total FROM messages m
           JOIN conversations c ON c.id = m.conversation_id
           WHERE (c.user1_id = %s OR c.user2_id = %s)
             AND m.sender_id != %s AND m.is_read = 0""",
        (user_id, user_id, user_id),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"total_unread": row["total"] or 0})


@app.get("/api/conversations/<int:conv_id>/messages")
def api_conv_messages_get(conv_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id FROM conversations WHERE id = %s AND (user1_id = %s OR user2_id = %s)",
        (conv_id, user_id, user_id),
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    since = request.args.get("since", 0, type=int)
    if since == 0:
        cur.execute(
            """SELECT m.id, m.sender_id, m.body, m.created_at, u.name AS sender_name
               FROM messages m JOIN users u ON u.id = m.sender_id
               WHERE m.conversation_id = %s ORDER BY m.id DESC LIMIT 50""",
            (conv_id,),
        )
        rows = list(reversed(cur.fetchall()))
    else:
        cur.execute(
            """SELECT m.id, m.sender_id, m.body, m.created_at, u.name AS sender_name
               FROM messages m JOIN users u ON u.id = m.sender_id
               WHERE m.conversation_id = %s AND m.id > %s ORDER BY m.id ASC""",
            (conv_id, since),
        )
        rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({
        "messages": [
            {
                "id": r["id"],
                "sender_id": r["sender_id"],
                "sender_name": r["sender_name"],
                "body": r["body"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    })


@app.post("/api/conversations/<int:conv_id>/messages")
def api_conv_messages_post(conv_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id FROM conversations WHERE id = %s AND (user1_id = %s OR user2_id = %s)",
        (conv_id, user_id, user_id),
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Message is required"}), 400
    if len(body) > 2000:
        return jsonify({"error": "Message too long"}), 400
    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO messages (conversation_id, sender_id, body) VALUES (%s, %s, %s)",
        (conv_id, user_id, body),
    )
    conn.commit()
    new_id = cur2.lastrowid
    cur2.close()
    cur.close()
    conn.close()
    return jsonify({"ok": True, "id": new_id}), 201


@app.post("/api/conversations/<int:conv_id>/read")
def api_conv_read(conv_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401
    user_id = current_user["id"]
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id FROM conversations WHERE id = %s AND (user1_id = %s OR user2_id = %s)",
        (conv_id, user_id, user_id),
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    cur2 = conn.cursor()
    cur2.execute(
        "UPDATE messages SET is_read = 1 WHERE conversation_id = %s AND sender_id != %s",
        (conv_id, user_id),
    )
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


# ─── Watchlist API ───────────────────────────────────


@app.post("/api/watchlist/<int:listing_id>")
def api_watchlist_add(listing_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT IGNORE INTO watchlist (user_id, listing_id) VALUES (%s, %s)",
            (current_user["id"], listing_id),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return jsonify({"ok": True, "watching": True})


@app.delete("/api/watchlist/<int:listing_id>")
def api_watchlist_remove(listing_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM watchlist WHERE user_id = %s AND listing_id = %s",
            (current_user["id"], listing_id),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return jsonify({"ok": True, "watching": False})


@app.get("/api/my/watchlist")
def api_my_watchlist():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Login required"}), 401

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        LISTINGS_SELECT + " JOIN watchlist w ON w.listing_id = l.id"
        " WHERE w.user_id = %s ORDER BY w.created_at DESC",
        (current_user["id"],),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"watchlist": [listing_row_to_json(r) for r in rows]})


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
