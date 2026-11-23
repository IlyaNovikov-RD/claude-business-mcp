"""Create business.db with sample data (fictional coffee-roaster shop)."""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).with_name("business.db")

SCHEMA = """
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT DEFAULT ''
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    order_date TEXT NOT NULL
);
"""

CUSTOMERS = [
    ("Dana Levi", "dana@example.com", "Tel Aviv"),
    ("Mark Cohen", "mark@example.com", "Haifa"),
    ("Sarah Klein", "sarah@example.com", "Jerusalem"),
    ("Tom Becker", "tom@example.com", "Berlin"),
    ("Anna Petrova", "anna@example.com", "London"),
    ("Yossi Mizrahi", "yossi@example.com", "Ariel"),
]
PRODUCTS = {"Espresso Beans 1kg": 32.0, "Filter Roast 500g": 18.0, "Cold Brew Pack": 24.0, "Gift Box": 55.0}


def main(seed: int = 7) -> None:
    rnd = random.Random(seed)
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO customers (name, email, city) VALUES (?, ?, ?)", CUSTOMERS)
    today = date.today()
    for _ in range(60):
        cid = rnd.randint(1, len(CUSTOMERS) - 1)  # last customer stays inactive on purpose
        product, price = rnd.choice(list(PRODUCTS.items()))
        d = today - timedelta(days=rnd.randint(1, 180))
        conn.execute("INSERT INTO orders (customer_id, product, quantity, unit_price, order_date) VALUES (?, ?, ?, ?, ?)",
                     (cid, product, rnd.randint(1, 5), price, d.isoformat()))
    conn.commit()
    conn.close()
    print(f"Seeded {DB}")


if __name__ == "__main__":
    main()
