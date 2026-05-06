import sqlite3
conn = sqlite3.connect("mcp_hub.db")
name = "J-Quants Japan Stock Daily Bars API"
rows = conn.execute("SELECT id FROM api_definitions WHERE name=?", (name,)).fetchall()
for (api_id,) in rows:
    conn.execute("DELETE FROM api_endpoints WHERE api_definition_id=?", (api_id,))
    conn.execute("DELETE FROM chatgpt_connections WHERE api_definition_id=?", (api_id,))
    conn.execute("DELETE FROM api_definitions WHERE id=?", (api_id,))
conn.commit()
conn.close()
print(f"Cleared {len(rows)} record(s) for '{name}'")
