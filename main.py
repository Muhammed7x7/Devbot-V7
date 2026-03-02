#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEV BOT V7 - ACİL TAMİR
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
OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS', '').split(',') if x.strip()]

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger("Bot")

# =========================
# BOT - DÜZGÜN KURULUM
# =========================
intents = discord.Intents.default()
intents.message_content = True  # MESAJ İÇERİĞİ ÇOK ÖNEMLİ!
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# BASİT KOMUTLAR - HEMEN ÇALIŞIR
# =========================
@bot.command(name="ping")
async def ping(ctx):
    """En basit test komutu"""
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")
    logger.info(f"Ping komutu çalıştı: {ctx.author}")

@bot.command(name="test")
async def test(ctx):
    """Test komutu"""
    await ctx.send("✅ Bot çalışıyor!")
    logger.info(f"Test komutu çalıştı: {ctx.author}")

@bot.command(name="help")
async def help_cmd(ctx):
    """Yardım komutu"""
    await ctx.send("""
📋 **KOMUTLAR:**
`!ping` - Bot test et
`!test` - Çalışıyor mu kontrol et
`!help` - Bu mesaj
    """)

# =========================
# ONAY MESAJI
# =========================
@bot.event
async def on_ready():
    logger.info(f"✅ Bot HAZIR: {bot.user}")
    logger.info(f"🌐 Sunucular: {len(bot.guilds)}")
    logger.info(f"📝 Prefix: !")
    await bot.change_presence(activity=discord.Game("!ping | !help"))

@bot.event
async def on_message(message):
    """Mesaj geldiğinde çalışır"""
    if message.author.bot:
        return
    
    # Prefix komutlarını işle
    if message.content.startswith('!'):
        logger.info(f"Komut alındı: {message.content} from {message.author}")
        await bot.process_commands(message)
    else:
        # Normal mesajları da işle (opsiyonel)
        await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Hata yakalama"""
    logger.error(f"Komut hatası: {error}")
    await ctx.send(f"❌ Hata: {str(error)[:100]}")

# =========================
# HEALTH CHECK
# =========================
async def health_check():
    async def handler(request):
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "bot": str(bot.user) if bot.user else "starting",
                "ready": bot.is_ready()
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
# KEEP ALIVE
# =========================
async def keep_alive():
    while True:
        await asyncio.sleep(60)
        if bot.is_ready():
            logger.info(f"💓 Bot çalışıyor - {len(bot.guilds)} sunucu")

# =========================
# ANA FONKSİYON
# =========================
async def main():
    print("""
╔════════════════════════════════════════╗
║                                        ║
║   DEV BOT V7 - ACİL TAMİR              ║
║                                        ║
║   • Prefix: !                          ║
║   • Test: !ping                        ║
║   • Hata: "command None" ÇÖZÜLDÜ       ║
║                                        ║
╚════════════════════════════════════════╝
    """)
    
    if not TOKEN:
        logger.error("❌ Token yok!")
        return
    
    # Health check başlat
    asyncio.create_task(health_check())
    
    # Keep alive başlat
    asyncio.create_task(keep_alive())
    
    # Bot'u başlat
    try:
        logger.info("🚀 Bot başlatılıyor...")
        await bot.start(TOKEN)
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ INTENT'LER KAPALI! Discord Developer Portal'da aç:")
        logger.error("1. https://discord.com/developers/applications")
        logger.error("2. Bot'unu seç")
        logger.error("3. Bot sekmesi")
        logger.error("4. MESSAGE CONTENT INTENT'i AÇ")
    except Exception as e:
        logger.error(f"❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
