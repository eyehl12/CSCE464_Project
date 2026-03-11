DROP DATABASE IF EXISTS unlistings;
CREATE DATABASE unlistings;
USE unlistings;

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
    image_url TEXT NOT NULL,
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
INSERT INTO listings (id, seller_id, title, description, image_url, category, starting_price_cents, ends_at) VALUES
(1,  1, 'Engineering Calculator Pro',
     'TI-84 Plus CE in excellent condition. Comes with USB cable and protective cover. Barely used — switching majors.',
    'https://picsum.photos/seed/listing-1/800/600',
     'educational-items', 2500, DATE_ADD(NOW(), INTERVAL 9 HOUR)),
(2,  2, 'Organic Chemistry Model Kit',
     'Full molecular model set for Orgo I & II. All atoms and bonds present. Great for visual learners.',
    'https://picsum.photos/seed/listing-2/800/600',
     'educational-items', 1500, DATE_ADD(NOW(), INTERVAL 16 HOUR)),
(3,  3, 'Campus Lab Notebook Set',
     'Pack of 5 quad-ruled lab notebooks, unused. Required format for CHEM and PHYS labs.',
    'https://picsum.photos/seed/listing-3/800/600',
     'educational-items', 800, DATE_ADD(NOW(), INTERVAL 21 HOUR)),
(4,  1, 'Data Structures Textbook Bundle',
     'Includes "Introduction to Algorithms" (CLRS) 4th ed. and "Data Structures in Java". Some highlighting.',
    'https://picsum.photos/seed/listing-4/800/600',
     'educational-items', 3500, DATE_ADD(NOW(), INTERVAL 6 HOUR)),
(5,  4, 'University Crest Hoodie',
     'Official maroon hoodie, size L. Worn twice — too big for me. Tags still on hood.',
    'https://picsum.photos/seed/listing-5/800/600',
     'university-merch', 2000, DATE_ADD(NOW(), INTERVAL 12 HOUR)),
(6,  2, 'Alumni Stadium Scarf',
     'Limited-run game-day scarf from the 2025 homecoming. Still in packaging.',
    'https://picsum.photos/seed/listing-6/800/600',
     'university-merch', 1000, DATE_ADD(NOW(), INTERVAL 19 HOUR)),
(7,  3, 'Campus Spirit Water Bottle',
     '32 oz insulated bottle with university logo. Keeps drinks cold 24 hrs. No dents.',
    'https://picsum.photos/seed/listing-7/800/600',
     'university-merch', 800, DATE_ADD(NOW(), INTERVAL 30 HOUR)),
(8,  1, 'Limited Edition Mascot Cap',
     'Snap-back cap with embroidered mascot. Only 200 made for the spring rally.',
    'https://picsum.photos/seed/listing-8/800/600',
     'university-merch', 1200, DATE_ADD(NOW(), INTERVAL 14 HOUR)),
(9,  4, 'Compact Dorm Air Fryer',
     'Cosori 2-quart air fryer, perfect for dorm cooking. Used one semester. Includes recipe booklet.',
    'https://picsum.photos/seed/listing-9/800/600',
     'dorm-essentials', 3000, DATE_ADD(NOW(), INTERVAL 10 HOUR)),
(10, 2, 'Under-Bed Storage Trio',
     'Set of 3 rolling under-bed bins with lids. Clear plastic, great condition. Saves closet space.',
    'https://picsum.photos/seed/listing-10/800/600',
     'dorm-essentials', 1500, DATE_ADD(NOW(), INTERVAL 28 HOUR)),
(11, 3, 'Desk Lamp with USB Ports',
     'LED desk lamp with adjustable brightness, built-in USB-A and USB-C charging. Clamp mount.',
    'https://picsum.photos/seed/listing-11/800/600',
     'dorm-essentials', 1200, DATE_ADD(NOW(), INTERVAL 17 HOUR)),
(12, 1, 'Noise-Low Study Fan',
     'Honeywell HT-900 turbo fan. Whisper-quiet on low setting. Ideal for dorm white noise.',
    'https://picsum.photos/seed/listing-12/800/600',
     'dorm-essentials', 1000, DATE_ADD(NOW(), INTERVAL 22 HOUR)),
(13, 4, 'Mystery Campus Auction Box',
     'Sealed box of campus collectibles and merch. At least $40 retail value guaranteed. Fun surprise!',
    'https://picsum.photos/seed/listing-13/800/600',
     'general-auction', 500, DATE_ADD(NOW(), INTERVAL 8 HOUR)),
(14, 2, 'Vintage Lecture Hall Chair',
     'Salvaged oak lecture chair from the old Science building renovation. Heavy and solid.',
    'https://picsum.photos/seed/listing-14/800/600',
     'general-auction', 4000, DATE_ADD(NOW(), INTERVAL 5 HOUR)),
(15, 3, 'Student Art Showcase Print',
     'Signed 18×24 print from the 2025 BFA showcase. Abstract campus landscape by a graduating senior.',
    'https://picsum.photos/seed/listing-15/800/600',
     'general-auction', 1500, DATE_ADD(NOW(), INTERVAL 27 HOUR)),
(16, 4, 'Retro Bicycle Permit Plaque',
     'Original 1970s campus bicycle permit metal plaque. Unique dorm wall decor.',
    'https://picsum.photos/seed/listing-16/800/600',
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
