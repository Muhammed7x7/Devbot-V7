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
                    🚀  GEMINI ENTEGRE - ÜCRETSİZ!  🚀
═══════════════════════════════════════════════════════════════════════════════
    • Prefix komutlar: !ping, !test, !help, !chat, !image, !code
    • Slash komutlar: /image, /chat, /code, /status, /menu
    • Gemini AI: 60 istek/dakika ÜCRETSİZ!
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
from typing import Optional, Dict, List, Any, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from discord import Embed, File

# Gemini için yeni kütüphane
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai kütüphanesi yok! pip install google-generativeai")

# OpenAI hala opsiyonel (görsel için)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", ""))  # Önce Gemini, yoksa OpenAI
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Görsel için
        self.OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS', '').split(',') if x.strip()]
        
        self.WORKSPACE_DIR = Path(BASE_DIR) / "workspace"
        self.DATA_DIR = Path(BASE_DIR) / "data"
        self.LOGS_DIR = Path(BASE_DIR) / "logs"
        
        for dir_path in [self.WORKSPACE_DIR, self.DATA_DIR, self.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Model ayarları
        self.GEMINI_MODEL = "gemini-1.5-flash"  # Hızlı model (ücretsiz)
        self.GEMINI_PRO_MODEL = "gemini-1.5-pro"  # Güçlü model
        self.OPENAI_CHAT_MODEL = "gpt-4o-mini"
        self.OPENAI_CODE_MODEL = "gpt-4-turbo"
        self.OPENAI_IMAGE_MODEL = "dall-e-3"
        
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
            "gemini_calls": 0,
            "openai_calls": 0,
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

# ======================================================================
# 🤖 6. GEMINI İSTEMCİSİ - DOĞRUDAN REST API
# ======================================================================
class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.available = False
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"  # /v1beta/ ile!
        
        if api_key:
            try:
                # Sadece API key'i test et
                import requests
                test_url = f"{self.base_url}/models/gemini-pro:generateContent?key={api_key}"
                test_data = {
                    "contents": [{
                        "parts": [{"text": "Merhaba"}]
                    }]
                }
                
                response = requests.post(test_url, json=test_data, timeout=5)
                if response.status_code == 200:
                    self.available = True
                    print(f"✅ Gemini API hazır: {self.base_url}")
                else:
                    print(f"⚠️ Gemini test başarısız: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Gemini bağlantı hatası: {e}")
    
    async def chat(self, message: str, user_id: int = None) -> str:
        """Gemini ile sohbet et - doğrudan REST API"""
        if not self.available:
            return "⚠️ Gemini API bağlantısı yok!"
        
        try:
            import requests
            url = f"{self.base_url}/models/gemini-pro:generateContent?key={self.api_key}"
            
            data = {
                "contents": [{
                    "parts": [{"text": message}]
                }]
            }
            
            # Async olarak çalıştır
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"API Hatası: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Bağlantı hatası: {str(e)}"
    
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Kod üret"""
        if not self.available:
            return "# API bağlantısı yok!"
        
        try:
            import requests
            url = f"{self.base_url}/models/gemini-pro:generateContent?key={self.api_key}"
            
            full_prompt = f"Write {language} code for: {prompt}. Only output code, no explanations."
            
            data = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }]
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                result = response.json()
                code = result['candidates'][0]['content']['parts'][0]['text']
                
                # Markdown temizliği
                if code.startswith("```"):
                    lines = code.split('\n')
                    if len(lines) > 2:
                        code = '\n'.join(lines[1:-1])
                return code
            else:
                return f"# Hata: {response.status_code}"
                
        except Exception as e:
            return f"# Hata: {str(e)}"

# ======================================================================
# 🎨 7. OPENAI İSTEMCİSİ (SADECE GÖRSEL İÇİN)
# ======================================================================
class OpenAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.image_history = []
        self.available = False
        
        if api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=api_key)
                self.available = True
                logger.info("✅ OpenAI bağlantısı kuruldu (görsel için)")
            except Exception as e:
                logger.error(f"❌ OpenAI hatası: {e}")
    
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> dict:
        """Sadece görsel üret - DALL-E 3"""
        if not self.available:
            raise Exception("OpenAI API anahtarı gerekli! Görsel üretilemiyor.")
        
        try:
            # Boyut kontrolü
            valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
            if size not in valid_sizes:
                size = "1024x1024"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.images.generate(
                    model="dall-e-3",
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
                "created": datetime.now().isoformat(),
                "revised_prompt": getattr(response.data[0], 'revised_prompt', prompt)
            }
            
            self.image_history.append(result)
            if len(self.image_history) > 20:
                self.image_history = self.image_history[-20:]
            
            db.track_metric("openai_calls")
            return result
            
        except Exception as e:
            raise Exception(f"DALL-E hatası: {str(e)}")
    
    def get_recent_images(self, limit: int = 5) -> list:
        return self.image_history[-limit:]

# ======================================================================
# 🤖 8. DİSCORD BOT - TÜM İNTENT'LER AÇIK
# ======================================================================
class DevBot(commands.Bot):
    def __init__(self):
        # TÜM İNTENT'LERİ AÇ
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
        self.start_time = datetime.now()
        
        # Gemini (ana AI)
        self.gemini = GeminiClient(config.GEMINI_API_KEY)
        
        # OpenAI (sadece görsel için)
        self.openai = OpenAIClient(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
        
        # AI seçimi (öncelik Gemini)
        self.ai = self.gemini if self.gemini.available else None
        
        self.owner_ids = config.OWNER_IDS
        self.last_heartbeat = time.time()
        self.network_issues = 0
        
        logger.info(f"🤖 AI Durumu: Gemini={'✅' if self.gemini.available else '❌'}, OpenAI={'✅' if self.openai else '❌'}")
    
    async def setup_hook(self):
        # Slash komutlarını senkronize et
        try:
            await self.tree.sync()
            logger.info(f"✅ {len(self.tree.get_commands())} slash komut yüklendi")
            for cmd in self.tree.get_commands():
                logger.info(f"   • /{cmd.name}")
        except Exception as e:
            logger.error(f"❌ Slash komut senkronizasyon hatası: {e}")
    
    async def on_ready(self):
        self.last_heartbeat = time.time()
        logger.info(f"✅ Bot HAZIR: {self.user}")
        logger.info(f"🌐 Sunucular: {len(self.guilds)}")
        logger.info(f"📝 Prefix: ! (Örnek: !ping, !test, !chat, !image, !code)")
        logger.info(f"⚡ Slash: / (Örnek: /image, /chat, /code, /status, /menu)")
        
        if self.gemini.available:
            logger.info(f"🤖 Gemini AKTİF - 60 istek/dakika ÜCRETSİZ!")
        
        await self.change_presence(
            activity=discord.Game("!ping | Gemini AI ✨"),
            status=discord.Status.online
        )
    
    async def on_message(self, message):
        if message.author.bot:
            return
        
        self.last_heartbeat = time.time()
        
        if message.content.startswith('!'):
            logger.info(f"📨 Komut alındı: {message.content} from {message.author}")
            await self.process_commands(message)
        else:
            await self.process_commands(message)
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"⚠️ Komut bulunamadı: {ctx.message.content}")
            await ctx.send(f"❌ Komut bulunamadı: `{ctx.message.content}`\n📝 Mevcut komutlar: `!ping`, `!test`, `!help`, `!chat`, `!image`, `!code`")
        else:
            logger.error(f"❌ Komut hatası: {error}")
            await ctx.send(f"❌ Hata: {str(error)[:100]}")
    
    def is_owner(self, user_id: int) -> bool:
        return user_id in self.owner_ids

bot = DevBot()

# ======================================================================
# 🎯 9. PREFIX KOMUTLAR
# ======================================================================

@bot.command(name="ping")
async def ping(ctx):
    """!ping - Bot test et"""
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")
    logger.info(f"✅ Ping komutu çalıştı: {ctx.author}")

@bot.command(name="test")
async def test(ctx):
    """!test - Bot çalışıyor mu?"""
    ai_status = "Gemini ✅" if bot.gemini.available else "Gemini ❌"
    openai_status = "OpenAI ✅" if bot.openai else "OpenAI ❌"
    await ctx.send(f"✅ Bot çalışıyor!\n🤖 {ai_status}\n🎨 {openai_status}")
    logger.info(f"✅ Test komutu çalıştı: {ctx.author}")

@bot.command(name="help")
async def help_command(ctx):
    """!help - Yardım menüsü"""
    embed = Embed(
        title="📋 Bot Komutları",
        description="Prefix: `!`  |  Slash: `/`\n🤖 Gemini AI: 60 istek/dk ÜCRETSİZ!",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📝 Prefix Komutlar",
        value="`!ping` - Bot test et\n`!test` - Durum göster\n`!help` - Bu mesaj\n`!chat <mesaj>` - Sohbet et\n`!image <prompt>` - Görsel oluştur\n`!code <dil> <prompt>` - Kod oluştur\n`!analyze <dil> <kod>` - Kodu analiz et",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Slash Komutlar",
        value="`/image` - Görsel oluştur\n`/chat` - Sohbet et\n`/code` - Kod oluştur\n`/status` - Bot durumu\n`/menu` - Ana menü",
        inline=False
    )
    
    embed.set_footer(text=f"{bot.user.name} • Gemini AI ✨")
    
    await ctx.send(embed=embed)

@bot.command(name="chat")
async def prefix_chat(ctx, *, mesaj: str):
    """!chat <mesaj> - Gemini ile sohbet et"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    async with ctx.typing():
        try:
            if not bot.gemini.available:
                await ctx.send("❌ Gemini API bağlantısı yok! Lütfen GEMINI_API_KEY ekleyin.")
                return
            
            response = await bot.gemini.chat(mesaj, ctx.author.id)
            db.track_command("chat")
            db.add_to_memory(ctx.author.id, "user", mesaj)
            db.add_to_memory(ctx.author.id, "assistant", response)
            
            if len(response) > 1900:
                for i in range(0, len(response), 1900):
                    await ctx.send(response[i:i+1900])
            else:
                await ctx.send(response)
                
            logger.info(f"✅ Chat komutu çalıştı: {ctx.author}")
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name="image")
async def prefix_image(ctx, *, prompt: str):
    """!image <prompt> - Görsel oluştur (DALL-E 3)"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    async with ctx.typing():
        try:
            if not bot.openai:
                await ctx.send("❌ OpenAI API anahtarı yok! Görsel üretilemiyor.")
                return
            
            await ctx.send(f"🎨 Görsel oluşturuluyor: *{prompt[:50]}...*")
            
            result = await bot.openai.generate_image(prompt)
            db.track_command("image")
            
            embed = Embed(
                title="🖼️ DALL-E 3",
                description=f"**Prompt:** {prompt}",
                color=0x5865F2,
                timestamp=datetime.now()
            )
            embed.set_image(url=result["url"])
            embed.add_field(name="📐 Boyut", value=result["size"], inline=True)
            
            if result.get("revised_prompt") and result["revised_prompt"] != prompt:
                embed.add_field(name="📝 Düzeltilmiş", value=result["revised_prompt"][:100], inline=False)
            
            await ctx.send(embed=embed)
            logger.info(f"✅ Image komutu çalıştı: {ctx.author}")
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name="code")
async def prefix_code(ctx, language: str = "python", *, prompt: str):
    """!code <dil> <prompt> - Kod oluştur"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    async with ctx.typing():
        try:
            if not bot.gemini.available:
                await ctx.send("❌ Gemini API bağlantısı yok!")
                return
            
            code = await bot.gemini.generate_code(prompt, language)
            db.track_command("code")
            
            filename = f"code_{int(time.time())}.{language}"
            filepath = config.WORKSPACE_DIR / filename
            filepath.write_text(code, encoding='utf-8')
            
            if len(code) < 1000:
                await ctx.send(f"```{language}\n{code}\n```")
            else:
                await ctx.send(file=File(filepath))
                
            logger.info(f"✅ Code komutu çalıştı: {ctx.author}")
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name="analyze")
async def prefix_analyze(ctx, language: str = "python", *, code: str):
    """!analyze <dil> <kod> - Kodu analiz et"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    async with ctx.typing():
        try:
            if not bot.gemini.available:
                await ctx.send("❌ Gemini API bağlantısı yok!")
                return
            
            analysis = await bot.gemini.analyze_code(code, language)
            db.track_command("analyze")
            
            if len(analysis) > 1900:
                for i in range(0, len(analysis), 1900):
                    await ctx.send(analysis[i:i+1900])
            else:
                await ctx.send(analysis)
                
            logger.info(f"✅ Analyze komutu çalıştı: {ctx.author}")
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

# ======================================================================
# 🎨 10. UI BİLEŞENLERİ
# ======================================================================
class ImageModal(Modal, title="🎨 Görsel Oluştur (DALL-E 3)"):
    prompt = TextInput(
        label="Ne görmek istersin?",
        style=discord.TextStyle.paragraph,
        placeholder="Örnek: Uzaylı bir kedi, neon ışıklar, fantastik manzara...",
        required=True,
        max_length=1000
    )
    size = TextInput(
        label="Boyut (1024x1024 / 1792x1024 / 1024x1792)",
        placeholder="1024x1024",
        default="1024x1024",
        required=False,
        max_length=11
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await image_command(interaction, self.prompt.value, self.size.value)

class ChatModal(Modal, title="💬 Gemini ile Sohbet"):
    message = TextInput(
        label="Mesajınız",
        style=discord.TextStyle.paragraph,
        placeholder="Ne sormak istersin?",
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await chat_command(interaction, self.message.value)

class CodeModal(Modal, title="💻 Kod Oluştur (Gemini)"):
    prompt = TextInput(
        label="Ne yapmak istiyorsun?",
        style=discord.TextStyle.paragraph,
        placeholder="Örnek: Bir web sunucusu, hesap makinesi, oyun...",
        required=True,
        max_length=1000
    )
    language = TextInput(
        label="Programlama dili",
        placeholder="python",
        default="python",
        required=False,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await code_command(interaction, self.prompt.value, self.language.value)

# ======================================================================
# 🎯 11. SLASH KOMUTLAR
# ======================================================================

@bot.tree.command(name="image", description="🎨 Görsel oluştur (DALL-E 3)")
@app_commands.describe(prompt="Ne görmek istersin?", size="Boyut (1024x1024, 1792x1024, 1024x1792)")
async def image_command(interaction: discord.Interaction, prompt: str, size: str = "1024x1024"):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        if not bot.openai:
            await interaction.followup.send("❌ OpenAI API anahtarı yok! Görsel üretilemiyor.")
            return
        
        result = await bot.openai.generate_image(prompt, size)
        db.track_command("image")
        
        embed = Embed(
            title="🖼️ DALL-E 3",
            description=f"**Prompt:** {prompt}",
            color=0x5865F2,
            timestamp=datetime.now()
        )
        embed.set_image(url=result["url"])
        embed.add_field(name="📐 Boyut", value=result["size"], inline=True)
        
        if result.get("revised_prompt") and result["revised_prompt"] != prompt:
            embed.add_field(name="📝 Düzeltilmiş", value=result["revised_prompt"][:100], inline=False)
        
        view = View()
        view.add_item(Button(label="📥 İndir", url=result["url"]))
        
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="chat", description="💬 Gemini ile sohbet et (ücretsiz!)")
@app_commands.describe(message="Mesajınız")
async def chat_command(interaction: discord.Interaction, message: str):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        if not bot.gemini.available:
            await interaction.followup.send("❌ Gemini API bağlantısı yok! Lütfen GEMINI_API_KEY ekleyin.")
            return
        
        response = await bot.gemini.chat(message, interaction.user.id)
        db.track_command("chat")
        db.add_to_memory(interaction.user.id, "user", message)
        db.add_to_memory(interaction.user.id, "assistant", response)
        
        embed = Embed(
            title="💬 Gemini Sohbet",
            description=f"**60 istek/dakika ÜCRETSİZ!**",
            color=0x4285F4  # Google mavisi
        )
        embed.add_field(name="📤 Siz", value=f"```{message[:500]}```", inline=False)
        embed.add_field(name="📥 Gemini", value=f"```{response[:1500]}```", inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="code", description="💻 Kod oluştur (Gemini)")
@app_commands.describe(prompt="Ne yapmak istiyorsun?", language="Programlama dili")
async def code_command(interaction: discord.Interaction, prompt: str, language: str = "python"):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    await interaction.response.defer()
    
    try:
        if not bot.gemini.available:
            await interaction.followup.send("❌ Gemini API bağlantısı yok!")
            return
        
        code = await bot.gemini.generate_code(prompt, language)
        db.track_command("code")
        
        filename = f"code_{int(time.time())}.{language}"
        filepath = config.WORKSPACE_DIR / filename
        filepath.write_text(code, encoding='utf-8')
        
        embed = Embed(
            title="💻 Kod Oluşturuldu",
            description=f"Dil: {language}",
            color=0x4285F4
        )
        embed.add_field(name="📏 Uzunluk", value=f"{len(code)} karakter", inline=True)
        
        if len(code) < 1000:
            embed.add_field(name="📝 Kod", value=f"```{language}\n{code[:500]}\n```", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            embed.add_field(name="📁 Dosya", value=f"`{filename}`", inline=True)
            await interaction.followup.send(embed=embed, file=File(filepath))
            
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="status", description="📊 Bot durumu")
async def status_command(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    uptime = datetime.now() - bot.start_time
    hours = int(uptime.total_seconds() / 3600)
    minutes = int((uptime.total_seconds() % 3600) / 60)
    
    embed = Embed(title="📊 Bot Durumu", color=0x4285F4)
    embed.add_field(name="⏰ Çalışma", value=f"{hours}s {minutes}d", inline=True)
    embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Sunucular", value=len(bot.guilds), inline=True)
    embed.add_field(name="🤖 Gemini", value="✅ Aktif" if bot.gemini.available else "❌ Pasif", inline=True)
    embed.add_field(name="🎨 OpenAI", value="✅ Aktif" if bot.openai else "❌ Pasif", inline=True)
    embed.add_field(name="📊 İstatistik", value=f"Sohbet: {db.stats.get('chats', 0)}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="menu", description="📋 Ana menü")
async def menu_command(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    
    embed = Embed(
        title="📋 Ana Menü",
        description="Gemini AI ile güçlendirilmiş bot",
        color=0x4285F4
    )
    
    embed.add_field(name="🎨 /image", value="Görsel oluştur (DALL-E 3)", inline=False)
    embed.add_field(name="💬 /chat", value="Sohbet et (Gemini - ÜCRETSİZ!)", inline=False)
    embed.add_field(name="💻 /code", value="Kod oluştur (Gemini)", inline=False)
    embed.add_field(name="📊 /status", value="Bot durumu", inline=False)
    
    view = View()
    view.add_item(Button(label="🎨 Görsel", style=discord.ButtonStyle.primary, custom_id="menu_image"))
    view.add_item(Button(label="💬 Sohbet", style=discord.ButtonStyle.success, custom_id="menu_chat"))
    view.add_item(Button(label="💻 Kod", style=discord.ButtonStyle.secondary, custom_id="menu_code"))
    view.add_item(Button(label="📊 Durum", style=discord.ButtonStyle.danger, custom_id="menu_status"))
    
    await interaction.response.send_message(embed=embed, view=view)

# ======================================================================
# 🎨 12. BUTON İŞLEYİCİLERİ
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
        elif custom_id == "menu_code":
            await interaction.response.send_modal(CodeModal())
        elif custom_id == "menu_status":
            await status_command(interaction)

# ======================================================================
# 🏥 13. HEALTH CHECK SERVER
# ======================================================================
async def health_check():
    """Railway health check server - HER ZAMAN 200 döndürür"""
    
    async def handler(request):
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "time": datetime.now().isoformat(),
                "bot_ready": bot.is_ready(),
                "bot_user": str(bot.user) if bot.user else None,
                "guilds": len(bot.guilds) if bot.guilds else 0,
                "gemini": bot.gemini.available,
                "openai": bot.openai is not None
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
# 👀 14. WATCHDOG
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
# 🚀 15. ANA FONKSİYON
# ======================================================================
async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   DEV BOT V7 - GEMINI ENTEGRE                                ║
║   ✨ 60 İSTEK/DAKİKA ÜCRETSİZ!                               ║
║                                                              ║
║   ✅ Prefix: !ping, !test, !help, !chat, !image, !code      ║
║   ✅ Slash: /image, /chat, /code, /status, /menu            ║
║   ✅ Gemini AI: 60 istek/dk ÜCRETSİZ!                       ║
║   ✅ DALL-E 3: Görsel üretimi                               ║
║   ✅ Health check: HER ZAMAN 200                            ║
║   ✅ Watchdog: AKTİF                                        ║
║   ✅ ekincimhuseyn                                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if not config.DISCORD_TOKEN:
        logger.error("❌ DISCORD_TOKEN bulunamadı!")
        return
    
    if not config.GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY bulunamadı! Sohbet ve kod özellikleri çalışmaz.")
    
    if not config.OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY bulunamadı! Görsel üretimi çalışmaz.")
    
    asyncio.create_task(health_check())
    logger.info("✅ Health check başlatıldı")
    
    asyncio.create_task(watchdog())
    logger.info("✅ Watchdog başlatıldı")
    
    logger.info("🚀 Bot başlatılıyor...")
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ INTENT'LER KAPALI! Discord Developer Portal'da aç:")
        logger.error("   1. https://discord.com/developers/applications")
        logger.error("   2. Bot'unu seç → Bot sekmesi")
        logger.error("   3. Aşağı kaydır → Tüm Intent'leri AÇ")
        logger.error("   4. Save Changes")
    except Exception as e:
        logger.error(f"❌ Bot hatası: {e}")
    finally:
        logger.warning("⚠️ Bot durdu, 5 saniye sonra yeniden başlatılıyor...")
        await asyncio.sleep(5)
        await main()

# ======================================================================
# 🏁 16. PROGRAM BAŞLANGICI
# ======================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Kapatıldı")
    except Exception as e:
        logger.error(f"💥 Kritik hata: {e}")
        time.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)
