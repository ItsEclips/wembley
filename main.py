
from keep_alive import keep_alive

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import random

DATABASE = "bar.db"
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # For slash commands

@bot.event
async def on_ready():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('currency', '💰')")
        await db.commit()

    # กำหนดสถานะ Watching
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")
    
    if bot.guilds:
        guild_name = bot.guilds[0].name
    else:
        guild_name = "this server"

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=guild_name
    ))

async def get_currency() -> str:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT value FROM config WHERE key = 'currency'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "💰"

# ตรวจสอบว่าผู้เล่นมีข้อมูลหรือยัง
async def ensure_user(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

# เริ่มรันบอท
keep_alive()  # ใส่ไว้ก่อน bot.run()
import os
bot.run(os.getenv("DISCORD_TOKEN"))  # ✅ แบบนี้ถูกต้อง
