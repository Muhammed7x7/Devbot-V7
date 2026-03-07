#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
from datetime import datetime
import requests
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================================
# Load env
# ================================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",")]

# ================================
# Direktories
# ================================
BASE_DIR = "./data"
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
os.makedirs(BASE_DIR, exist_ok=True)

# ================================
# Memory yönetimi
# ================================
if os.path.exists(MEMORY_FILE):
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

# ================================
# DeepSeek Chat
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

def is_owner(user_id):
    return user_id in OWNER_IDS

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
    # memory ekle
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
# Bot Run
# ================================
bot.run(DISCORD_TOKEN)
