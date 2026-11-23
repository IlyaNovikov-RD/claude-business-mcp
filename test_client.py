"""End-to-end test: launch the server over stdio like Claude Desktop does, call every tool."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).parent


def text(result) -> str:
    return "\n".join(c.text for c in result.content if hasattr(c, "text"))


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")])
    failures = 0
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            print("TOOLS:", tools)

            async def call(name, args, expect_error=False):
                nonlocal failures
                res = await s.call_tool(name, args)
                is_error = bool(getattr(res, "is_error", getattr(res, "isError", False)))
                ok = is_error == expect_error
                failures += not ok
                print(f"\n[{'PASS' if ok else 'FAIL'}] {name}({json.dumps(args)})\n{text(res)[:600]}")
                return res

            await call("list_tables", {})
            await call("sales_summary", {"group_by": "product"})
            await call("inactive_customers", {"days": 60})
            await call("add_customer", {"name": "Noa Barak", "email": "noa@example.com", "city": "Netanya"})
            await call("add_order", {"customer_email": "noa@example.com", "product": "Gift Box",
                                     "quantity": 2, "unit_price": 55})
            await call("run_query", {"sql": "SELECT name, city FROM customers WHERE city = 'Netanya'"})
            # safety checks: these must be rejected
            await call("run_query", {"sql": "DELETE FROM orders"}, expect_error=True)
            await call("run_query", {"sql": "SELECT 1; DROP TABLE orders"}, expect_error=True)
            await call("add_order", {"customer_email": "ghost@example.com", "product": "X",
                                     "quantity": 1, "unit_price": 1}, expect_error=True)
    print(f"\n{'ALL PASSED' if failures == 0 else f'{failures} FAILED'}")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
