# Business Data MCP Server

Connect Claude to your business data and work with it in plain language.

> "Which customers haven't ordered in 60 days?"
> "Add an order for dana@example.com: 3 × Espresso Beans at $32"
> "Show revenue by month"

Built on the official [Model Context Protocol](https://modelcontextprotocol.io) Python SDK (works with SDK 1.x and 2.x).
The sample data is a fictional coffee shop in SQLite; in client projects the same server talks to
Postgres, Google Sheets, Airtable, or a CRM API.

## Tools

| Tool | What it does |
|---|---|
| `list_tables` | Shows the tables and columns Claude can work with |
| `run_query` | Read-only SQL (SELECT/WITH). Writes are blocked twice: by a statement check and by SQLite `query_only` mode |
| `add_customer` | Adds a customer with validation |
| `add_order` | Records an order for an existing customer |
| `sales_summary` | Revenue by month, product or customer |
| `inactive_customers` | Customers with no order in N days, for win-back campaigns |

Writes only happen through the dedicated, validated tools, never through free-form SQL.

## Run it

```bash
pip install mcp
python seed.py          # creates business.db with sample data
python test_client.py   # end-to-end test over stdio, the same way Claude Desktop connects
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "business-data": {
      "command": "python",
      "args": ["/full/path/to/server.py"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add business-data -- python /full/path/to/server.py
```

Set `BUSINESS_DB=/path/to/your.db` to point it at a different database.
