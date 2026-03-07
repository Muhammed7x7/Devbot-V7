#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path

import requests
import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
from dotenv import load_dotenv

# ================================
# Load env
# ================================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]
PORT = int(os.getenv("PORT", 8080))

# ================================
# Direktories
# ================================
BASE_DIR = Path("./data")
MEMORY_FILE = BASE_DIR / "memory.json"
BASE_DIR.mkdir(exist_ok=True, parents=True)

# ================================
# Memory yönetimi
# ================================
if MEMORY_FILE.exists():
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = {}

def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def add_to_memory(user_id, role, content):
    uid = str(user_id)
    if uid not in memory:
        memory[uid] = []
    memory[uid].append({"role": role, "content": content, "time": time.time()})
    if len(memory[uid]) > 50:
        memory[uid] = memory[uid][-50:]
    save_memory()

def get_memory(user_id):
    return memory.get(str(user_id), [])

def is_owner(user_id):
    return user_id in OWNER_IDS

# ================================
# DeepSeek API
# ================================
def deepseek_chat(message):
    url = "https://api.deepseek.ai/v1/chat"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": message}]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ DeepSeek error: {str(e)}"

# ================================
# Discord Bot
# ================================
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot hazır: {bot.user}")
    print(f"🌐 Sunucular: {len(bot.guilds)}")
    # Slash komutları senkronizasyonu
    try:
        await bot.tree.sync()
        print(f"✅ Slash komutları yüklendi")
    except Exception as e:
        print(f"❌ Slash sync hatası: {e}")

# ----------------
# Ping komutu
# ----------------
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

# ----------------
# Chat komutu
# ----------------
@bot.command(name="chat")
async def chat(ctx, *, mesaj: str):
    if not is_owner(ctx.author.id):
        await ctx.send("❌ Yetkiniz yok!")
        return
    await ctx.typing()
    add_to_memory(ctx.author.id, "user", mesaj)
    response = deepseek_chat(mesaj)
    add_to_memory(ctx.author.id, "assistant", response)
    if len(response) > 1900:
        for i in range(0, len(response), 1900):
            await ctx.send(response[i:i+1900])
    else:
        await ctx.send(response)

# ----------------
# Memory temizleme
# ----------------
@bot.command(name="clear")
async def clear_memory(ctx):
    if not is_owner(ctx.author.id):
        await ctx.send("❌ Yetkiniz yok!")
        return
    memory[str(ctx.author.id)] = []
    save_memory()
    await ctx.send("✅ Memory temizlendi!")

# ================================
# Healthcheck server (Railway uyumlu)
# ================================
async def health_check():
    async def handler(request):
        return web.json_response({
            "status": "alive",
            "time": datetime.now().isoformat(),
            "bot_ready": bot.is_ready(),
            "guilds": len(bot.guilds),
        })
    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_get("/health", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Health check aktif: 0.0.0.0:{PORT}")

# ================================
# Watchdog (network kontrol)
# ================================
async def watchdog():
    while True:
        await asyncio.sleep(60)
        heartbeat_age = time.time() - bot.latency
        if heartbeat_age > 900:
            print(f"⚠️ Heartbeat yaşlı: {heartbeat_age:.0f}s")
            os._exit(1)

# ================================
# Ana fonksiyon
# ================================
async def main():
    asyncio.create_task(health_check())
    asyncio.create_task(watchdog())
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
