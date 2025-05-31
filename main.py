
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

# ตรวจสอบว่าผู้เล่นมีข้อมูลหรือยัง
async def ensure_user(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

# /balance
@tree.command(name="balance", description="ดูจำนวน ChillCoin ของคุณ")
async def balance(interaction: discord.Interaction):
    await ensure_user(interaction.user.id)
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (interaction.user.id,)) as cursor:
            row = await cursor.fetchone()
            await interaction.response.send_message(f"💰 {interaction.user.display_name} มี {row[0]} ChillCoin", ephemeral=True)

# /work
@tree.command(name="work", description="ทำงานในบาร์เพื่อหาเงิน ChillCoin")
async def work(interaction: discord.Interaction):
    await ensure_user(interaction.user.id)
    earned = random.randint(15, 25)
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (earned, interaction.user.id))
        await db.commit()
    await interaction.response.send_message(f"🍹 คุณทำงานเป็น Bartender และได้ {earned} ChillCoin!")

# /daily
@tree.command(name="daily", description="รับ ChillCoin ฟรีวันละครั้ง")
async def daily(interaction: discord.Interaction):
    await ensure_user(interaction.user.id)
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT last_daily FROM users WHERE user_id = ?", (interaction.user.id,)) as cursor:
            row = await cursor.fetchone()
            now = datetime.utcnow()
            if row[0] is not None:
                last_claimed = datetime.fromisoformat(row[0])
                if now - last_claimed < timedelta(hours=24):
                    next_time = last_claimed + timedelta(hours=24)
                    remain = next_time - now
                    await interaction.response.send_message(
                        f"⏳ รับ daily ได้อีกใน {remain.seconds // 3600} ชม.", ephemeral=True)
                    return
        await db.execute("UPDATE users SET balance = balance + 100, last_daily = ? WHERE user_id = ?",
                         (now.isoformat(), interaction.user.id))
        await db.commit()
    await interaction.response.send_message("🎁 คุณได้รับ 100 ChillCoin จากโบนัสประจำวัน!")

# เริ่มรันบอท
keep_alive()  # ใส่ไว้ก่อน bot.run()
import os
bot.run(os.getenv("DISCORD_TOKEN"))  # ✅ แบบนี้ถูกต้อง
