#!/usr/bin/env python3
"""
create_db.py

Creates an SQLite database with tables:
 - users
 - items
 - transaction_history

UUIDs are stored as TEXT. Booleans are stored as INTEGER (0/1).
"""

import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path("mydb.sqlite3")

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

BEGIN;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    card_id TEXT PRIMARY KEY,          -- students cards is as text
    name TEXT NOT NULL DEFAULT '',
    balance INTEGER NOT NULL DEFAULT 0, -- stored in ore
    active INTEGER NOT NULL DEFAULT 1  -- boolean (0/1)
);

-- Items table
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,          -- UUID stored as text
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    barcode_id TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

-- Transaction history
CREATE TABLE IF NOT EXISTS transaction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- bigint/autoinc
    user_card_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    time TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(user_card_id) REFERENCES users(card_id) ON DELETE CASCADE,
    FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE RESTRICT
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_transaction_history_user ON transaction_history(user_card_id);
CREATE INDEX IF NOT EXISTS idx_transaction_history_item ON transaction_history(item_id);

COMMIT;
"""

SAMPLE_DATA = True


def create_db(path: Path):
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA)
        conn.commit()

        if SAMPLE_DATA:
            # sample uuid for item
            i1 = str(uuid.uuid4())

            # insert sample data
            # Insert sample user and item
            cur.execute(
                "INSERT OR IGNORE INTO users (card_id, name, balance, active) VALUES (?, ?, ?, ?);",
                ("1234567890", "alice", 500, 1)
            )
            cur.execute(
                "INSERT OR IGNORE INTO items (id, name, price, barcode_id, active) VALUES (?, ?, ?, ?, ?);",
                (i1, "apple", 100, "000001", 1)
            )
            conn.commit()  # commit first so FK can see these rows

            # Insert transaction referencing the above rows
            cur.execute(
                "INSERT INTO transaction_history (user_card_id, item_id, time) VALUES (?, ?, datetime('now'));",
                ("1234567890", i1)
            )
            conn.commit()


            print("Sample user card_id: 1234567890")
            print("Sample item id:", i1)

    finally:
        conn.close()

if __name__ == "__main__":
    create_db(DB_PATH)
    print(f"Database created at: {DB_PATH.resolve()}")
