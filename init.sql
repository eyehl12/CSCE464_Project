DROP DATABASE IF EXISTS campusbid;
CREATE DATABASE campusbid;
USE campusbid;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category ENUM('educational-items', 'university-merch', 'dorm-essentials', 'general-auction') NOT NULL,
    price_cents INT NOT NULL,
    rating DECIMAL(2,1) NOT NULL DEFAULT 4.5,
    reviews INT NOT NULL DEFAULT 0,
    bid_count INT NOT NULL DEFAULT 0,
    time_left_hours INT NOT NULL DEFAULT 24,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE carts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guest_key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cart_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_cart_product (cart_id, product_id),
    CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

INSERT INTO products (name, category, price_cents, rating, reviews, bid_count, time_left_hours) VALUES
('Engineering Calculator Pro', 'educational-items', 4599, 4.8, 122, 14, 9),
('Organic Chemistry Model Kit', 'educational-items', 3299, 4.6, 88, 9, 16),
('Campus Lab Notebook Set', 'educational-items', 1899, 4.7, 63, 7, 21),
('Data Structures Textbook Bundle', 'educational-items', 6799, 4.9, 147, 18, 6),
('University Crest Hoodie', 'university-merch', 5499, 4.8, 204, 25, 12),
('Alumni Stadium Scarf', 'university-merch', 2499, 4.5, 71, 11, 19),
('Campus Spirit Water Bottle', 'university-merch', 1999, 4.6, 95, 8, 30),
('Limited Edition Mascot Cap', 'university-merch', 2799, 4.7, 83, 10, 14),
('Compact Dorm Air Fryer', 'dorm-essentials', 7499, 4.8, 165, 19, 10),
('Under-Bed Storage Trio', 'dorm-essentials', 3899, 4.4, 52, 5, 28),
('Desk Lamp with USB Ports', 'dorm-essentials', 3199, 4.7, 109, 12, 17),
('Noise-Low Study Fan', 'dorm-essentials', 2699, 4.5, 76, 6, 22),
('Mystery Campus Auction Box', 'general-auction', 1599, 4.3, 41, 16, 8),
('Vintage Lecture Hall Chair', 'general-auction', 8999, 4.6, 33, 13, 5),
('Student Art Showcase Print', 'general-auction', 3499, 4.9, 58, 9, 27),
('Retro Bicycle Permit Plaque', 'general-auction', 2299, 4.4, 24, 4, 36);
