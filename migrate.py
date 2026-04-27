"""
Run this once to apply schema changes without wiping existing data:
    python migrate.py
"""
from db import get_conn

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

conn = get_conn()
cur = conn.cursor()


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

    return "Other"

def column_exists(table, column):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column),
    )
    return cur.fetchone()[0] > 0

def table_exists(table):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
        (table,),
    )
    return cur.fetchone()[0] > 0

# users.campus_location
if not column_exists("users", "campus_location"):
    cur.execute("ALTER TABLE users ADD COLUMN campus_location VARCHAR(255) DEFAULT NULL")
    print("Added users.campus_location")
else:
    print("users.campus_location already exists")

cur.execute("SELECT id, campus_location FROM users")
user_rows = cur.fetchall()
normalized_count = 0
for user_id, campus_location in user_rows:
    normalized_location = normalize_campus_location(campus_location)
    if normalized_location != campus_location:
        cur.execute("UPDATE users SET campus_location = %s WHERE id = %s", (normalized_location, user_id))
        normalized_count += 1
print(f"Normalized users.campus_location values: {normalized_count}")

# listings.pickup_location
if not column_exists("listings", "pickup_location"):
    cur.execute("ALTER TABLE listings ADD COLUMN pickup_location VARCHAR(255) DEFAULT NULL")
    print("Added listings.pickup_location")
else:
    print("listings.pickup_location already exists")

# watchlist table
if not table_exists("watchlist"):
    cur.execute("""
        CREATE TABLE watchlist (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            listing_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_watchlist (user_id, listing_id),
            CONSTRAINT fk_watchlist_user    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
            CONSTRAINT fk_watchlist_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
        )
    """)
    print("Created watchlist table")
else:
    print("watchlist table already exists")

conn.commit()
cur.close()
conn.close()
print("Migration complete.")
