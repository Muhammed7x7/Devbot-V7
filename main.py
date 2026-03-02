#!/usr/bin/env python3
"""
DEV BOT V7 - RAILWAY KESİN ÇÖZÜM
"""

import os
import sys
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
from aiohttp import web

# =========================
# RAILWAY KONFİG
# =========================
PORT = int(os.getenv("PORT", 8080))
TOKEN = os.getenv("DISCORD_TOKEN")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger("Bot")

# =========================
# BOT - TÜM INTENT'LER AÇIK
# =========================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True    # Mesaj içeriği için
        intents.members = True             # Üye bilgileri için
        intents.presences = True           # Durum bilgileri için
        
        super().__init__(command_prefix="!", intents=intents)
        self.start_time = datetime.now()
        self.ready = False
    
    async def on_ready(self):
        self.ready = True
        logger.info(f"✅ BAŞARILI! Bot aktif: {self.user}")
        await self.change_presence(activity=discord.Game("✅ ÇALIŞIYOR"))

bot = MyBot()

# =========================
# BASİT KOMUT
# =========================
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# =========================
# HEALTH CHECK - KESİN ÇÖZÜM
# =========================
# ÖNEMLİ: Her zaman 200 döndür, asla 503 verme!
async def health_check():
    async def handler(request):
        # NE OLURSA OLSUN 200 DÖNDÜR!
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "time": datetime.now().isoformat()
            }),
            status=200,
            content_type="application/json"
        )
    
    app = web.Application()
    app.router.add_get("/", handler)
    app.router.add_get("/health", handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"✅ Health check: {PORT} (HER ZAMAN 200)")

# =========================
# ANA FONKSİYON - BASİT
# =========================
async def main():
    print("""
╔════════════════════════════════════════╗
║                                        ║
║   DEV BOT V7 - KESİN ÇÖZÜM             ║
║                                        ║
║   • Health check HER ZAMAN 200         ║
║   • Intent'ler AÇIK                     ║
║   • Railway ASLA DURDURMAZ              ║
║                                        ║
╚════════════════════════════════════════╝
    """)
    
    if not TOKEN:
        logger.error("❌ Token yok!")
        return
    
    # Health check başlat
    asyncio.create_task(health_check())
    
    # Bot'u başlat
    try:
        await bot.start(TOKEN)
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ INTENT'LER KAPALI! Discord Developer Portal'da aç!")
    except Exception as e:
        logger.error(f"❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
