#!/usr/bin/env python3
"""
DEV BOT V7 - RAILWAY KESİN ÇÖZÜM (SON VERSİYON)
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
# BOT
# =========================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.start_time = datetime.now()
        self.ready = False
    
    async def on_ready(self):
        self.ready = True
        logger.info(f"✅ BAŞARILI! Bot aktif: {self.user}")
        await self.change_presence(activity=discord.Game("🚀 ÇALIŞIYOR"))
    
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

bot = MyBot()

# =========================
# KOMUT
# =========================
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# =========================
# HEALTH CHECK
# =========================
async def health_check():
    async def handler(request):
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "time": datetime.now().isoformat(),
                "ready": bot.ready
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
# KEEP ALIVE TASK
# =========================
async def keep_alive():
    """Bot'un sonsuza kadar çalışmasını sağla"""
    while True:
        await asyncio.sleep(60)
        logger.info(f"💓 Bot çalışıyor... (Uptime: {datetime.now() - bot.start_time})")

# =========================
# ANA FONKSİYON - DOĞRU YAPI
# =========================
async def main():
    print("""
╔════════════════════════════════════════╗
║                                        ║
║   DEV BOT V7 - KESİN ÇÖZÜM             ║
║                                        ║
║   • Health check AKTİF                  ║
║   • Keep-alive task AKTİF               ║
║   • Railway ASLA DURMAZ                 ║
║                                        ║
╚════════════════════════════════════════╝
    """)
    
    if not TOKEN:
        logger.error("❌ Token yok!")
        return
    
    # Health check başlat
    asyncio.create_task(health_check())
    
    # Keep-alive task başlat (ÇOK ÖNEMLİ!)
    asyncio.create_task(keep_alive())
    
    # Bot'u başlat ve sonsuza kadar bekle
    try:
        await bot.start(TOKEN)
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ INTENT'LER KAPALI! Discord Developer Portal'da aç!")
    except Exception as e:
        logger.error(f"❌ Hata: {e}")
    finally:
        # Bot durursa hemen yeniden başlat
        logger.warning("⚠️ Bot durdu, 5 saniye sonra yeniden başlatılıyor...")
        await asyncio.sleep(5)
        await main()

# =========================
# BAŞLAT
# =========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Kapatıldı")
    except Exception as e:
        logger.error(f"💥 Kritik hata: {e}")
        time.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)  # Yeniden başlat
