#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
██████╗ ███████╗██╗   ██╗██████╗  ██████╗ ████████╗
██╔══██╗██╔════╝██║   ██║██╔══██╗██╔═══██╗╚══██╔══╝
██║  ██║█████╗  ██║   ██║██████╔╝██║   ██║   ██║   
██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██║   ██║   ██║   
██████╔╝███████╗ ╚████╔╝ ██████╔╝╚██████╔╝   ██║   
╚═════╝ ╚══════╝  ╚═══╝  ╚═════╝  ╚═══╝    ╚═╝   

███████╗██╗  ██╗██████╗ ███████╗██████╗ ██╗███████╗███╗   ██╗ ██████╗███████╗
██╔════╝██║  ██║██╔══██╗██╔════╝██╔══██╗██║██╔════╝████╗  ██║██╔════╝██╔════╝
███████╗███████║██████╔╝█████╗  ██████╔╝██║█████╗  ██╔██╗ ██║██║     █████╗  
╚════██║██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗██║██╔══╝  ██║╚██╗██║██║     ██╔══╝  
███████║██║  ██║██║     ███████╗██║  ██║██║███████╗██║ ╚████║╚██████╗███████╗
╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝

═══════════════════════════════════════════════════════════════════════════════
                    🚀  GELİŞTİRİCİ SÜRÜMÜ v7.0  🚀
═══════════════════════════════════════════════════════════════════════════════
    • ALTIN ORAN ile tasarlandı (1:1.618)
    • DALL-E 3 + GPT-4 ENTEGRE
    • Railway + Health Check + Watchdog
    • ekincimhuseyn
═══════════════════════════════════════════════════════════════════════════════
"""

# ======================================================================
# 📦 1. İTHALATLAR
# ======================================================================
import os
import sys
import asyncio
import logging
import json
import time
import signal
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from discord import Embed, File

from openai import OpenAI
from aiohttp import web

# ======================================================================
# ⚙️ 2. RAILWAY KONFİGÜRASYONU
# ======================================================================
RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT") is not None
PORT = int(os.getenv("PORT", 8080))
BASE_DIR = "/tmp" if RAILWAY_ENV else "."

# ======================================================================
# 🔧 3. KONFİGÜRASYON SINIFI
# ======================================================================
class Config:
    def __init__(self):
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS', '').split(',') if x.strip()]
        
        self.WORKSPACE_DIR = Path(BASE_DIR) / "workspace"
        self.DATA_DIR = Path(BASE_DIR) / "data"
        self.LOGS_DIR = Path(BASE_DIR) / "logs"
        
        for dir_path in [self.WORKSPACE_DIR, self.DATA_DIR, self.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.CHAT_MODEL = "gpt-4o-mini"
        self.CODE_MODEL = "gpt-4-turbo"
        self.IMAGE_MODEL = "dall-e-3"
        self.HEALTH_CHECK_INTERVAL = 60
        self.NETWORK_TOLERANCE = 10

config = Config()

# ======================================================================
# 📊 4. LOGGING SİSTEMİ
# ======================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / "bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DevBot")

# ======================================================================
# 📁 5. VERİ YÖNETİCİSİ
# ======================================================================
class DataManager:
    def __init__(self):
        self.stats_file = config.DATA_DIR / "stats.json"
        self.memory_file = config.DATA_DIR / "memory.json"
        self.stats = self._load_json(self.stats_file, self._default_stats())
        self.memory = self._load_json(self.memory_file, {})
    
    def _default_stats(self) -> dict:
        return {
            "start_time": datetime.now().isoformat(),
            "restarts": 0,
            "commands": {},
            "images": 0,
            "chats": 0,
            "codes": 0,
            "network_issues": 0
        }
    
    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return default
    
    def _save_json(self, path: Path, data: Any):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def track_command(self, command: str):
        self.stats["commands"][command] = self.stats["commands"].get(command, 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def track_metric(self, metric: str):
        self.stats[metric] = self.stats.get(metric, 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def add_to_memory(self, user_id: int, role: str, content: str):
        uid = str(user_id)
        if uid not in self.memory:
            self.memory[uid] = []
        self.memory[uid].append({
            "role": role,
            "content": content,
            "time": time.time()
        })
        if len(self.memory[uid]) > 50:
            self.memory[uid] = self.memory[uid][-50:]
        self._save_json(self.memory_file, self.memory)
    
    def get_memory(self, user_id: int) -> list:
        return self.memory.get(str(user_id), [])
    
    def clear_memory(self, user_id: int):
        self.memory[str(user_id)] = []
        self._save_json(self.memory_file, self.memory)

db = DataManager()

# ======================================================================
# 🤖 6. OPENAI İSTEMCİSİ
# ======================================================================
class OpenAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.image_history = []
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info("✅ OpenAI bağlantısı kuruldu")
            except Exception as e:
                logger.error(f"❌ OpenAI hatası: {e}")
    
    async def chat(self, message: str) -> str:
        if not self.client:
            return "OpenAI API anahtarı gerekli!"
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=[{"role": "user", "content": message}],
                    max_tokens=2000
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Hata: {str(e)}"
    
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        if not self.client:
            return "# API anahtarı gerekli"
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=config.CODE_MODEL,
                    messages=[
                        {"role": "system", "content": f"Sen bir {language} uzmanı. Sadece kod üret."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"# Hata: {str(e)}"
    
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> dict:
        if not self.client:
            raise Exception("OpenAI API anahtarı gerekli!")
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.images.generate(
                    model=config.IMAGE_MODEL,
                    prompt=prompt,
                    size=size,
                    quality="standard",
                    n=1
                )
            )
            result = {
                "url": response.data[0].url,
                "prompt": prompt,
                "size": size,
                "created": datetime.now().isoformat()
            }
            self.image_history.append(result)
            if len(self.image_history) > 20:
                self.image_history = self.image_history[-20:]
            return result
        except Exception as e:
            raise Exception(f"DALL-E hatası: {str(e)}")
    
    def get_recent_images(self, limit: int = 5) -> list:
        return self.image_history[-limit:]

ai = OpenAIClient(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

# ======================================================================
# 🤖 7. DİSCORD BOT
# ======================================================================
class DevBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
        self.start_time = datetime.now()
        self.ai = ai
        self.owner_ids = config.OWNER_IDS
        self.last_heartbeat = time.time()
        self.network_issues = 0
    
    async def setup_hook(self):
        await self.tree.sync()
        logger.info(f"✅ {len(self.tree.get_commands())} komut yüklendi")
    
    async def on_ready(self):
        self.last_heartbeat = time.time()
        logger.info(f"✅ Bot hazır: {self.user}")
        logger.info(f"🌐 Sunucular: {len(self.guilds)}")
        await self.change_presence(activity=discord.Game("🎨 /image | 💬 /chat"))
    
    async def on_message(self, message):
        if message.author.bot:
            return
        self.last_heartbeat = time.time()
        await self.process_commands(message)
    
    def is_owner(self, user_id: int) -> bool:
        return user_id in self.owner_ids

bot = DevBot()

# ======================================================================
# 🎨 8. UI BİLEŞENLERİ
# ======================================================================
class ImageModal(Modal, title="🎨 Görsel Oluştur"):
    prompt = TextInput(label="Ne görmek istersin?", style=discord.TextStyle.paragraph, required=True)
    size = TextInput(label="Boyut", placeholder="1024x1024", default="1024x1024", required=False)
    
    async def on_submit(self, interaction: discord.Interaction):
        await image_command(interaction, self.prompt.value, self.size.value)

class ChatModal(Modal, title="💬 Sohbet"):
    message = TextInput(label="Mesajınız", style=discord.TextStyle.paragraph, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        await chat_command(interaction, self.message.value)

# ======================================================================
# 🎯 9. KOMUTLAR
# ======================================================================
@bot.tree.command(name="image", description="🎨 Görsel oluştur")
async def image_command(interaction: discord.Interaction, prompt: str, size: str = "1024x1024"):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        result = await bot.ai.generate_image(prompt, size)
        db.track_command("image")
        
        embed = Embed(title="🖼️ DALL-E 3", description=f"**Prompt:** {prompt}", color=0x5865F2)
        embed.set_image(url=result["url"])
        
        view = View()
        view.add_item(Button(label="📥 İndir", url=result["url"]))
        
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="chat", description="💬 Sohbet et")
async def chat_command(interaction: discord.Interaction, message: str):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        response = await bot.ai.chat(message)
        db.track_command("chat")
        db.add_to_memory(interaction.user.id, "user", message)
        db.add_to_memory(interaction.user.id, "assistant", response)
        
        embed = Embed(title="💬 Sohbet", color=0x57F287)
        embed.add_field(name="📤 Siz", value=f"```{message[:500]}```", inline=False)
        embed.add_field(name="📥 AI", value=f"```{response[:1500]}```", inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="code", description="💻 Kod oluştur")
async def code_command(interaction: discord.Interaction, prompt: str, language: str = "python"):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        code = await bot.ai.generate_code(prompt, language)
        db.track_command("code")
        
        filename = f"code_{int(time.time())}.{language}"
        filepath = config.WORKSPACE_DIR / filename
        filepath.write_text(code)
        
        if len(code) < 1000:
            await interaction.followup.send(f"```{language}\n{code}\n```")
        else:
            await interaction.followup.send(file=File(filepath))
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}")

@bot.tree.command(name="menu", description="📋 Ana menü")
async def menu_command(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    embed = Embed(title="📋 Ana Menü", color=0x5865F2)
    embed.add_field(name="🎨 /image", value="Görsel oluştur", inline=False)
    embed.add_field(name="💬 /chat", value="Sohbet et", inline=False)
    embed.add_field(name="💻 /code", value="Kod oluştur", inline=False)
    embed.add_field(name="📊 /status", value="Bot durumu", inline=False)
    
    view = View()
    view.add_item(Button(label="🎨 Görsel", custom_id="menu_image"))
    view.add_item(Button(label="💬 Sohbet", custom_id="menu_chat"))
    view.add_item(Button(label="📊 Durum", custom_id="menu_status"))
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="status", description="📊 Bot durumu")
async def status_command(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    uptime = datetime.now() - bot.start_time
    hours = int(uptime.total_seconds() / 3600)
    minutes = int((uptime.total_seconds() % 3600) / 60)
    
    embed = Embed(title="📊 Bot Durumu", color=0x5865F2)
    embed.add_field(name="⏰ Çalışma", value=f"{hours}s {minutes}d", inline=True)
    embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Ağ Sorunu", value=bot.network_issues, inline=True)
    
    await interaction.response.send_message(embed=embed)

# ======================================================================
# 🎨 10. BUTON İŞLEYİCİLERİ
# ======================================================================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        
        if not bot.is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        
        if custom_id == "menu_image":
            await interaction.response.send_modal(ImageModal())
        elif custom_id == "menu_chat":
            await interaction.response.send_modal(ChatModal())
        elif custom_id == "menu_status":
            await status_command(interaction)

# ======================================================================
# 🏥 11. HEALTH CHECK SERVER
# ======================================================================
async def health_check():
    """Railway health check server - HER ZAMAN 200 döndürür"""
    
    async def handler(request):
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "time": datetime.now().isoformat(),
                "bot_ready": bot.is_ready() if bot else False
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
    
    logger.info(f"✅ Health check aktif: 0.0.0.0:{PORT}")
    return runner

# ======================================================================
# 👀 12. WATCHDOG
# ======================================================================
async def watchdog():
    """Bot sağlığını izle"""
    while True:
        await asyncio.sleep(config.HEALTH_CHECK_INTERVAL)
        
        try:
            heartbeat_age = time.time() - bot.last_heartbeat
            
            if heartbeat_age > 900:  # 15 dakika
                logger.warning(f"⚠️ Heartbeat yaşlı: {heartbeat_age:.0f}s")
                bot.network_issues += 1
                db.track_metric("network_issues")
                
                if bot.network_issues >= config.NETWORK_TOLERANCE * 2:
                    logger.critical("❌ Çok fazla ağ sorunu - restart")
                    os._exit(1)
            else:
                bot.network_issues = max(0, bot.network_issues - 1)
                
        except Exception as e:
            logger.error(f"❌ Watchdog hatası: {e}")

# ======================================================================
# 🚀 13. ANA FONKSİYON - DÜZGÜN VERSİYON
# ======================================================================
async def main():
    """Ana fonksiyon - Tüm task'leri başlat"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   DEV BOT V7 - RAILWAY EDITION                              ║
║   Huseyin.ekinci - Ekincimhuseyn                            ║
║                                                              ║
║                               ║
║                                        ║
║   ✅ Bot is working                                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Token kontrolü
    if not config.DISCORD_TOKEN:
        logger.error("❌ DISCORD_TOKEN bulunamadı!")
        return
    
    # Health check server'ını başlat
    asyncio.create_task(health_check())
    logger.info("✅ Health check başlatıldı")
    
    # Watchdog'u başlat
    asyncio.create_task(watchdog())
    logger.info("✅ Watchdog başlatıldı")
    
    # Bot'u başlat
    logger.info("🚀 Bot başlatılıyor...")
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ INTENT'LER KAPALI! Discord Developer Portal'da aç:")
        logger.error("   • PRESENCE INTENT")
        logger.error("   • SERVER MEMBERS INTENT")
        logger.error("   • MESSAGE CONTENT INTENT")
    except Exception as e:
        logger.error(f"❌ Bot hatası: {e}")
    finally:
        # Bot durursa 5 saniye bekle ve yeniden dene
        logger.warning("⚠️ Bot durdu, 5 saniye sonra yeniden başlatılıyor...")
        await asyncio.sleep(5)
        await main()

# ======================================================================
# 🏁 14. PROGRAM BAŞLANGICI
# ======================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Kapatıldı")
    except Exception as e:
        logger.error(f"💥 Kritik hata: {e}")
        time.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)  # Yeniden başlat
