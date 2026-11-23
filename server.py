"""
Business Data MCP Server
------------------------
Lets Claude (Claude Desktop, Claude Code, or any MCP client) work with a
small business's orders and customers in plain language:

  "Which customers haven't ordered in 60 days?"
  "Add an order for Dana Levi: 3 x Espresso Beans"
  "Summarize revenue by month"

Backed by SQLite so it runs anywhere with zero setup. Swapping SQLite for
Postgres, Google Sheets, Airtable or a CRM API only changes the db layer.

Run:   python server.py            (stdio transport, for Claude Desktop / Code)
"""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # MCP Python SDK 1.x
    from mcp.server.fastmcp import FastMCP as Server
    from mcp.server.fastmcp.exceptions import ToolError

DB_PATH = Path(os.environ.get("BUSINESS_DB", Path(__file__).with_name("business.db")))

mcp = Server("business-data")


# ---------- db layer ----------

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


READ_ONLY = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace)\b", re.IGNORECASE)


# ---------- tools ----------

@mcp.tool()
def list_tables() -> dict:
    """List the tables in the business database with their columns."""
    with connect() as conn:
        names = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {n: [c["name"] for c in conn.execute(f"PRAGMA table_info({n})")] for n in names}


@mcp.tool()
def run_query(sql: str, limit: int = 100) -> list[dict]:
    """Run a READ-ONLY SQL query (SELECT / WITH) and return the rows.
    Write operations are rejected; use the dedicated add_* tools instead."""
    if not READ_ONLY.match(sql) or FORBIDDEN.search(sql):
        raise ToolError("Only read-only SELECT/WITH queries are allowed.")
    limit = max(1, min(int(limit), 1000))
    with connect() as conn:
        conn.execute("PRAGMA query_only = ON")
        return rows(conn.execute(f"SELECT * FROM ({sql.rstrip(';')}) LIMIT {limit}"))


@mcp.tool()
def add_customer(name: str, email: str, city: str = "") -> dict:
    """Add a new customer. Returns the created customer."""
    if "@" not in email:
        raise ToolError("Invalid email address.")
    with connect() as conn:
        cur = conn.execute("INSERT INTO customers (name, email, city) VALUES (?, ?, ?)",
                           (name.strip(), email.strip().lower(), city.strip()))
        return dict(conn.execute("SELECT * FROM customers WHERE id = ?", (cur.lastrowid,)).fetchone())


@mcp.tool()
def add_order(customer_email: str, product: str, quantity: int, unit_price: float,
              order_date: str | None = None) -> dict:
    """Record an order for an existing customer (looked up by email).
    order_date is YYYY-MM-DD; defaults to today."""
    if quantity <= 0 or unit_price < 0:
        raise ToolError("Quantity must be positive and price non-negative.")
    d = order_date or date.today().isoformat()
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        raise ToolError("order_date must be in YYYY-MM-DD format.")
    with connect() as conn:
        c = conn.execute("SELECT id FROM customers WHERE email = ?",
                         (customer_email.strip().lower(),)).fetchone()
        if c is None:
            raise ToolError(f"No customer with email {customer_email}. Add them first.")
        cur = conn.execute(
            "INSERT INTO orders (customer_id, product, quantity, unit_price, order_date) VALUES (?, ?, ?, ?, ?)",
            (c["id"], product.strip(), quantity, unit_price, d))
        return dict(conn.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone())


@mcp.tool()
def sales_summary(group_by: str = "month") -> list[dict]:
    """Revenue summary grouped by 'month', 'product' or 'customer'."""
    key = {
        "month": "substr(o.order_date, 1, 7)",
        "product": "o.product",
        "customer": "c.name",
    }.get(group_by)
    if key is None:
        raise ToolError("group_by must be 'month', 'product' or 'customer'.")
    with connect() as conn:
        return rows(conn.execute(f"""
            SELECT {key} AS {group_by},
                   COUNT(*) AS orders,
                   ROUND(SUM(o.quantity * o.unit_price), 2) AS revenue
            FROM orders o JOIN customers c ON c.id = o.customer_id
            GROUP BY 1 ORDER BY {'1' if group_by == 'month' else 'revenue DESC'}"""))


@mcp.tool()
def inactive_customers(days: int = 60) -> list[dict]:
    """Customers whose last order is older than `days` days (or who never ordered)."""
    with connect() as conn:
        return rows(conn.execute("""
            SELECT c.name, c.email, c.city, MAX(o.order_date) AS last_order
            FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
            GROUP BY c.id
            HAVING last_order IS NULL OR julianday('now') - julianday(last_order) > ?
            ORDER BY last_order""", (days,)))


if __name__ == "__main__":
    mcp.run()
