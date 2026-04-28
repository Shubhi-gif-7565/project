-- ============================================================
--  SANSKAR – AI-Based Age-Adaptive Child Learning Platform
--  Database Schema (MySQL 8+)
-- ============================================================

CREATE DATABASE IF NOT EXISTS sanskar_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sanskar_db;

-- ─────────────────────────────────────────────────────────────
-- 1. USERS
-- ─────────────────────────────────────────────────────────────
CREATE TABLE users (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    age           INT           NOT NULL CHECK (age BETWEEN 2 AND 14),
    email         VARCHAR(150)  UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,          -- BCrypt hash
    parent_pin    VARCHAR(255)  NOT NULL,           -- BCrypt-hashed 4-digit PIN
    age_group     ENUM('2-4','5-7','8-10','11-14') NOT NULL,
    avatar_url    VARCHAR(500),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active     BOOLEAN DEFAULT TRUE
);

-- ─────────────────────────────────────────────────────────────
-- 2. CONTENT CATEGORIES
-- ─────────────────────────────────────────────────────────────
CREATE TABLE categories (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    icon_emoji  VARCHAR(10),
    color_hex   VARCHAR(7),
    min_age     INT NOT NULL,
    max_age     INT NOT NULL,
    description TEXT
);

INSERT INTO categories (name, icon_emoji, color_hex, min_age, max_age, description) VALUES
('Alphabets & Numbers', '🔤', '#FF6B6B', 2,  7,  'Learn A-Z and 1-100 with fun animations'),
('Animals & Nature',   '🦁', '#4ECDC4', 2,  14, 'Discover amazing creatures and nature'),
('Basic Science',      '🔬', '#45B7D1', 5,  14, 'Fun experiments and science concepts'),
('Stories & Tales',    '📚', '#FFA07A', 2,  10, 'Engaging moral stories and fairy tales'),
('Mind Games',         '🧩', '#98D8C8', 5,  14, 'Puzzles and brain teasers'),
('Safety Awareness',   '🛡️', '#F7DC6F', 2,  14, 'Good touch/bad touch, stranger safety'),
('Music & Rhymes',     '🎵', '#BB8FCE', 2,  8,  'Nursery rhymes and songs'),
('Math & Logic',       '➕', '#82E0AA', 6,  14, 'Fun math concepts and logic problems'),
('Art & Creativity',   '🎨', '#F1948A', 3,  14, 'Drawing, coloring, and crafts'),
('Emergency Skills',   '🚨', '#AED6F1', 5,  14, 'What to do in emergencies');

-- ─────────────────────────────────────────────────────────────
-- 3. CURATED YOUTUBE CHANNELS (safe, educational)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE curated_channels (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    channel_id  VARCHAR(100) NOT NULL UNIQUE,  -- YouTube channel ID
    name        VARCHAR(200) NOT NULL,
    min_age     INT NOT NULL,
    max_age     INT NOT NULL,
    category_id BIGINT,
    is_active   BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

INSERT INTO curated_channels (channel_id, name, min_age, max_age) VALUES
('UCddiUEpeqJcYeBxX1IVBKvQ', 'Cocomelon - Nursery Rhymes',  2,  6),
('UCbCmjCuTUZos6Inko4u57EA', 'ChuChu TV Nursery Rhymes',    2,  6),
('UCnUYZLuoy1rq1aVMwx4aTzw', 'National Geographic Kids',    6, 14),
('UC295-Dw4tzbMmF-lMtl1AoQ', 'Crash Course Kids',           8, 14),
('UCYO_jab_esuFRV4b17AJtAg', '3Blue1Brown',                11, 14),
('UC7_gcs09iThXybpVgjHZ_7g', 'PBS Space Time',             11, 14),
('UCHnyfMqiRRG1u-2MsSQLbXA', 'Veritasium',                  9, 14),
('UCZYTClx2T1of7BRZ86-8fow', 'SciShow Kids',                6, 12),
('UCi_-vXcleAGNL8zGONqoJIA', 'Kids Learning Tube',          3,  9),
('UCsooa4yRKGN_zEE8iknghZA', 'TED-Ed',                      9, 14);

-- ─────────────────────────────────────────────────────────────
-- 4. VIDEO CACHE (fetched from YouTube API)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE videos (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    youtube_id    VARCHAR(20)  NOT NULL UNIQUE,
    title         VARCHAR(500) NOT NULL,
    description   TEXT,
    thumbnail_url VARCHAR(500),
    channel_id    VARCHAR(100),
    channel_name  VARCHAR(200),
    duration      VARCHAR(20),
    view_count    BIGINT DEFAULT 0,
    category_id   BIGINT,
    min_age       INT DEFAULT 2,
    max_age       INT DEFAULT 14,
    tags          TEXT,           -- comma-separated
    is_approved   BOOLEAN DEFAULT TRUE,
    fetched_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- ─────────────────────────────────────────────────────────────
-- 5. VIDEO WATCH HISTORY
-- ─────────────────────────────────────────────────────────────
CREATE TABLE video_history (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT NOT NULL,
    video_id     BIGINT NOT NULL,
    youtube_id   VARCHAR(20) NOT NULL,
    watched_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_seconds INT DEFAULT 0,       -- seconds watched
    completed    BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    INDEX idx_user_watched (user_id, watched_at DESC)
);

-- ─────────────────────────────────────────────────────────────
-- 6. SEARCH HISTORY
-- ─────────────────────────────────────────────────────────────
CREATE TABLE search_history (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    query       VARCHAR(300) NOT NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result_count INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_search (user_id, searched_at DESC)
);

-- ─────────────────────────────────────────────────────────────
-- 7. RECOMMENDATIONS
-- ─────────────────────────────────────────────────────────────
CREATE TABLE recommendations (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT NOT NULL,
    video_id     BIGINT NOT NULL,
    score        FLOAT DEFAULT 0.0,
    reason       VARCHAR(200),   -- 'age_group', 'watch_history', 'search_behavior'
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_video (user_id, video_id)
);

-- ─────────────────────────────────────────────────────────────
-- 8. SAFETY CONTENT (static curated content)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE safety_content (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(300) NOT NULL,
    content     TEXT NOT NULL,
    video_id    BIGINT,
    min_age     INT NOT NULL,
    max_age     INT NOT NULL,
    topic       ENUM('good_bad_touch','stranger_danger','emergency','online_safety','road_safety'),
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- ─────────────────────────────────────────────────────────────
-- 9. JWT REFRESH TOKENS (optional token rotation)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE refresh_tokens (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    token       VARCHAR(500) NOT NULL UNIQUE,
    expires_at  TIMESTAMP NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
