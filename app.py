"""
CampusBid Auction — Flask API Backend
=====================================
Provides RESTful endpoints for listings and serves listing images.

Endpoints:
    GET  /api/products?page=1&limit=12&category=all  — paginated listing feed
    GET  /api/products/<id>                           — single listing detail
    GET  /api/products/<id>/image                     — listing image file
    POST /api/cart                                    — add listing to bid list
    GET  /api/cart                                    — view current bid list

Run:
    pip install flask flask-cors
    python app.py
"""

import os
import random

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Auction listing "database" — generated once at startup so every request
# sees the same catalog.
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"key": "educational-items", "label": "Educational Items"},
    {"key": "university-merch", "label": "University Merch"},
    {"key": "dorm-essentials", "label": "Dorm Essentials"},
    {"key": "general-auction", "label": "General Auction"},
]

THEME_WORDS = {
    "educational-items": ["Textbook Set", "Study Guide", "Lab Kit", "Calculator", "Reference Pack"],
    "university-merch": ["Hoodie", "Stadium Blanket", "Campus Cap", "Alumni Jacket", "Game Day Tee"],
    "dorm-essentials": ["Mini Fridge", "Desk Lamp", "Storage Caddy", "Laundry Hamper", "Twin Sheet Set"],
    "general-auction": ["Vintage Camera", "Bluetooth Speaker", "Board Game", "Art Print", "Travel Mug"],
}

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
NUM_IMAGES = len([f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(".jpg")])

random.seed(42)


def _generate_products(n=100):
    products = []
    for i in range(1, n + 1):
        category = CATEGORIES[(i - 1) % len(CATEGORIES)]
        item_name = random.choice(THEME_WORDS[category["key"]])
        bid_count = random.randint(3, 48)
        products.append(
            {
                "id": i,
                "name": f"{item_name} #{100 + i}",
                "category": category["key"],
                "category_label": category["label"],
                "price": round(random.uniform(15.0, 650.0), 2),
                "rating": round(random.uniform(3.4, 5.0), 1),
                "reviews": random.randint(20, 1200),
                "bid_count": bid_count,
                "time_left": f"{random.randint(2, 72)}h left",
                "image_url": f"/api/products/{i}/image",
            }
        )
    return products


PRODUCTS = _generate_products()

# ---------------------------------------------------------------------------
# Bid list — simple in-memory list (resets when server restarts)
# ---------------------------------------------------------------------------

CART = []


def _get_product_by_id(product_id):
    return next((item for item in PRODUCTS if item["id"] == product_id), None)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Serve the auction storefront page."""
    return render_template("index.html")


@app.route("/api/products")
def get_products():
    """Return a paginated slice of listings.

    Query params:
        page     — 1-based page number  (default 1)
        limit    — items per page        (default 12)
        category — category key          (default all)
    """
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 12, type=int)
    category = request.args.get("category", "all", type=str)

    page = max(1, page)
    limit = max(1, min(limit, 50))

    filtered = PRODUCTS
    if category != "all":
        filtered = [item for item in PRODUCTS if item["category"] == category]

    start = (page - 1) * limit
    end = start + limit
    batch = filtered[start:end]

    return jsonify(
        {
            "page": page,
            "limit": limit,
            "category": category,
            "total": len(filtered),
            "products": batch,
        }
    )


@app.route("/api/products/<int:product_id>")
def get_product(product_id):
    """Return a single listing by ID."""
    product = _get_product_by_id(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@app.route("/api/products/<int:product_id>/image")
def get_product_image(product_id):
    """Serve the image file for a listing."""
    if not _get_product_by_id(product_id):
        return jsonify({"error": "Product not found"}), 404
    if NUM_IMAGES == 0:
        return jsonify({"error": "No images available"}), 404

    image_index = ((product_id - 1) % NUM_IMAGES) + 1
    filename = f"product_{image_index}.jpg"
    return send_from_directory(IMAGE_DIR, filename)


@app.route("/api/cart", methods=["POST"])
def add_to_cart():
    """Add a listing to the bid list.

    Expects JSON body: { "product_id": 1 }
    If the listing already exists in the list, its quantity is incremented.
    """
    data = request.get_json()
    if not data or "product_id" not in data:
        return jsonify({"error": "Missing product_id"}), 400

    product_id = data["product_id"]
    product = _get_product_by_id(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    for item in CART:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            break
    else:
        CART.append(
            {
                "product_id": product_id,
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
            }
        )

    total_items = sum(item["quantity"] for item in CART)
    return jsonify({"message": "Added to bid list", "total_items": total_items, "cart": CART})


@app.route("/api/cart")
def view_cart():
    """Return the current bid list."""
    total_items = sum(item["quantity"] for item in CART)
    total_price = round(sum(item["price"] * item["quantity"] for item in CART), 2)
    return jsonify({
        "total_items": total_items,
        "total_price": total_price,
        "cart": CART,
    })


@app.route("/api/cart/<int:product_id>", methods=["DELETE"])
def remove_item(product_id):
    """Delete a listing from the bid list."""
    for item in CART:
        if item["product_id"] == product_id:
            CART.remove(item)
            break
    else:
        return jsonify({"error": "Product not found"}), 404

    total_items = sum(item["quantity"] for item in CART)
    total_price = round(sum(item["price"] * item["quantity"] for item in CART), 2)
    return jsonify({
        "total_items": total_items,
        "total_price": total_price,
        "cart": CART,
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("CampusBid API running at http://127.0.0.1:5005")
    print("Auction site:  http://127.0.0.1:5005/")
    print("Listings:      http://127.0.0.1:5005/api/products?page=1&limit=12")
    app.run(debug=True, port=5005)
