#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEV BOT V7 - RAILWAY ACİL ÇÖZÜM
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
# KONFİG
# =========================
PORT = int(os.getenv("PORT", 8080))
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS', '').split(',') if x.strip()]

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger("Bot")

# =========================
# BASİT BOT - TEST İÇİN
# =========================
class TestBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.start_time = datetime.now()
        self.last_heartbeat = time.time()
        self.ready = False
    
    async def on_ready(self):
        self.ready = True
        self.last_heartbeat = time.time()
        logger.info(f"✅ BAŞARILI! Bot aktif: {self.user}")
        logger.info(f"🌐 Sunucular: {len(self.guilds)}")
        
        await self.change_presence(activity=discord.Game("✅ ÇALIŞIYOR"))
    
    async def on_message(self, message):
        if not message.author.bot:
            self.last_heartbeat = time.time()
        await self.process_commands(message)
    
    async def on_error(self, event, *args, **kwargs):
        logger.error(f"❌ Hata: {event}")

bot = TestBot()

# =========================
# BASİT KOMUT
# =========================
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")
    bot.last_heartbeat = time.time()

# =========================
# HEALTH CHECK
# =========================
async def health_check():
    async def handler(request):
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "ready": bot.ready,
                "uptime": str(datetime.now() - bot.start_time).split('.')[0],
                "heartbeat": f"{time.time() - bot.last_heartbeat:.0f}s"
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
    logger.info(f"✅ Health check: {PORT}")

# =========================
# WATCHDOG - GEÇİCİ DEVRE DIŞI
# =========================
async def watchdog():
    """Şimdilik sadece logla, restart ETME"""
    while True:
        await asyncio.sleep(60)
        if not bot.ready:
            logger.warning(f"⏳ Bot hazır değil... ({int(time.time() - bot.start_time.total_seconds())}s)")
        else:
            logger.info(f"💓 Heartbeat: {int(time.time() - bot.last_heartbeat)}s")

# =========================
# ANA FONKSİYON
# =========================
async def main():
    print("""
╔════════════════════════════════════════╗
║                                        ║
║   DEV BOT V7 - ACİL TEST               ║
║                                        ║
║   • Watchdog GEÇİCİ devre dışı         ║
║   • Sadece log tutar                    ║
║   • RESTART YOK                         ║
║                                        ║
╚════════════════════════════════════════╝
    """)
    
    if not TOKEN:
        logger.error("❌ Token yok!")
        return
    
    # Health check başlat
    asyncio.create_task(health_check())
    
    # Watchdog başlat (log için)
    asyncio.create_task(watchdog())
    
    # Bot'u başlat
    try:
        logger.info("🚀 Bot başlatılıyor...")
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logger.error("❌ TOKEN GEÇERSİZ!")
    except Exception as e:
        logger.error(f"❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
