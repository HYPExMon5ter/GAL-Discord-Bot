# gal_discord_bot/persistence.py

import os
import json
from gal_discord_bot.config import DATABASE_URL

PERSIST_FILE = "persisted_views.json"

if DATABASE_URL:
    import psycopg2
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persisted_views (
            key TEXT PRIMARY KEY,
            data JSONB
        );
    """)
    conn.commit()

    def load_persisted():
        cursor.execute("SELECT data FROM persisted_views WHERE key = %s", ("default",))
        row = cursor.fetchone()
        return row[0] if row else {}

    def save_persisted(data):
        cursor.execute(
            "INSERT INTO persisted_views (key, data) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data",
            ("default", json.dumps(data))
        )
        conn.commit()
else:
    # Local fallback: JSON file
    def load_persisted():
        try:
            with open(PERSIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_persisted(data):
        with open(PERSIST_FILE, "w") as f:
            json.dump(data, f, indent=2)

persisted = load_persisted()

def set_persisted_msg(guild_id, key, msg_id):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid][key] = msg_id
    save_persisted(persisted)

def get_persisted_msg(guild_id, key):
    return persisted.get(str(guild_id), {}).get(key)

def get_event_mode_for_guild(guild_id):
    gid = str(guild_id)
    return persisted.get(gid, {}).get("event_mode", "normal")

def set_event_mode_for_guild(guild_id, mode):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid]["event_mode"] = mode
    save_persisted(persisted)

def get_schedule(guild_id, key):
    data = persisted.get(str(guild_id), {})
    return data.get(f"{key}_schedule")

def set_schedule(guild_id, key, dtstr):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid][f"{key}_schedule"] = dtstr
    save_persisted(persisted)