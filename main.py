
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

@bot.event
async def on_member_join(member):
    async with aiosqlite.connect("bar.db") as db:
        async with db.execute("SELECT channel_id, title, description, color FROM welcome_settings WHERE guild_id = ?", (member.guild.id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return
            channel_id, title, desc, color = row

    channel = member.guild.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            title=title,
            description=desc.replace("{user}", member.mention).replace("{server}", member.guild.name),
            color=color
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"ตอนนี้มี {member.guild.member_count} คนแล้ว!")

        await channel.send(embed=embed)

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

# /setwelcome
@tree.command(name="setwelcome", description="ตั้งค่าข้อความต้อนรับ (เฉพาะแอดมิน)")
@app_commands.describe(
    channel="ช่องที่จะใช้ต้อนรับ",
    title="หัวข้อข้อความ Embed",
    description="รายละเอียดใน Embed",
    color="สี Embed (ตัวเลขฐาน 10 หรือ HEX เช่น 0xffcc00)"
)
async def setwelcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    description: str,
    color: str = "0x3498db"  # สีฟ้าอ่อนเริ่มต้น
):
    # จำกัดสิทธิ์เฉพาะแอดมิน
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    color_int = int(color, 16) if color.startswith("0x") else int(color)

    async with aiosqlite.connect("bar.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                title TEXT,
                description TEXT,
                color INTEGER
            )
        """)
        await db.execute("""
            INSERT INTO welcome_settings (guild_id, channel_id, title, description, color)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id=excluded.channel_id,
                title=excluded.title,
                description=excluded.description,
                color=excluded.color
        """, (interaction.guild.id, channel.id, title, description, color_int))
        await db.commit()

    await interaction.response.send_message(f"✅ ตั้งค่าข้อความต้อนรับเรียบร้อยแล้วในช่อง {channel.mention}", ephemeral=True)
# /addemoji
@tree.command(name="addemoji", description="เพิ่มอีโมจิลงในเซิร์ฟเวอร์")
@app_commands.describe(name="ชื่อของอีโมจิ", image="ไฟล์อีโมจิ (PNG/GIF)")
async def addemoji(interaction: discord.Interaction, name: str, image: discord.Attachment):
    # ตรวจสอบ permission
    if not interaction.user.guild_permissions.manage_emojis_and_stickers:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์เพิ่มอีโมจิ", ephemeral=True)
        return

    # ดาวน์โหลดไฟล์
    file_bytes = await image.read()
    
    # สร้างอีโมจิ
    try:
        emoji = await interaction.guild.create_custom_emoji(name=name, image=file_bytes)
        await interaction.response.send_message(
            f"✅ เพิ่มอีโมจิเรียบร้อย: `<:{emoji.name}:{emoji.id}>`", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ ล้มเหลว: {e}", ephemeral=True)

# เริ่มรันบอท
keep_alive()  # ใส่ไว้ก่อน bot.run()
import os
bot.run(os.getenv("DISCORD_TOKEN"))  # ✅ แบบนี้ถูกต้อง
