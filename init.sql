DROP DATABASE IF EXISTS campusbid;
CREATE DATABASE campusbid;
USE campusbid;

-- ═══════════════════════════════════════════════════════
-- Users
-- ═══════════════════════════════════════════════════════
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════
-- Auction Listings
-- ═══════════════════════════════════════════════════════
CREATE TABLE listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category ENUM('educational-items', 'university-merch', 'dorm-essentials', 'general-auction') NOT NULL,
    starting_price_cents INT NOT NULL,
    ends_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_listings_seller FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════════════
-- Bids
-- ═══════════════════════════════════════════════════════
CREATE TABLE bids (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    bidder_id INT NOT NULL,
    amount_cents INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bids_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    CONSTRAINT fk_bids_bidder  FOREIGN KEY (bidder_id)  REFERENCES users(id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════════════
-- Seed Users (passwords are all "password" hashed with werkzeug)
-- ═══════════════════════════════════════════════════════
INSERT INTO users (id, email, password_hash, name) VALUES
(1, 'alice@campus.edu',   'scrypt:32768:8:1$XvZ0LdFwYq$placeholder_hash_alice',   'Alice Johnson'),
(2, 'bob@campus.edu',     'scrypt:32768:8:1$XvZ0LdFwYq$placeholder_hash_bob',     'Bob Martinez'),
(3, 'carol@campus.edu',   'scrypt:32768:8:1$XvZ0LdFwYq$placeholder_hash_carol',   'Carol Chen'),
(4, 'dave@campus.edu',    'scrypt:32768:8:1$XvZ0LdFwYq$placeholder_hash_dave',    'Dave Williams');

-- ═══════════════════════════════════════════════════════
-- Seed Listings  (ends_at spread across future hours)
-- ═══════════════════════════════════════════════════════
INSERT INTO listings (id, seller_id, title, description, category, starting_price_cents, ends_at) VALUES
(1,  1, 'Engineering Calculator Pro',
     'TI-84 Plus CE in excellent condition. Comes with USB cable and protective cover. Barely used — switching majors.',
     'educational-items', 2500, DATE_ADD(NOW(), INTERVAL 9 HOUR)),
(2,  2, 'Organic Chemistry Model Kit',
     'Full molecular model set for Orgo I & II. All atoms and bonds present. Great for visual learners.',
     'educational-items', 1500, DATE_ADD(NOW(), INTERVAL 16 HOUR)),
(3,  3, 'Campus Lab Notebook Set',
     'Pack of 5 quad-ruled lab notebooks, unused. Required format for CHEM and PHYS labs.',
     'educational-items', 800, DATE_ADD(NOW(), INTERVAL 21 HOUR)),
(4,  1, 'Data Structures Textbook Bundle',
     'Includes "Introduction to Algorithms" (CLRS) 4th ed. and "Data Structures in Java". Some highlighting.',
     'educational-items', 3500, DATE_ADD(NOW(), INTERVAL 6 HOUR)),
(5,  4, 'University Crest Hoodie',
     'Official maroon hoodie, size L. Worn twice — too big for me. Tags still on hood.',
     'university-merch', 2000, DATE_ADD(NOW(), INTERVAL 12 HOUR)),
(6,  2, 'Alumni Stadium Scarf',
     'Limited-run game-day scarf from the 2025 homecoming. Still in packaging.',
     'university-merch', 1000, DATE_ADD(NOW(), INTERVAL 19 HOUR)),
(7,  3, 'Campus Spirit Water Bottle',
     '32 oz insulated bottle with university logo. Keeps drinks cold 24 hrs. No dents.',
     'university-merch', 800, DATE_ADD(NOW(), INTERVAL 30 HOUR)),
(8,  1, 'Limited Edition Mascot Cap',
     'Snap-back cap with embroidered mascot. Only 200 made for the spring rally.',
     'university-merch', 1200, DATE_ADD(NOW(), INTERVAL 14 HOUR)),
(9,  4, 'Compact Dorm Air Fryer',
     'Cosori 2-quart air fryer, perfect for dorm cooking. Used one semester. Includes recipe booklet.',
     'dorm-essentials', 3000, DATE_ADD(NOW(), INTERVAL 10 HOUR)),
(10, 2, 'Under-Bed Storage Trio',
     'Set of 3 rolling under-bed bins with lids. Clear plastic, great condition. Saves closet space.',
     'dorm-essentials', 1500, DATE_ADD(NOW(), INTERVAL 28 HOUR)),
(11, 3, 'Desk Lamp with USB Ports',
     'LED desk lamp with adjustable brightness, built-in USB-A and USB-C charging. Clamp mount.',
     'dorm-essentials', 1200, DATE_ADD(NOW(), INTERVAL 17 HOUR)),
(12, 1, 'Noise-Low Study Fan',
     'Honeywell HT-900 turbo fan. Whisper-quiet on low setting. Ideal for dorm white noise.',
     'dorm-essentials', 1000, DATE_ADD(NOW(), INTERVAL 22 HOUR)),
(13, 4, 'Mystery Campus Auction Box',
     'Sealed box of campus collectibles and merch. At least $40 retail value guaranteed. Fun surprise!',
     'general-auction', 500, DATE_ADD(NOW(), INTERVAL 8 HOUR)),
(14, 2, 'Vintage Lecture Hall Chair',
     'Salvaged oak lecture chair from the old Science building renovation. Heavy and solid.',
     'general-auction', 4000, DATE_ADD(NOW(), INTERVAL 5 HOUR)),
(15, 3, 'Student Art Showcase Print',
     'Signed 18×24 print from the 2025 BFA showcase. Abstract campus landscape by a graduating senior.',
     'general-auction', 1500, DATE_ADD(NOW(), INTERVAL 27 HOUR)),
(16, 4, 'Retro Bicycle Permit Plaque',
     'Original 1970s campus bicycle permit metal plaque. Unique dorm wall decor.',
     'general-auction', 800, DATE_ADD(NOW(), INTERVAL 36 HOUR));

-- ═══════════════════════════════════════════════════════
-- Seed Bids  (various users bidding on various listings)
-- ═══════════════════════════════════════════════════════
-- Listing 1: Engineering Calculator Pro (seller: Alice)
-- Listing 4: Data Structures Textbook Bundle (seller: Alice)
-- Listing 5: University Crest Hoodie (seller: Dave)
-- Listing 9: Compact Dorm Air Fryer (seller: Dave)
-- Listing 13: Mystery Campus Auction Box (seller: Dave)
-- Listing 14: Vintage Lecture Hall Chair (seller: Bob)
-- Listing 2: Organic Chemistry Model Kit (seller: Bob)
-- Listing 6: Alumni Stadium Scarf (seller: Bob)
-- Listing 11: Desk Lamp with USB Ports (seller: Carol)
-- A few listings with no bids yet: 3, 7, 8, 10, 12, 15, 16

INSERT INTO bids (listing_id, bidder_id, amount_cents, created_at) VALUES
(1, 2, 2600, DATE_SUB(NOW(), INTERVAL 5 HOUR)),
(1, 3, 2800, DATE_SUB(NOW(), INTERVAL 4 HOUR)),
(1, 4, 3200, DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(1, 2, 3500, DATE_SUB(NOW(), INTERVAL 1 HOUR)),
(4, 3, 3600, DATE_SUB(NOW(), INTERVAL 8 HOUR)),
(4, 4, 4200, DATE_SUB(NOW(), INTERVAL 6 HOUR)),
(4, 2, 5000, DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(5, 1, 2200, DATE_SUB(NOW(), INTERVAL 7 HOUR)),
(5, 3, 2500, DATE_SUB(NOW(), INTERVAL 5 HOUR)),
(5, 1, 3000, DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(9, 1, 3200, DATE_SUB(NOW(), INTERVAL 6 HOUR)),
(9, 2, 3800, DATE_SUB(NOW(), INTERVAL 4 HOUR)),
(9, 3, 4500, DATE_SUB(NOW(), INTERVAL 1 HOUR)),
(13, 1, 600, DATE_SUB(NOW(), INTERVAL 10 HOUR)),
(13, 2, 900, DATE_SUB(NOW(), INTERVAL 7 HOUR)),
(13, 3, 1200, DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(14, 1, 4500, DATE_SUB(NOW(), INTERVAL 9 HOUR)),
(14, 4, 5500, DATE_SUB(NOW(), INTERVAL 5 HOUR)),
(14, 1, 7000, DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(2, 1, 1600, DATE_SUB(NOW(), INTERVAL 6 HOUR)),
(2, 4, 2000, DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(6, 1, 1100, DATE_SUB(NOW(), INTERVAL 4 HOUR)),
(6, 4, 1400, DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(6, 1, 1800, DATE_SUB(NOW(), INTERVAL 1 HOUR)),
(11, 1, 1300, DATE_SUB(NOW(), INTERVAL 5 HOUR)),
(11, 2, 1600, DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(11, 4, 2000, DATE_SUB(NOW(), INTERVAL 1 HOUR));
