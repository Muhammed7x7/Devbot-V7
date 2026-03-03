#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 GEMINI-POWERED DISCORD BOT 🚀                          ║
║                         (RAILWAY EDITION - DEBUG EKLİ)                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Tamamen ÜCRETSİZ Gemini AI                                                ║
║  • 60 istek/dakika - Hiçbir ücret yok!                                      ║
║  • Prefix: !ping, !test, !gemini, !kod, !temizle                            ║
║  • Slash: /gemini, /kod, /durum, /menü                                      ║
║  • Railway + Health Check + Otomatik yeniden başlatma                       ║
║  • Hafıza: Son 50 mesajı hatırlar                                           ║
║  • DEBUG: Environment değişkenleri loglanır                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ======================================================================
# 🔍 DEBUG - ENVIRONMENT KONTROL (EN ÜSTE OLMALI)
# ======================================================================
import os
import sys

print("=" * 60)
print("🔍 RAILWAY ENVIRONMENT DEBUG")
print("=" * 60)

# Tüm environment değişkenlerini listele (güvenlik için token'ları gizle)
for key, value in sorted(os.environ.items()):
    if "TOKEN" in key.upper() or "KEY" in key.upper():
        if value:
            gizli = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
            print(f"✅ {key} = {gizli} (gizli, uzunluk: {len(value)})")
        else:
            print(f"❌ {key} = BOŞ!")
    else:
        print(f"📌 {key} = {value}")

print("=" * 60)

# Gemini API key'ini özel kontrol et
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    print(f"✅ GEMINI_API_KEY bulundu: {gemini_key[:5]}...{gemini_key[-5:]}")
    print(f"📏 Uzunluk: {len(gemini_key)} karakter (39 olmalı)")
    
    # API key formatını kontrol et
    if gemini_key.startswith('AIza'):
        print("✅ API key formatı doğru (AIza ile başlıyor)")
    else:
        print("❌ API key formatı yanlış! AIza ile başlamalı")
else:
    print("❌ GEMINI_API_KEY BULUNAMADI!")
    print("📝 Railway'de Variables sekmesine GEMINI_API_KEY eklemeyi unutma!")

# Discord token kontrolü
discord_token = os.getenv('DISCORD_TOKEN')
if discord_token:
    print(f"✅ DISCORD_TOKEN bulundu: {discord_token[:5]}...{discord_token[-5:]}")
    print(f"📏 Uzunluk: {len(discord_token)} karakter")
else:
    print("❌ DISCORD_TOKEN BULUNAMADI!")

# Owner ID kontrolü
owner_ids = os.getenv('OWNER_IDS')
if owner_ids:
    print(f"✅ OWNER_IDS bulundu: {owner_ids}")
else:
    print("⚠️ OWNER_IDS bulunamadı, sadece ana owner çalışacak")

print("=" * 60)
print("🚀 Bot başlatılıyor...")
print("=" * 60)

# ======================================================================
# 📦 GEREKLİ KÜTÜPHANELER
# ======================================================================
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from discord import Embed, File

import requests
from aiohttp import web

# ======================================================================
# ⚙️ RAILWAY KONFİGÜRASYONU
# ======================================================================
RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT") is not None
PORT = int(os.getenv("PORT", 8080))
BASE_DIR = "/tmp" if RAILWAY_ENV else "."

# ======================================================================
# 🔧 KONFİGÜRASYON
# ======================================================================
class Config:
    def __init__(self):
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
        
        # Owner ID'ler (virgülle ayır: 123456789,987654321)
        owner_ids = os.getenv('OWNER_IDS', '')
        self.OWNER_IDS = [int(x) for x in owner_ids.split(',') if x.strip()]
        
        # Dizinler
        self.WORKSPACE_DIR = Path(BASE_DIR) / "workspace"
        self.DATA_DIR = Path(BASE_DIR) / "data"
        self.LOGS_DIR = Path(BASE_DIR) / "logs"
        
        for dir_path in [self.WORKSPACE_DIR, self.DATA_DIR, self.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Gemini ayarları
        self.GEMINI_MODEL = "gemini-pro"
        self.GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        
        # Sistem ayarları
        self.HEALTH_CHECK_INTERVAL = 60
        self.MEMORY_LIMIT = 50

config = Config()

# ======================================================================
# 📊 LOGLAMA SİSTEMİ
# ======================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / "bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GeminiBot")

# ======================================================================
# 📁 VERİ YÖNETİCİSİ
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
            "gemini_calls": 0,
            "total_users": 0,
            "total_messages": 0
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
        self.stats["total_messages"] = self.stats.get("total_messages", 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def track_gemini(self):
        self.stats["gemini_calls"] = self.stats.get("gemini_calls", 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def add_to_memory(self, user_id: int, role: str, content: str):
        uid = str(user_id)
        if uid not in self.memory:
            self.memory[uid] = []
            self.stats["total_users"] = len(self.memory)
        
        self.memory[uid].append({
            "role": role,
            "content": content,
            "time": time.time()
        })
        
        if len(self.memory[uid]) > config.MEMORY_LIMIT:
            self.memory[uid] = self.memory[uid][-config.MEMORY_LIMIT:]
        
        self._save_json(self.memory_file, self.memory)
        self._save_json(self.stats_file, self.stats)
    
    def get_memory(self, user_id: int) -> list:
        return self.memory.get(str(user_id), [])
    
    def clear_memory(self, user_id: int):
        self.memory[str(user_id)] = []
        self._save_json(self.memory_file, self.memory)

db = DataManager()

# ======================================================================
# 🤖 GEMINI İSTEMCİSİ (DEBUG EKLİ)
# ======================================================================
class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.available = False
        self.model = config.GEMINI_MODEL
        self.api_url = f"{config.GEMINI_API_URL}?key={api_key}"
        
        logger.info("🤖 Gemini istemcisi başlatılıyor...")
        
        if api_key:
            self._test_connection()
        else:
            logger.error("❌ GEMINI_API_KEY boş! Lütfen Railway'de GEMINI_API_KEY değişkenini ekleyin.")
    
    def _test_connection(self):
        """API bağlantısını test et - DETAYLI DEBUG"""
        logger.info("🔄 Gemini API bağlantısı test ediliyor...")
        
        try:
            # API key'in uzunluğunu kontrol et
            logger.info(f"🔑 API Key uzunluğu: {len(self.api_key)} karakter")
            logger.info(f"🔑 API Key formatı: {self.api_key[:5]}...{self.api_key[-5:]}")
            
            # Test mesajı
            test_data = {
                "contents": [{
                    "parts": [{"text": "Merhaba, test mesajı. Sadece 'Evet' yaz."}]
                }]
            }
            
            logger.info(f"📡 API URL: {self.api_url[:50]}...")
            logger.info("📤 Test isteği gönderiliyor...")
            
            response = requests.post(
                self.api_url,
                json=test_data,
                timeout=15,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"📥 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                self.available = True
                logger.info("✅ Gemini API bağlantısı BAŞARILI!")
                logger.info(f"   • Model: {self.model}")
                logger.info(f"   • Limit: 60 istek/dakika (ÜCRETSİZ!)")
                
                # Response'u logla
                try:
                    result = response.json()
                    if 'candidates' in result:
                        logger.info("✅ API yanıt formatı doğru")
                except:
                    pass
                    
            else:
                logger.error(f"❌ Gemini API hatası! Status: {response.status_code}")
                logger.error(f"📄 Response: {response.text[:500]}")
                
                # Hata kodlarına göre özel mesajlar
                if response.status_code == 403:
                    logger.error("🚫 403 Hatası: API key geçersiz veya yetkisiz!")
                    logger.error("   • API key'in doğru olduğundan emin ol")
                    logger.error("   • Yeni bir API key almayı dene")
                elif response.status_code == 429:
                    logger.error("⏳ 429 Hatası: Çok fazla istek! (Rate limit)")
                    logger.error("   • 60 saniye bekle ve tekrar dene")
                elif response.status_code == 400:
                    logger.error("❌ 400 Hatası: İstek formatı yanlış")
                
        except requests.exceptions.Timeout:
            logger.error("❌ Gemini API timeout! (15 saniye)")
            logger.error("   • Bağlantı yavaş, tekrar dene")
        except requests.exceptions.ConnectionError:
            logger.error("❌ Gemini API bağlantı hatası!")
            logger.error("   • İnternet bağlantını kontrol et")
            logger.error("   • VPN kullanıyorsan kapat")
        except Exception as e:
            logger.error(f"❌ Gemini bağlantı hatası: {str(e)}")
            logger.error(f"   • Hata tipi: {type(e).__name__}")
    
    async def chat(self, message: str, context: list = None) -> str:
        """Gemini ile sohbet et"""
        if not self.available:
            return "❌ Gemini API bağlantısı yok! Lütfen GEMINI_API_KEY ekleyin.\nhttps://aistudio.google.com/app/apikey"
        
        try:
            contents = []
            
            if context:
                for msg in context[-5:]:
                    contents.append({
                        "parts": [{"text": msg['content']}]
                    })
            
            contents.append({
                "parts": [{"text": message}]
            })
            
            data = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 2048
                }
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.api_url,
                    json=data,
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                db.track_gemini()
                
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError) as e:
                    return f"❌ Yanıt formatı hatası: {str(e)}"
            else:
                return f"❌ API Hatası ({response.status_code})"
                
        except Exception as e:
            return f"❌ Bağlantı hatası: {str(e)}"
    
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Kod oluştur"""
        if not self.available:
            return "# Gemini API bağlantısı yok!"
        
        try:
            full_prompt = f"""Write {language} code for: {prompt}
            
Requirements:
- Only output the code, no explanations
- No markdown formatting
- Include comments in Turkish
- Make it production-ready"""
            
            data = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 4096
                }
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.api_url,
                    json=data,
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                db.track_gemini()
                
                try:
                    code = result['candidates'][0]['content']['parts'][0]['text']
                    
                    if code.startswith("```"):
                        lines = code.split('\n')
                        if len(lines) > 2:
                            code = '\n'.join(lines[1:-1])
                    
                    return code
                except (KeyError, IndexError):
                    return "# Yanıt formatı hatası"
            else:
                return f"# Hata: {response.status_code}"
                
        except Exception as e:
            return f"# Hata: {str(e)}"

# ======================================================================
# 🤖 DİSCORD BOT
# ======================================================================
class GeminiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
        self.start_time = datetime.now()
        self.gemini = GeminiClient(config.GEMINI_API_KEY)
        self.owner_ids = config.OWNER_IDS
        self.last_heartbeat = time.time()
        
        # Durum özeti
        logger.info("=" * 50)
        logger.info("🤖 BOT DURUM ÖZETİ")
        logger.info("=" * 50)
        logger.info(f"🤖 Gemini: {'✅ AKTİF' if self.gemini.available else '❌ PASIF'}")
        logger.info(f"👤 Owner ID'ler: {self.owner_ids if self.owner_ids else 'YOK (varsayılan owner kullanılacak)'}")
        logger.info("=" * 50)
    
    async def setup_hook(self):
        try:
            await self.tree.sync()
            logger.info(f"✅ {len(self.tree.get_commands())} slash komut yüklendi")
        except Exception as e:
            logger.error(f"❌ Slash komut senkronizasyon hatası: {e}")
    
    async def on_ready(self):
        self.last_heartbeat = time.time()
        logger.info(f"✅ Bot hazır: {self.user}")
        logger.info(f"🌐 Sunucu sayısı: {len(self.guilds)}")
        logger.info(f"👥 Kullanıcılar: {len(self.users)}")
        
        await self.change_presence(
            activity=discord.Game("✨ Gemini AI | !help"),
            status=discord.Status.online
        )
    
    async def on_message(self, message):
        if message.author.bot:
            return
        
        self.last_heartbeat = time.time()
        await self.process_commands(message)
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"❌ Komut bulunamadı: `{ctx.message.content}`\n📝 `!help` yazarak tüm komutları görebilirsin.")
        else:
            logger.error(f"❌ Komut hatası: {error}")
            await ctx.send(f"❌ Hata: {str(error)[:100]}")
    
    def is_owner(self, user_id: int) -> bool:
        main_owner = 1298163612189597716
        return user_id in self.owner_ids or user_id == main_owner

bot = GeminiBot()

# ======================================================================
# 📝 MODAL SINIFLARI
# ======================================================================
class GeminiModal(Modal, title="💬 Gemini ile Sohbet"):
    mesaj = TextInput(
        label="Mesajınız",
        style=discord.TextStyle.paragraph,
        placeholder="Ne sormak istersiniz?",
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await gemini_slash(interaction, self.mesaj.value)

class KodModal(Modal, title="💻 Kod Oluştur"):
    prompt = TextInput(
        label="Ne yapmak istiyorsunuz?",
        style=discord.TextStyle.paragraph,
        placeholder="Örnek: Discord botu, web sunucusu, hesap makinesi...",
        required=True,
        max_length=1000
    )
    dil = TextInput(
        label="Programlama dili",
        placeholder="python",
        default="python",
        required=False,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await kod_slash(interaction, self.prompt.value, self.dil.value)

# ======================================================================
# 🎯 PREFIX KOMUTLAR
# ======================================================================

@bot.command(name="ping")
async def ping(ctx):
    """!ping - Bot durumunu test et"""
    await ctx.send(f"🏓 Pong! **{round(bot.latency * 1000)}ms**")
    db.track_command("ping")

@bot.command(name="test")
async def test(ctx):
    """!test - Bot bilgilerini göster"""
    embed = Embed(
        title="🤖 Bot Durumu",
        color=0x4285F4,
        timestamp=datetime.now()
    )
    
    gemini_durum = "✅ Aktif" if bot.gemini.available else "❌ Pasif"
    
    embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Sunucular", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Kullanıcılar", value=len(bot.users), inline=True)
    embed.add_field(name="🤖 Gemini", value=gemini_durum, inline=True)
    embed.add_field(name="💬 Toplam Mesaj", value=db.stats.get("total_messages", 0), inline=True)
    embed.add_field(name="📊 API Kullanım", value=f"{db.stats.get('gemini_calls', 0)} istek", inline=True)
    
    if not bot.gemini.available:
        embed.add_field(name="⚠️ Gemini Hatası", value="API anahtarı kontrol ediliyor...", inline=False)
    
    await ctx.send(embed=embed)
    db.track_command("test")

@bot.command(name="help")
async def help_command(ctx):
    """!help - Yardım menüsü"""
    embed = Embed(
        title="📋 Gemini Bot Komutları",
        description="✨ **60 istek/dakika ÜCRETSİZ!**",
        color=0x4285F4
    )
    
    embed.add_field(
        name="📝 Prefix Komutlar (!)",
        value="`!ping` - Bot test et\n"
              "`!test` - Bot durumu\n"
              "`!help` - Bu menü\n"
              "`!gemini <mesaj>` - Gemini'ye sor\n"
              "`!kod <dil> <açıklama>` - Kod oluştur\n"
              "`!temizle` - Hafızanı temizle",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Slash Komutlar (/)",
        value="`/gemini` - Sohbet et\n"
              "`/kod` - Kod oluştur\n"
              "`/durum` - Bot durumu\n"
              "`/menü` - Ana menü\n"
              "`/hafıza` - Hafızanı görüntüle",
        inline=False
    )
    
    gemini_durum = "✅ Aktif" if bot.gemini.available else "❌ Pasif (API anahtarı gerekli!)"
    embed.set_footer(text=f"{bot.user.name} • Gemini: {gemini_durum}")
    
    await ctx.send(embed=embed)
    db.track_command("help")

@bot.command(name="gemini")
async def gemini_command(ctx, *, mesaj: str):
    """!gemini <mesaj> - Gemini'ye sor"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        return
    
    async with ctx.typing():
        try:
            if not bot.gemini.available:
                await ctx.send("❌ Gemini API bağlantısı yok! Lütfen GEMINI_API_KEY ekleyin.")
                return
            
            memory = db.get_memory(ctx.author.id)
            response = await bot.gemini.chat(mesaj, memory)
            
            db.add_to_memory(ctx.author.id, "user", mesaj)
            db.add_to_memory(ctx.author.id, "assistant", response[:500])
            db.track_command("gemini")
            
            if len(response) > 1900:
                for i in range(0, len(response), 1900):
                    await ctx.send(response[i:i+1900])
            else:
                await ctx.send(response)
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name="kod")
async def kod_command(ctx, dil: str = "python", *, aciklama: str):
    """!kod <dil> <açıklama> - Kod oluştur"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        return
    
    async with ctx.typing():
        try:
            if not bot.gemini.available:
                await ctx.send("❌ Gemini API bağlantısı yok!")
                return
            
            code = await bot.gemini.generate_code(aciklama, dil)
            db.track_command("kod")
            
            filename = f"kod_{int(time.time())}.{dil}"
            filepath = config.WORKSPACE_DIR / filename
            filepath.write_text(code, encoding='utf-8')
            
            embed = Embed(
                title=f"💻 {dil.capitalize()} Kodu",
                description=f"**İstek:** {aciklama[:200]}",
                color=0x4285F4
            )
            embed.add_field(name="📏 Uzunluk", value=f"{len(code)} karakter", inline=True)
            
            if len(code) < 1000:
                embed.add_field(name="📝 Kod", value=f"```{dil}\n{code[:500]}\n```", inline=False)
                await ctx.send(embed=embed)
            else:
                embed.add_field(name="📁 Dosya", value=f"`{filename}`", inline=True)
                await ctx.send(embed=embed, file=File(filepath))
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name="temizle")
async def temizle_command(ctx):
    """!temizle - Hafızanı temizle"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        return
    
    db.clear_memory(ctx.author.id)
    await ctx.send("✅ Hafızan temizlendi! Artık ben seni unuttum 😊")
    db.track_command("temizle")

# ======================================================================
# ⚡ SLASH KOMUTLAR
# ======================================================================

@bot.tree.command(name="gemini", description="💬 Gemini ile sohbet et")
@app_commands.describe(mesaj="Ne sormak istersin?")
async def gemini_slash(interaction: discord.Interaction, mesaj: str):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        if not bot.gemini.available:
            await interaction.followup.send("❌ Gemini API bağlantısı yok! Lütfen GEMINI_API_KEY ekleyin.")
            return
        
        memory = db.get_memory(interaction.user.id)
        response = await bot.gemini.chat(mesaj, memory)
        
        db.add_to_memory(interaction.user.id, "user", mesaj)
        db.add_to_memory(interaction.user.id, "assistant", response[:500])
        db.track_command("slash_gemini")
        
        embed = Embed(
            title="💬 Gemini Sohbet",
            description=f"**{interaction.user.name}** sordu:",
            color=0x4285F4,
            timestamp=datetime.now()
        )
        embed.add_field(name="📤 Siz", value=f"```{mesaj[:500]}```", inline=False)
        embed.add_field(name="📥 Gemini", value=f"{response[:1500]}", inline=False)
        embed.set_footer(text=f"60 istek/dakika • ÜCRETSİZ!")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="kod", description="💻 Kod oluştur")
@app_commands.describe(prompt="Ne yapmak istiyorsun?", dil="Programlama dili")
async def kod_slash(interaction: discord.Interaction, prompt: str, dil: str = "python"):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        if not bot.gemini.available:
            await interaction.followup.send("❌ Gemini API bağlantısı yok!")
            return
        
        code = await bot.gemini.generate_code(prompt, dil)
        db.track_command("slash_kod")
        
        filename = f"kod_{int(time.time())}.{dil}"
        filepath = config.WORKSPACE_DIR / filename
        filepath.write_text(code, encoding='utf-8')
        
        embed = Embed(
            title=f"💻 {dil.capitalize()} Kodu",
            description=f"**İstek:** {prompt[:200]}",
            color=0x4285F4
        )
        embed.add_field(name="📏 Uzunluk", value=f"{len(code)} karakter", inline=True)
        
        if len(code) < 1000:
            embed.add_field(name="📝 Kod", value=f"```{dil}\n{code[:500]}\n```", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            embed.add_field(name="📁 Dosya", value=f"`{filename}`", inline=True)
            await interaction.followup.send(embed=embed, file=File(filepath))
        
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="durum", description="📊 Bot durumunu göster")
async def durum_slash(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    uptime = datetime.now() - bot.start_time
    saat = int(uptime.total_seconds() / 3600)
    dakika = int((uptime.total_seconds() % 3600) / 60)
    
    embed = Embed(
        title="📊 Bot Durumu",
        color=0x4285F4,
        timestamp=datetime.now()
    )
    
    gemini_durum = "✅ Aktif" if bot.gemini.available else "❌ Pasif"
    
    embed.add_field(name="⏰ Çalışma Süresi", value=f"{saat}s {dakika}d", inline=True)
    embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Sunucular", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Kullanıcılar", value=len(bot.users), inline=True)
    embed.add_field(name="🤖 Gemini", value=gemini_durum, inline=True)
    embed.add_field(name="📊 API Kullanım", value=f"{db.stats.get('gemini_calls', 0)} istek", inline=True)
    
    if not bot.gemini.available:
        embed.add_field(name="⚠️ Gemini Hatası", value="API anahtarı kontrol ediliyor...", inline=False)
    
    await interaction.response.send_message(embed=embed)
    db.track_command("slash_durum")

@bot.tree.command(name="menü", description="📋 Ana menü")
async def menu_slash(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    embed = Embed(
        title="📋 Gemini Bot Menüsü",
        description="✨ **60 istek/dakika ÜCRETSİZ!**",
        color=0x4285F4
    )
    
    embed.add_field(name="💬 /gemini", value="Sohbet et", inline=False)
    embed.add_field(name="💻 /kod", value="Kod oluştur", inline=False)
    embed.add_field(name="📊 /durum", value="Bot durumu", inline=False)
    embed.add_field(name="🧹 /hafıza", value="Hafızanı görüntüle/temizle", inline=False)
    
    view = View()
    view.add_item(Button(label="💬 Sohbet", style=discord.ButtonStyle.primary, custom_id="menu_gemini"))
    view.add_item(Button(label="💻 Kod", style=discord.ButtonStyle.success, custom_id="menu_kod"))
    view.add_item(Button(label="📊 Durum", style=discord.ButtonStyle.secondary, custom_id="menu_durum"))
    
    await interaction.response.send_message(embed=embed, view=view)
    db.track_command("menu")

@bot.tree.command(name="hafıza", description="🧹 Hafızanı görüntüle/temizle")
async def hafiza_slash(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    memory = db.get_memory(interaction.user.id)
    
    embed = Embed(
        title="🧠 Hafıza Durumu",
        description=f"Toplam {len(memory)} mesaj hatırlıyorum.",
        color=0x4285F4
    )
    
    if memory:
        son_mesajlar = memory[-5:]
        mesaj_liste = ""
        for msg in son_mesajlar:
            rol = "👤 Siz" if msg['role'] == 'user' else "🤖 Bot"
            mesaj_liste += f"{rol}: {msg['content'][:50]}...\n"
        
        embed.add_field(name="📝 Son 5 Mesaj", value=mesaj_liste, inline=False)
    
    view = View()
    view.add_item(Button(label="🧹 Hafızayı Temizle", style=discord.ButtonStyle.danger, custom_id="temizle_hafiza"))
    
    await interaction.response.send_message(embed=embed, view=view)
    db.track_command("hafiza")

# ======================================================================
# 🎨 BUTON İŞLEYİCİLERİ
# ======================================================================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        
        if not bot.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
            return
        
        if custom_id == "menu_gemini":
            await interaction.response.send_modal(GeminiModal())
        
        elif custom_id == "menu_kod":
            await interaction.response.send_modal(KodModal())
        
        elif custom_id == "menu_durum":
            await durum_slash(interaction)
        
        elif custom_id == "temizle_hafiza":
            db.clear_memory(interaction.user.id)
            await interaction.response.send_message("✅ Hafızan temizlendi!", ephemeral=True)

# ======================================================================
# 🏥 HEALTH CHECK SERVER
# ======================================================================
async def health_check():
    """Railway için health check server"""
    
    async def handler(request):
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "time": datetime.now().isoformat(),
                "bot": str(bot.user) if bot.user else "starting",
                "guilds": len(bot.guilds),
                "gemini": bot.gemini.available,
                "uptime": str(datetime.now() - bot.start_time)
            }, indent=2, ensure_ascii=False),
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
    
    logger.info(f"✅ Health check: 0.0.0.0:{PORT}")
    return runner

# ======================================================================
# 👀 WATCHDOG
# ======================================================================
async def watchdog():
    """Bot sağlığını izle"""
    while True:
        await asyncio.sleep(60)
        
        try:
            heartbeat_age = time.time() - bot.last_heartbeat
            
            if heartbeat_age > 300:
                logger.warning(f"⚠️ Heartbeat yaşlı: {heartbeat_age:.0f}s")
            
            if heartbeat_age > 900:
                logger.error("❌ Bot yanıt vermiyor, yeniden başlatılıyor...")
                os._exit(1)
                
        except Exception as e:
            logger.error(f"❌ Watchdog hatası: {e}")

# ======================================================================
# 🚀 ANA FONKSİYON
# ======================================================================
async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🤖 GEMINI DISCORD BOT - RAILWAY EDITION                   ║
║   ✨ 60 istek/dakika - TAMAMEN ÜCRETSİZ!                    ║
║                                                              ║
║   ✅ Prefix: !ping, !test, !help, !gemini, !kod             ║
║   ✅ Slash: /gemini, /kod, /durum, /menü, /hafıza           ║
║   ✅ Health Check: Her zaman 200 döndürür                   ║
║   ✅ Watchdog: Otomatik yeniden başlatma                    ║
║   ✅ Hafıza: Son 50 mesajı hatırlar                         ║
║   ✅ DEBUG: Environment logları gösterilir                  ║
║   ✅ Owner: Sadece yetkililer kullanabilir                  ║
║   ✅ ekincimhuseyn                                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Token kontrolü
    if not config.DISCORD_TOKEN:
        logger.error("❌ DISCORD_TOKEN bulunamadı!")
        return
    
    if not config.GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY bulunamadı! Bot çalışmayacak.")
    
    # Servisleri başlat
    asyncio.create_task(health_check())
    asyncio.create_task(watchdog())
    
    logger.info("🚀 Bot başlatılıyor...")
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ INTENT HATASI! Discord Developer Portal'da intent'leri aç:")
        logger.error("   1. https://discord.com/developers/applications")
        logger.error("   2. Bot'unu seç → Bot sekmesi")
        logger.error("   3. Tüm Intent'leri AÇ → Save Changes")
    except Exception as e:
        logger.error(f"❌ Kritik hata: {e}")
    finally:
        logger.warning("⚠️ Bot durdu, yeniden başlatılıyor...")
        await asyncio.sleep(5)

# ======================================================================
# 🏁 PROGRAM BAŞLANGICI
# ======================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👌 Bot kapatıldı")
    except Exception as e:
        logger.error(f"💥 Beklenmeyen hata: {e}")
        time.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)
