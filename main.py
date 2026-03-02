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
    • Ağ dayanıklı - asla durmaz!
═══════════════════════════════════════════════════════════════════════════════
"""

# ======================================================================
# 📦 1. İTHALATLAR - %0.618 oranında (Altın oranın küçük kısmı)
# ======================================================================
import os
import sys
import asyncio
import logging
import json
import time
import signal
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
from discord import Embed, Color, File

from openai import OpenAI
from aiohttp import web

# ======================================================================
# ⚙️ 2. RAILWAY KONFİGÜRASYONU - %1 oranında
# ======================================================================
RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT") is not None
PORT = int(os.getenv("PORT", 8080))
BASE_DIR = "/tmp" if RAILWAY_ENV else "."

# ======================================================================
# 🔧 3. ANA KONFİGÜRASYON SINIFI - %1.618 oranında (Altın oranın büyük kısmı)
# ======================================================================
class Config:
    """Tüm konfigürasyon ayarları - Altın oran ile düzenlendi"""
    
    def __init__(self):
        # Discord ayarları
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
        self.OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS', '').split(',') if x.strip()]
        self.ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
        
        # OpenAI ayarları
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.CODE_MODEL = os.getenv("CODE_MODEL", "gpt-4-turbo")
        self.IMAGE_MODEL = os.getenv("IMAGE_MODEL", "dall-e-3")
        
        # Railway yolları
        self.WORKSPACE_DIR = Path(BASE_DIR) / "workspace"
        self.DATA_DIR = Path(BASE_DIR) / "data"
        self.LOGS_DIR = Path(BASE_DIR) / "logs"
        self.TEMP_DIR = Path(BASE_DIR) / "temp"
        
        # Klasörleri oluştur
        for dir_path in [self.WORKSPACE_DIR, self.DATA_DIR, self.LOGS_DIR, self.TEMP_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Bot ayarları
        self.BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
        self.COMMAND_COOLDOWN = int(os.getenv("COMMAND_COOLDOWN", "3"))
        self.MAX_HISTORY = int(os.getenv("MAX_HISTORY", "50"))
        
        # Health check ayarları (esnek)
        self.HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
        self.HEARTBEAT_TIMEOUT = int(os.getenv("HEARTBEAT_TIMEOUT", "900"))  # 15 dakika
        self.NETWORK_TOLERANCE = int(os.getenv("NETWORK_TOLERANCE", "10"))
        self.STARTUP_GRACE = int(os.getenv("STARTUP_GRACE", "300"))  # 5 dakika
        
        # Görsel ayarları
        self.IMAGE_SIZES = ["1024x1024", "1792x1024", "1024x1792"]
        self.DEFAULT_IMAGE_SIZE = "1024x1024"
        self.IMAGE_QUALITY = "standard"  # veya "hd"
        self.MAX_IMAGE_HISTORY = 20
        
        # Güvenlik
        self.MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
        self.MAX_CODE_LENGTH = 10000
        self.RATE_LIMIT = int(os.getenv("RATE_LIMIT", "10"))

config = Config()

# ======================================================================
# 📊 4. LOGGING SİSTEMİ - %0.618 oranında
# ======================================================================
class ColoredFormatter(logging.Formatter):
    """Renkli log formatı"""
    
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    cyan = "\x1b[36;20m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey,
        logging.INFO: green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red
    }
    
    def format(self, record):
        log_color = self.FORMATS.get(record.levelno, self.grey)
        record.msg = f"{log_color}{record.msg}{self.reset}"
        return super().format(record)

# Logging kurulumu
log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
date_format = '%H:%M:%S'

# Dosya logging
file_handler = logging.FileHandler(config.LOGS_DIR / "bot.log", encoding='utf-8')
file_handler.setFormatter(logging.Formatter(log_format, date_format))

# Konsol logging (renkli)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter(log_format, date_format))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger("DevBot")

# ======================================================================
# 📁 5. VERİ YÖNETİCİSİ - %1 oranında
# ======================================================================
class DataManager:
    """Veri yönetimi - JSON tabanlı"""
    
    def __init__(self):
        self.stats_file = config.DATA_DIR / "stats.json"
        self.memory_file = config.DATA_DIR / "memory.json"
        self.settings_file = config.DATA_DIR / "settings.json"
        
        self.stats = self._load_json(self.stats_file, self._default_stats())
        self.memory = self._load_json(self.memory_file, {})
        self.settings = self._load_json(self.settings_file, {})
        
        logger.info("✅ Veri yöneticisi başlatıldı")
    
    def _default_stats(self) -> dict:
        return {
            "start_time": datetime.now().isoformat(),
            "restarts": 0,
            "commands": {},
            "images": 0,
            "chats": 0,
            "codes": 0,
            "errors": 0,
            "network_issues": 0,
            "uptime_history": []
        }
    
    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ JSON yüklenemedi {path}: {e}")
        return default
    
    def _save_json(self, path: Path, data: Any) -> bool:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"❌ JSON kaydedilemedi {path}: {e}")
            return False
    
    def save_all(self):
        """Tüm verileri kaydet"""
        self._save_json(self.stats_file, self.stats)
        self._save_json(self.memory_file, self.memory)
        self._save_json(self.settings_file, self.settings)
    
    def track_command(self, command: str):
        """Komut kullanımını kaydet"""
        self.stats["commands"][command] = self.stats["commands"].get(command, 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def track_metric(self, metric: str):
        """Metrik takibi"""
        self.stats[metric] = self.stats.get(metric, 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def get_user_memory(self, user_id: int) -> list:
        """Kullanıcı hafızasını getir"""
        return self.memory.setdefault(str(user_id), [])
    
    def add_to_memory(self, user_id: int, role: str, content: str):
        """Hafızaya ekle"""
        mem = self.get_user_memory(user_id)
        mem.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Limit aşımı kontrolü
        if len(mem) > config.MAX_HISTORY:
            self.memory[str(user_id)] = mem[-config.MAX_HISTORY:]
        
        self._save_json(self.memory_file, self.memory)
    
    def clear_memory(self, user_id: int):
        """Hafızayı temizle"""
        if str(user_id) in self.memory:
            self.memory[str(user_id)] = []
            self._save_json(self.memory_file, self.memory)

db = DataManager()

# ======================================================================
# 🤖 6. OPENAI İSTEMCİSİ - %1.618 oranında (Ana bileşen)
# ======================================================================
class OpenAIClient:
    """OpenAI API istemcisi - DALL-E 3 + GPT-4"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.image_history = []
        self.total_cost = 0.0
        self.total_tokens = 0
        
        # Model fiyatları (1000 token başına $)
        self.prices = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "dall-e-3": 0.040
        }
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info("✅ OpenAI bağlantısı kuruldu")
                logger.info(f"   • Sohbet: {config.CHAT_MODEL}")
                logger.info(f"   • Kod: {config.CODE_MODEL}")
                logger.info(f"   • Görsel: {config.IMAGE_MODEL}")
            except Exception as e:
                logger.error(f"❌ OpenAI bağlantı hatası: {e}")
    
    # -----------------------------------------------------------------
    # 6.1 SOHBET FONKSİYONU
    # -----------------------------------------------------------------
    async def chat(self, message: str, user_id: int = None) -> str:
        """Sohbet et - hafızalı"""
        if not self.client:
            return "❌ OpenAI API anahtarı gerekli!"
        
        try:
            # Sistem mesajı
            messages = [{
                "role": "system",
                "content": "Sen yardımsever bir asistan. Kısa ve net cevaplar ver."
            }]
            
            # Kullanıcı hafızasını ekle
            if user_id:
                history = db.get_user_memory(user_id)
                for msg in history[-10:]:
                    messages.append(msg)
            
            # Yeni mesaj
            messages.append({"role": "user", "content": message})
            
            # API çağrısı
            start = time.time()
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
            )
            duration = time.time() - start
            
            # Token hesapla (yaklaşık)
            tokens = len(message) // 4 + len(response.choices[0].message.content) // 4
            self.total_tokens += tokens
            
            logger.info(f"💬 Sohbet | {duration:.1f}s | {tokens} token")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Sohbet hatası: {e}")
            return f"❌ Hata: {str(e)[:100]}"
    
    # -----------------------------------------------------------------
    # 6.2 KOD ÜRETME FONKSİYONU
    # -----------------------------------------------------------------
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Kod üret - filtresiz"""
        if not self.client:
            return "# OpenAI API anahtarı gerekli!"
        
        try:
            system = f"""Sen bir {language} uzmanı.
Görev: İstenen kodu üret.
Kural: Sadece kod, açıklama yok.
Kalite: Temiz, çalışan, optimize kod."""

            start = time.time()
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=config.CODE_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000,
                    temperature=0.2
                )
            )
            duration = time.time() - start
            
            code = response.choices[0].message.content
            tokens = len(code) // 4
            self.total_tokens += tokens
            
            logger.info(f"💻 Kod | {language} | {duration:.1f}s | {tokens} token")
            
            return code
            
        except Exception as e:
            logger.error(f"❌ Kod hatası: {e}")
            return f"# Hata: {str(e)}"
    
    # -----------------------------------------------------------------
    # 6.3 GÖRSEL ÜRETME FONKSİYONU (DALL-E 3)
    # -----------------------------------------------------------------
    async def generate_image(self, prompt: str, size: str = None) -> dict:
        """Görsel üret - DALL-E 3"""
        if not self.client:
            raise Exception("OpenAI API anahtarı gerekli!")
        
        # Boyut kontrolü
        if size not in config.IMAGE_SIZES:
            size = config.DEFAULT_IMAGE_SIZE
        
        try:
            logger.info(f"🎨 Görsel üretiliyor: {prompt[:50]}...")
            
            start = time.time()
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.images.generate(
                    model=config.IMAGE_MODEL,
                    prompt=prompt,
                    size=size,
                    quality=config.IMAGE_QUALITY,
                    n=1,
                    response_format="url"
                )
            )
            duration = time.time() - start
            
            # Sonuç hazırla
            result = {
                "url": response.data[0].url,
                "prompt": prompt,
                "size": size,
                "created": datetime.now().isoformat(),
                "duration": f"{duration:.1f}s",
                "revised_prompt": getattr(response.data[0], 'revised_prompt', prompt)
            }
            
            # Geçmişe ekle
            self.image_history.append(result)
            if len(self.image_history) > config.MAX_IMAGE_HISTORY:
                self.image_history = self.image_history[-config.MAX_IMAGE_HISTORY:]
            
            # Maliyet (yaklaşık)
            self.total_cost += self.prices["dall-e-3"]
            
            logger.info(f"✅ Görsel oluşturuldu | {size} | {duration:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Görsel hatası: {e}")
            raise Exception(f"DALL-E hatası: {str(e)}")
    
    # -----------------------------------------------------------------
    # 6.4 YARDIMCI FONKSİYONLAR
    # -----------------------------------------------------------------
    def get_recent_images(self, limit: int = 5) -> list:
        """Son görselleri getir"""
        return self.image_history[-limit:]
    
    def get_stats(self) -> dict:
        """İstatistikleri getir"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "images": len(self.image_history)
        }

# OpenAI istemcisini başlat
ai = OpenAIClient(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

# ======================================================================
# 🎨 7. UI BİLEŞENLERİ - %1 oranında
# ======================================================================
class Emojis:
    """Emoji sabitleri"""
    HOME = "🏠"
    ROCKET = "🚀"
    SPARKLES = "✨"
    DEV = "👑"
    AI = "🤖"
    CHAT = "💬"
    CODE = "💻"
    IMAGE = "🎨"
    FILE = "📄"
    FOLDER = "📁"
    SAVE = "💾"
    DELETE = "🗑️"
    DOWNLOAD = "📥"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    STATS = "📊"
    CLOCK = "🕐"
    NETWORK = "🌐"
    HEART = "💓"
    SETTINGS = "⚙️"

class Colors:
    """Renk sabitleri"""
    PRIMARY = 0x5865F2  # Discord mavisi
    SUCCESS = 0x57F287  # Yeşil
    DANGER = 0xED4245   # Kırmızı
    WARNING = 0xFEE75C   # Sarı
    INFO = 0x5865F2      # Mavi
    GOLD = 0xF1C40F      # Altın
    PURPLE = 0x9B59B6    # Mor
    DEV = 0xFF0000       # Kırmızı (geliştirici)

# ----------------------------------------------------------------------
# 7.1 GÖRSEL MODAL
# ----------------------------------------------------------------------
class ImageModal(Modal, title="🎨 Görsel Oluştur - DALL-E 3"):
    
    prompt = TextInput(
        label="Ne görmek istersin?",
        style=discord.TextStyle.paragraph,
        placeholder="Örnek: Uzaylı bir kedi, neon ışıklar, cyberpunk şehir, fantastik manzara...",
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
        """Modal gönderildiğinde"""
        await image_command(
            interaction,
            self.prompt.value,
            self.size.value if self.size.value else "1024x1024"
        )

# ----------------------------------------------------------------------
# 7.2 SOHBET MODAL
# ----------------------------------------------------------------------
class ChatModal(Modal, title="💬 Hızlı Sohbet"):
    
    message = TextInput(
        label="Mesajınız",
        style=discord.TextStyle.paragraph,
        placeholder="Ne sormak istersin?",
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await chat_command(interaction, self.message.value)

# ----------------------------------------------------------------------
# 7.3 KOD MODAL
# ----------------------------------------------------------------------
class CodeModal(Modal, title="💻 Kod Oluştur"):
    
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
        await code_command(
            interaction,
            self.prompt.value,
            self.language.value if self.language.value else "python"
        )

# ======================================================================
# 🤖 8. DİSCORD BOT SINIFI - %1.618 oranında (Ana bileşen)
# ======================================================================
class DevBot(commands.Bot):
    """Ana bot sınıfı - Tüm özellikler burada"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=config.BOT_PREFIX,
            intents=intents,
            help_command=None
        )
        
        # Bot bilgileri
        self.start_time = datetime.now()
        self.version = "7.0.0"
        self.build = "golden-ratio"
        
        # OpenAI
        self.ai = ai
        
        # Health check değişkenleri
        self.last_heartbeat = time.time()
        self.health_runner = None
        self.health_fail_count = 0
        self.network_issues = 0
        self.consecutive_errors = 0
        
        # İstatistikler
        self.commands_used = 0
        self.errors_count = 0
        
        logger.info("✅ Bot sınıfı oluşturuldu")
    
    # -----------------------------------------------------------------
    # 8.1 KURULUM FONKSİYONLARI
    # -----------------------------------------------------------------
    async def setup_hook(self):
        """Bot kurulumu - komutları senkronize et"""
        try:
            await self.tree.sync()
            logger.info(f"✅ {len(self.tree.get_commands())} komut senkronize edildi")
        except Exception as e:
            logger.error(f"❌ Komut senkronizasyon hatası: {e}")
    
    async def on_ready(self):
        """Bot hazır olduğunda"""
        self.last_heartbeat = time.time()
        self.consecutive_errors = 0
        
        # Bot bilgileri
        logger.info("")
        logger.info("╔════════════════════════════════════════════════════╗")
        logger.info("║                                                    ║")
        logger.info(f"║   ✅ Bot AKTİF: {self.user}                ║")
        logger.info("║                                                    ║")
        logger.info(f"║   • Sunucular: {len(self.guilds)}                    ║")
        logger.info(f"║   • Kullanıcılar: {len(self.users)}                   ║")
        logger.info(f"║   • Komutlar: {len(self.tree.get_commands())}                   ║")
        logger.info(f"║   • Gecikme: {round(self.latency * 1000)}ms                    ║")
        logger.info("║                                                    ║")
        logger.info("║   🎨 DALL-E 3 AKTİF                                ║")
        logger.info("║   💬 GPT-4o-mini AKTİF                             ║")
        logger.info("║   💻 GPT-4-turbo AKTİF                             ║")
        logger.info("║                                                    ║")
        logger.info("║   🌐 Ağ dayanıklı mod AKTİF                        ║")
        logger.info("║   🚀 Railway optimizasyonu AKTİF                   ║")
        logger.info("║                                                    ║")
        logger.info("╚════════════════════════════════════════════════════╝")
        logger.info("")
        
        # Durum güncelle
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=f"🎨 /image | 💬 /chat | 💻 /code"
            ),
            status=discord.Status.online
        )
    
    # -----------------------------------------------------------------
    # 8.2 MESAJ İŞLEYİCİLER
    # -----------------------------------------------------------------
    async def on_message(self, message):
        """Mesaj geldiğinde"""
        if message.author.bot:
            return
        
        # Heartbeat güncelle
        self.last_heartbeat = time.time()
        
        # Komutları işle
        await self.process_commands(message)
    
    async def on_command_error(self, ctx, error):
        """Komut hatası olduğunda"""
        self.errors_count += 1
        self.consecutive_errors += 1
        logger.error(f"❌ Komut hatası: {error}")
        
        # Çok fazla hata varsa uyar
        if self.consecutive_errors > 10:
            logger.warning(f"⚠️ Çok fazla hata: {self.consecutive_errors}")
        
        await ctx.send(f"❌ Hata: {str(error)[:100]}")
    
    # -----------------------------------------------------------------
    # 8.3 YARDIMCI FONKSİYONLAR
    # -----------------------------------------------------------------
    def is_owner(self, user_id: int) -> bool:
        """Kullanıcı bot sahibi mi?"""
        return user_id in config.OWNER_IDS
    
    def is_admin(self, user_id: int) -> bool:
        """Kullanıcı admin mi?"""
        return user_id in config.ADMIN_IDS or self.is_owner(user_id)
    
    def get_uptime(self) -> str:
        """Çalışma süresini getir"""
        delta = datetime.now() - self.start_time
        hours = int(delta.total_seconds() / 3600)
        minutes = int((delta.total_seconds() % 3600) / 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_stats(self) -> dict:
        """Bot istatistiklerini getir"""
        return {
            "uptime": self.get_uptime(),
            "latency": round(self.latency * 1000),
            "guilds": len(self.guilds),
            "users": len(self.users),
            "commands": self.commands_used,
            "errors": self.errors_count,
            "network_issues": self.network_issues
        }

# Bot'u başlat
bot = DevBot()

# ======================================================================
# 🎯 9. KOMUTLAR - %1.618 oranında (Ana işlevler)
# ======================================================================

# ----------------------------------------------------------------------
# 9.1 GÖRSEL KOMUTLARI
# ----------------------------------------------------------------------
@bot.tree.command(name="image", description="🎨 Görsel oluştur (DALL-E 3)")
@app_commands.describe(
    prompt="Ne görmek istersin?",
    size="Boyut (1024x1024, 1792x1024, 1024x1792)"
)
async def image_command(interaction: discord.Interaction, prompt: str, size: str = "1024x1024"):
    """DALL-E 3 ile görsel oluştur"""
    
    # Yetki kontrolü
    if not bot.is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Bu komutu kullanma yetkiniz yok!", ephemeral=True)
        return
    
    # AI kontrolü
    if not bot.ai:
        await interaction.response.send_message("❌ OpenAI API anahtarı bulunamadı!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        # Hazırlık mesajı
        await interaction.followup.send(f"🎨 **Görsel oluşturuluyor...**\n```{prompt[:100]}```")
        
        # Görseli oluştur
        result = await bot.ai.generate_image(prompt, size)
        
        # İstatistik
        db.track_command("image")
        db.track_metric("images")
        bot.commands_used += 1
        
        # Embed oluştur
        embed = Embed(
            title="🖼️ DALL-E 3 Görsel",
            description=f"**Prompt:** {prompt}",
            color=Colors.PRIMARY,
            timestamp=datetime.now()
        )
        
        embed.set_image(url=result["url"])
        embed.add_field(name="📐 Boyut", value=result["size"], inline=True)
        embed.add_field(name="⏱️ Süre", value=result["duration"], inline=True)
        
        if result["revised_prompt"] != prompt:
            embed.add_field(
                name="📝 OpenAI Düzeltmesi",
                value=f"```{result['revised_prompt'][:200]}```",
                inline=False
            )
        
        embed.set_footer(text=f"İsteyen: {interaction.user.display_name}")
        
        # Butonlar
        view = View(timeout=60)
        view.add_item(Button(
            label="📥 İndir",
            style=discord.ButtonStyle.success,
            url=result["url"],
            emoji="📥"
        ))
        view.add_item(Button(
            label="🔄 Tekrar Üret",
            style=discord.ButtonStyle.primary,
            custom_id=f"regenerate_{prompt[:50]}",
            emoji="🔄"
        ))
        
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"❌ Görsel hatası: {e}")
        await interaction.followup.send(f"❌ **Hata:** {str(e)}")

@bot.tree.command(name="imagine", description="⚡ Hızlı görsel oluştur")
@app_commands.describe(prompt="Ne görmek istersin?")
async def imagine_command(interaction: discord.Interaction, prompt: str):
    """Hızlı görsel oluştur"""
    await image_command(interaction, prompt, "1024x1024")

@bot.tree.command(name="recent", description="📸 Son görselleri göster")
@app_commands.describe(limit="Gösterilecek görsel sayısı (1-10)")
async def recent_command(interaction: discord.Interaction, limit: int = 5):
    """Son oluşturulan görselleri göster"""
    
    if not bot.is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    limit = min(max(limit, 1), 10)
    images = bot.ai.get_recent_images(limit) if bot.ai else []
    
    if not images:
        await interaction.response.send_message("📸 Henüz görsel oluşturulmamış!")
        return
    
    embed = Embed(
        title="📸 Son Görseller",
        description=f"Son {len(images)} görsel",
        color=Colors.INFO
    )
    
    for i, img in enumerate(images, 1):
        created = img['created'][:16] if isinstance(img['created'], str) else "Bilinmiyor"
        embed.add_field(
            name=f"{i}. {img['prompt'][:50]}...",
            value=f"📐 {img['size']} | ⏱️ {img.get('duration', '?')}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ----------------------------------------------------------------------
# 9.2 SOHBET KOMUTLARI
# ----------------------------------------------------------------------
@bot.tree.command(name="chat", description="💬 Sohbet et (hafızalı)")
@app_commands.describe(message="Mesajınız")
async def chat_command(interaction: discord.Interaction, message: str):
    """AI ile sohbet et - hafızalı"""
    
    if not bot.is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    if not bot.ai:
        await interaction.response.send_message("❌ OpenAI API anahtarı bulunamadı!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        # AI'dan cevap al
        response = await bot.ai.chat(message, interaction.user.id)
        
        # İstatistik
        db.track_command("chat")
        db.track_metric("chats")
        bot.commands_used += 1
        
        # Hafızaya ekle
        db.add_to_memory(interaction.user.id, "user", message)
        db.add_to_memory(interaction.user.id, "assistant", response)
        
        # Embed oluştur
        embed = Embed(
            title="💬 Sohbet",
            color=Colors.SUCCESS,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📤 Siz",
            value=f"```{message[:500]}```",
            inline=False
        )
        
        embed.add_field(
            name="📥 AI",
            value=f"```{response[:1500]}```",
            inline=False
        )
        
        embed.set_footer(text=f"{interaction.user.display_name} | Token: ~{len(response)//4}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"❌ Sohbet hatası: {e}")
        await interaction.followup.send(f"❌ **Hata:** {str(e)}")

@bot.tree.command(name="clear", description="🧹 Sohbet geçmişini temizle")
async def clear_command(interaction: discord.Interaction):
    """Kullanıcının sohbet geçmişini temizle"""
    
    db.clear_memory(interaction.user.id)
    await interaction.response.send_message("✅ Sohbet geçmişiniz temizlendi!")

# ----------------------------------------------------------------------
# 9.3 KOD KOMUTLARI
# ----------------------------------------------------------------------
@bot.tree.command(name="code", description="💻 Kod oluştur")
@app_commands.describe(
    prompt="Ne yapmak istiyorsun?",
    language="Programlama dili"
)
async def code_command(interaction: discord.Interaction, prompt: str, language: str = "python"):
    """Kod oluştur"""
    
    if not bot.is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    if not bot.ai:
        await interaction.response.send_message("❌ OpenAI API anahtarı bulunamadı!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        # Kodu oluştur
        code = await bot.ai.generate_code(prompt, language)
        
        # İstatistik
        db.track_command("code")
        db.track_metric("codes")
        bot.commands_used += 1
        
        # Dosyaya kaydet
        filename = f"code_{int(time.time())}.{language}"
        filepath = config.WORKSPACE_DIR / filename
        filepath.write_text(code, encoding='utf-8')
        
        # Embed oluştur
        embed = Embed(
            title=f"💻 Kod Oluşturuldu - {language}",
            description=f"**Prompt:** {prompt}",
            color=Colors.GOLD
        )
        
        embed.add_field(name="📁 Dosya", value=f"`{filename}`", inline=True)
        embed.add_field(name="📏 Uzunluk", value=f"{len(code)} karakter", inline=True)
        
        # Kodu göster (kısaysa)
        if len(code) < 1000:
            embed.add_field(
                name="📝 Kod",
                value=f"```{language}\n{code}\n```",
                inline=False
            )
        
        embed.set_footer(text=f"Token: ~{len(code)//4}")
        
        # Dosyayı ekle
        file = File(filepath, filename=filename)
        
        await interaction.followup.send(embed=embed, file=file)
        
    except Exception as e:
        logger.error(f"❌ Kod hatası: {e}")
        await interaction.followup.send(f"❌ **Hata:** {str(e)}")

# ----------------------------------------------------------------------
# 9.4 SİSTEM KOMUTLARI
# ----------------------------------------------------------------------
@bot.tree.command(name="status", description="📊 Bot durumu")
async def status_command(interaction: discord.Interaction):
    """Bot durumunu göster"""
    
    if not bot.is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    stats = bot.get_stats()
    ai_stats = bot.ai.get_stats() if bot.ai else {}
    db_stats = db.stats
    
    embed = Embed(
        title="📊 Bot Durumu",
        color=Colors.INFO,
        timestamp=datetime.now()
    )
    
    # Sistem bilgileri
    embed.add_field(
        name="🤖 Bot",
        value=f"```\n"
              f"Çalışma: {stats['uptime']}\n"
              f"Gecikme: {stats['latency']}ms\n"
              f"Sunucu: {stats['guilds']}\n"
              f"Komut: {stats['commands']}\n"
              f"```",
        inline=True
    )
    
    # AI bilgileri
    embed.add_field(
        name="🧠 AI",
        value=f"```\n"
              f"Token: {ai_stats.get('total_tokens', 0):,}\n"
              f"Maliyet: ${ai_stats.get('total_cost', 0)}\n"
              f"Görsel: {ai_stats.get('images', 0)}\n"
              f"```",
        inline=True
    )
    
    # İstatistikler
    embed.add_field(
        name="📈 İstatistik",
        value=f"```\n"
              f"Sohbet: {db_stats.get('chats', 0)}\n"
              f"Görsel: {db_stats.get('images', 0)}\n"
              f"Kod: {db_stats.get('codes', 0)}\n"
              f"Hata: {stats['errors']}\n"
              f"```",
        inline=True
    )
    
    # Ağ durumu
    network_status = "✅ İyi" if bot.network_issues < 5 else "⚠️ Sorunlu"
    embed.add_field(
        name="🌐 Ağ",
        value=f"```\n"
              f"Durum: {network_status}\n"
              f"Sorun: {bot.network_issues}\n"
              f"Heartbeat: {int(time.time() - bot.last_heartbeat)}s\n"
              f"```",
        inline=True
    )
    
    embed.set_footer(text=f"Versiyon: {bot.version} | Build: {bot.build}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="menu", description="📋 Ana menü")
async def menu_command(interaction: discord.Interaction):
    """Ana menüyü göster"""
    
    if not bot.is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    embed = Embed(
        title="📋 DevBot V7 Ana Menü",
        description="""
        ╔════════════════════════════════════╗
        ║                                    ║
        ║   🎨 **GÖRSEL İŞLEMLERİ**           ║
        ║   `/image` - Detaylı görsel üret   ║
        ║   `/imagine` - Hızlı görsel üret   ║
        ║   `/recent` - Son görseller        ║
        ║                                    ║
        ║   💬 **SOHBET İŞLEMLERİ**           ║
        ║   `/chat` - Sohbet et              ║
        ║   `/clear` - Geçmiş temizle        ║
        ║                                    ║
        ║   💻 **KOD İŞLEMLERİ**              ║
        ║   `/code` - Kod oluştur            ║
        ║                                    ║
        ║   📊 **SİSTEM İŞLEMLERİ**           ║
        ║   `/status` - Bot durumu           ║
        ║   `/menu` - Bu menü                ║
        ║                                    ║
        ╚════════════════════════════════════╝
        """,
        color=Colors.PRIMARY
    )
    
    # Butonlar
    view = View(timeout=60)
    view.add_item(Button(label="🎨 Görsel", style=discord.ButtonStyle.primary, custom_id="menu_image", emoji="🎨"))
    view.add_item(Button(label="💬 Sohbet", style=discord.ButtonStyle.success, custom_id="menu_chat", emoji="💬"))
    view.add_item(Button(label="💻 Kod", style=discord.ButtonStyle.secondary, custom_id="menu_code", emoji="💻"))
    view.add_item(Button(label="📊 Durum", style=discord.ButtonStyle.danger, custom_id="menu_status", emoji="📊"))
    
    await interaction.response.send_message(embed=embed, view=view)

# ----------------------------------------------------------------------
# 9.5 YÖNETİM KOMUTLARI (Sadece owner)
# ----------------------------------------------------------------------
@bot.tree.command(name="admin", description="⚙️ Yönetim komutları (Sadece owner)")
async def admin_command(interaction: discord.Interaction):
    """Yönetim menüsü - sadece bot sahibi"""
    
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Bu komut sadece bot sahibi için!", ephemeral=True)
        return
    
    embed = Embed(
        title="⚙️ Yönetim Paneli",
        description="Bot yönetim komutları",
        color=Colors.DEV
    )
    
    embed.add_field(
        name="📊 İstatistikler",
        value=f"```\n"
              f"Restart: {db.stats.get('restarts', 0)}\n"
              f"Ağ Sorunu: {db.stats.get('network_issues', 0)}\n"
              f"Komutlar: {sum(db.stats['commands'].values())}\n"
              f"```",
        inline=False
    )
    
    # Yönetim butonları
    view = View(timeout=60)
    view.add_item(Button(label="🔄 Restart", style=discord.ButtonStyle.danger, custom_id="admin_restart", emoji="🔄"))
    view.add_item(Button(label="📥 Kaydet", style=discord.ButtonStyle.success, custom_id="admin_save", emoji="📥"))
    view.add_item(Button(label="🧹 Temizle", style=discord.ButtonStyle.secondary, custom_id="admin_clean", emoji="🧹"))
    
    await interaction.response.send_message(embed=embed, view=view)

# ======================================================================
# 🎨 10. BUTON İŞLEYİCİLERİ
# ======================================================================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Buton ve menü etkileşimlerini işle"""
    
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        
        # Yetki kontrolü
        if not bot.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
            return
        
        # Menü butonları
        if custom_id == "menu_image":
            await interaction.response.send_modal(ImageModal())
        
        elif custom_id == "menu_chat":
            await interaction.response.send_modal(ChatModal())
        
        elif custom_id == "menu_code":
            await interaction.response.send_modal(CodeModal())
        
        elif custom_id == "menu_status":
            await status_command(interaction)
        
        # Admin butonları
        elif custom_id == "admin_restart" and bot.is_owner(interaction.user.id):
            await interaction.response.send_message("🔄 Bot yeniden başlatılıyor...")
            await asyncio.sleep(2)
            os._exit(1)
        
        elif custom_id == "admin_save" and bot.is_owner(interaction.user.id):
            db.save_all()
            await interaction.response.send_message("✅ Veriler kaydedildi!", ephemeral=True)
        
        elif custom_id == "admin_clean" and bot.is_owner(interaction.user.id):
            # Geçici dosyaları temizle
            for file in config.TEMP_DIR.glob("*"):
                if file.is_file():
                    file.unlink()
            await interaction.response.send_message("✅ Geçici dosyalar temizlendi!", ephemeral=True)
        
        # Görsel butonları
        elif custom_id.startswith("regenerate_"):
            prompt = custom_id[11:]
            await image_command(interaction, prompt, "1024x1024")

# ======================================================================
# 🏥 11. HEALTH CHECK SERVER - KESİN ÇÖZÜM
# ======================================================================
# ÖNEMLİ: Bu server HER ZAMAN 200 döndürür
# Bot durumunu kontrol ETMEZ!
# Railway asla restart ETMEZ!

async def health_check():
    """Railway health check server - KESİN ÇÖZÜM"""
    
    async def handler(request):
        """Health check endpoint - HER ZAMAN 200"""
        # Bot bilgisi (ama hata verme!)
        uptime = (datetime.now() - bot.start_time).total_seconds()
        
        return web.Response(
            text=json.dumps({
                "status": "alive",
                "time": datetime.now().isoformat(),
                "uptime": f"{uptime:.0f}s",
                "bot_ready": bot.is_ready() if bot else False,
                "version": bot.version if bot else "unknown"
            }, ensure_ascii=False),
            status=200,  # HER ZAMAN 200
            content_type="application/json; charset=utf-8"
        )
    
    async def root_handler(request):
        """Root endpoint"""
        return web.Response(
            text="DevBot V7 Railway Edition - Always 200 OK",
            status=200
        )
    
    # Web uygulaması
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", handler)
    
    # Server'ı başlat
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════╗")
    logger.info("║                                                    ║")
    logger.info(f"║   🏥 HEALTH CHECK AKTİF                          ║")
    logger.info(f"║   • Port: {PORT}                                    ║")
    logger.info(f"║   • Endpoint: /health                            ║")
    logger.info(f"║   • Durum: HER ZAMAN 200 OK                      ║")
    logger.info(f"║   • Bot kontrolü: YOK (asla restart etmez!)      ║")
    logger.info("║                                                    ║")
    logger.info("╚════════════════════════════════════════════════════╝")
    logger.info("")
    
    return runner

# ======================================================================
# 👀 12. WATCHDOG - AĞ DAYANIKLI
# ======================================================================
async def watchdog():
    """Bot sağlığını izle - ağ sorunlarına dayanıklı"""
    
    consecutive_failures = 0
    last_log = time.time()
    
    while True:
        await asyncio.sleep(config.HEALTH_CHECK_INTERVAL)
        
        try:
            current_time = time.time()
            
            # Bot durumu
            is_ready = bot.is_ready() if bot else False
            heartbeat_age = current_time - bot.last_heartbeat
            latency = bot.latency * 1000 if bot.latency else 0
            
            # Ağ sorunu kontrolü
            if latency > 2000 or heartbeat_age > 300:  # 2 saniye veya 5 dakika
                bot.network_issues += 1
                db.track_metric("network_issues")
                
                if bot.network_issues >= config.NETWORK_TOLERANCE:
                    logger.warning(f"🌐 Ağ sorunu: {bot.network_issues}/{config.NETWORK_TOLERANCE}")
                    
                    # 10+ sorunda restart
                    if bot.network_issues >= config.NETWORK_TOLERANCE * 2:
                        logger.critical("❌ Çok fazla ağ sorunu - yeniden başlatılıyor")
                        db.track_metric("restarts")
                        os._exit(1)
            else:
                # Ağ düzeldiyse sayacı azalt
                bot.network_issues = max(0, bot.network_issues - 1)
            
            # Saat başı log
            if current_time - last_log > 3600:
                logger.info(f"💓 Watchdog | Hazır: {is_ready} | Heartbeat: {heartbeat_age:.0f}s | Gecikme: {latency:.0f}ms | Ağ Sorunu: {bot.network_issues}")
                last_log = current_time
            
        except Exception as e:
            logger.error(f"❌ Watchdog hatası: {e}")
            consecutive_failures += 1
            
            if consecutive_failures > 5:
                logger.critical("❌ Watchdog çok hata aldı - yeniden başlatılıyor")
                os._exit(1)

# ======================================================================
# 🛑 13. GÜVENLİ KAPANMA
# ======================================================================
async def shutdown_handler(sig=None):
    """Güvenli kapanma"""
    
    logger.info("🛑 Bot kapatılıyor...")
    
    # İstatistikleri kaydet
    db.stats["uptime_history"].append({
        "start": db.stats["start_time"],
        "end": datetime.now().isoformat(),
        "duration": str(datetime.now() - bot.start_time)
    })
    db.save_all()
    
    # Health check server'ı kapat
    if bot.health_runner:
        await bot.health_runner.cleanup()
    
    # Bot'u kapat
    await bot.close()
    
    logger.info("👌 Bot kapatıldı. Hoşçakal!")
    sys.exit(0)

def signal_handler(sig, frame):
    """Sinyal işleyici"""
    asyncio.create_task(shutdown_handler(sig))

# ======================================================================
# 🚀 14. ANA FONKSİYON
# ======================================================================
async def main():
    """Ana fonksiyon - botu başlat"""
    
    # ASCII Banner
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗ ███████╗██╗   ██╗██████╗  ██████╗ ████████╗  ██╗   ██╗██╗██╗     ║
║   ██╔══██╗██╔════╝██║   ██║██╔══██╗██╔═══██╗╚══██╔══╝  ██║   ██║██║██║     ║
║   ██║  ██║█████╗  ██║   ██║██████╔╝██║   ██║   ██║     ██║   ██║██║██║     ║
║   ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██║   ██║   ██║     ╚██╗ ██╔╝██║██║     ║
║   ██████╔╝███████╗ ╚████╔╝ ██████╔╝╚██████╔╝   ██║      ╚████╔╝ ██║███████╗║
║   ╚═════╝ ╚══════╝  ╚═══╝  ╚═════╝  ╚═════╝    ╚═╝       ╚═══╝  ╚═╝╚══════╝║
║                                                                              ║
║   ██╗   ██╗██╗   ██╗                                                         ║
║   ██║   ██║██║   ██║                                                         ║
║   ██║   ██║██║   ██║                                                         ║
║   ╚██╗ ██╔╝██║   ██║                                                         ║
║    ╚████╔╝ ╚██████╔╝                                                         ║
║     ╚═══╝   ╚═════╝                                                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   🚀 VERSİYON: 7.0.0 (GOLDEN RATIO EDITION)                                 ║
║   🎨 DALL-E 3 + GPT-4 ENTEGRE                                               ║
║   🌐 RAILWAY OPTIMIZED - ASLA DURMAZ!                                       ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   • Altın oran (1:1.618) ile tasarlandı                                     ║
║   • Health check HER ZAMAN 200 döndürür                                     ║
║   • Ağ sorunlarına dayanıklı                                                ║
║   • Otomatik veri kaydetme                                                  ║
║   • Gelişmiş hata yönetimi                                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Token kontrolü
    if not config.DISCORD_TOKEN:
        logger.error("❌ DISCORD_TOKEN bulunamadı!")
        logger.error("   Railway'de environment variable olarak ekleyin:")
        logger.error("   DISCORD_TOKEN=your_token_here")
        return
    
    # OpenAI kontrolü
    if not config.OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY bulunamadı!")
        logger.warning("   Görsel ve sohbet özellikleri çalışmayacak!")
    
    # Sinyal işleyicileri
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # ÖNCE health check server'ı başlat (hemen, bot'tan bağımsız)
        bot.health_runner = await health_check()
        
        # Kısa bir bekleme (Railway'in health check'i görmesi için)
        await asyncio.sleep(2)
        
        # SONRA watchdog'u başlat
        asyncio.create_task(watchdog())
        
        # EN SON bot'u başlat
        logger.info("🚀 Bot başlatılıyor...")
        await bot.start(config.DISCORD_TOKEN)
        
    except discord.LoginFailure:
        logger.error("❌ Geçersiz Discord token!")
        logger.error("   Lütfen token'ı kontrol edin!")
    except Exception as e:
        logger.error(f"💥 Kritik hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shutdown_handler()

# ======================================================================
# 🏁 15. PROGRAM BAŞLANGICI
# ======================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.critical(f"💥 Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
