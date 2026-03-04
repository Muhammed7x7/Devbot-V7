#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 DEEPSEEK-POWERED DISCORD BOT 🚀                       ║
║                         (RAILWAY EDITION - main.py)                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • DeepSeek AI - GÜÇLÜ ve HIZLI!                                            ║
║  • Tamamen ÜCRETSİZ (1M token context)                                      ║
║  • Prefix: !ping, !test, !deepseek, !kod, !sohbet                           ║
║  • Slash: /deepseek, /kod, /durum, /menü                                    ║
║  • Railway + Health Check + Otomatik yeniden başlatma                       ║
║  • Hafıza: Son 50 mesajı hatırlar                                           ║
║  • Owner: sadece belirlenen kişiler kullanabilir                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ======================================================================
# 📦 GEREKLİ KÜTÜPHANELER
# ======================================================================
import os
import sys
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

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
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
        
        # Owner ID'ler (virgülle ayır: 123456789,987654321)
        owner_ids = os.getenv('OWNER_IDS', '')
        self.OWNER_IDS = [int(x) for x in owner_ids.split(',') if x.strip()]
        
        # Dizinler
        self.WORKSPACE_DIR = Path(BASE_DIR) / "workspace"
        self.DATA_DIR = Path(BASE_DIR) / "data"
        self.LOGS_DIR = Path(BASE_DIR) / "logs"
        
        for dir_path in [self.WORKSPACE_DIR, self.DATA_DIR, self.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # DeepSeek ayarları
        self.DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
        self.DEEPSEEK_MODEL = "deepseek-chat"  # veya "deepseek-coder"
        
        # Sistem ayarları
        self.HEALTH_CHECK_INTERVAL = 60  # saniye
        self.MEMORY_LIMIT = 50  # kullanıcı başına maksimum mesaj

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
logger = logging.getLogger("DeepSeekBot")

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
            "deepseek_calls": 0,
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
    
    def track_deepseek(self):
        self.stats["deepseek_calls"] = self.stats.get("deepseek_calls", 0) + 1
        self._save_json(self.stats_file, self.stats)
    
    def add_to_memory(self, user_id: int, role: str, content: str):
        """Kullanıcı mesajlarını hafızada tut"""
        uid = str(user_id)
        if uid not in self.memory:
            self.memory[uid] = []
            self.stats["total_users"] = len(self.memory)
        
        self.memory[uid].append({
            "role": role,
            "content": content,
            "time": time.time()
        })
        
        # Hafıza limiti
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
# 🤖 DEEPSEEK İSTEMCİSİ
# ======================================================================
class DeepSeekClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.available = False
        self.model = config.DEEPSEEK_MODEL
        self.api_url = config.DEEPSEEK_API_URL
        
        if api_key:
            self._test_connection()
        else:
            logger.warning("⚠️ DEEPSEEK_API_KEY bulunamadı!")
    
    def _test_connection(self):
        """API bağlantısını test et"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            test_data = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Merhaba"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                self.api_url,
                json=test_data,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                self.available = True
                logger.info("✅ DeepSeek API bağlantısı başarılı!")
                logger.info(f"   • Model: {self.model}")
                logger.info(f"   • Context: 1M token (ÜCRETSİZ!)")
            else:
                logger.error(f"❌ DeepSeek API hatası: {response.status_code}")
                logger.error(f"   {response.text}")
                
        except Exception as e:
            logger.error(f"❌ DeepSeek bağlantı hatası: {e}")
    
    async def chat(self, message: str, context: list = None, system_prompt: str = None) -> str:
        """DeepSeek ile sohbet et"""
        if not self.available:
            return "❌ DeepSeek API bağlantısı yok! Lütfen DEEPSEEK_API_KEY ekleyin."
        
        try:
            # Mesajları hazırla
            messages = []
            
            # Sistem promptu
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": "Sen yardımsever bir AI asistanısın. Türkçe yanıt ver."})
            
            # Context varsa ekle
            if context:
                for msg in context[-10:]:  # Son 10 mesajı al
                    role = "assistant" if msg['role'] == 'assistant' else "user"
                    messages.append({"role": role, "content": msg['content']})
            
            # Yeni mesajı ekle
            messages.append({"role": "user", "content": message})
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4000,
                "top_p": 0.9,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=60
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                db.track_deepseek()
                
                try:
                    return result['choices'][0]['message']['content']
                except (KeyError, IndexError) as e:
                    return f"❌ Yanıt formatı hatası: {str(e)}"
            else:
                error_msg = response.json() if response.text else "Bilinmeyen hata"
                return f"❌ API Hatası ({response.status_code}): {error_msg}"
                
        except Exception as e:
            return f"❌ Bağlantı hatası: {str(e)}"
    
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """Kod oluştur - DeepSeek Coder özelliği"""
        if not self.available:
            return "# DeepSeek API bağlantısı yok!"
        
        try:
            system_prompt = f"""Sen bir kod uzmanısın. Sadece {language} kodu yaz, açıklama ekleme.
Kodlar çalışır durumda ve hata ayıklanmış olmalı.
Türkçe yorum satırları ekle."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{prompt}\n\nKod:"}
            ]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-coder",  # Kod için özel model
                "messages": messages,
                "temperature": 0.3,  # Daha deterministik
                "max_tokens": 8000,
                "top_p": 0.95
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=60
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                db.track_deepseek()
                
                try:
                    code = result['choices'][0]['message']['content']
                    
                    # Markdown temizliği
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
class DeepSeekBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
        self.start_time = datetime.now()
        self.deepseek = DeepSeekClient(config.DEEPSEEK_API_KEY)
        self.owner_ids = config.OWNER_IDS
        self.last_heartbeat = time.time()
        
        logger.info(f"🤖 DeepSeek: {'✅ AKTİF' if self.deepseek.available else '❌ PASIF'}")
    
    async def setup_hook(self):
        """Bot başlangıcında çalışır"""
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
            activity=discord.Game("🔥 DeepSeek AI | !help"),
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
        """Kullanıcı bot sahibi mi?"""
        # Ana owner ID'yi otomatik ekle
        main_owner = 1298163612189597716  # ekincimhuseyn
        return user_id in self.owner_ids or user_id == main_owner

bot = DeepSeekBot()

# ======================================================================
# 📝 MODAL SINIFLARI
# ======================================================================
class DeepSeekModal(Modal, title="💬 DeepSeek ile Sohbet"):
    mesaj = TextInput(
        label="Mesajınız",
        style=discord.TextStyle.paragraph,
        placeholder="Ne sormak istersiniz?",
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await deepseek_slash(interaction, self.mesaj.value)

class KodModal(Modal, title="💻 Kod Oluştur (DeepSeek)"):
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
        color=0x4D6BFE,  # DeepSeek mavisi
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Sunucular", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Kullanıcılar", value=len(bot.users), inline=True)
    embed.add_field(name="🤖 DeepSeek", value="✅ Aktif" if bot.deepseek.available else "❌ Pasif", inline=True)
    embed.add_field(name="💬 Toplam Mesaj", value=db.stats.get("total_messages", 0), inline=True)
    embed.add_field(name="📊 API Kullanım", value=f"{db.stats.get('deepseek_calls', 0)} istek", inline=True)
    
    await ctx.send(embed=embed)
    db.track_command("test")

@bot.command(name="help")
async def help_command(ctx):
    """!help - Yardım menüsü"""
    embed = Embed(
        title="📋 DeepSeek Bot Komutları",
        description="🔥 **1M token context - ÜCRETSİZ!**",
        color=0x4D6BFE
    )
    
    embed.add_field(
        name="📝 Prefix Komutlar (!)",
        value="`!ping` - Bot test et\n"
              "`!test` - Bot durumu\n"
              "`!help` - Bu menü\n"
              "`!deepseek <mesaj>` - DeepSeek'e sor\n"
              "`!sohbet <mesaj>` - DeepSeek ile sohbet\n"
              "`!kod <dil> <açıklama>` - Kod oluştur\n"
              "`!temizle` - Hafızanı temizle",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Slash Komutlar (/)",
        value="`/deepseek` - Sohbet et\n"
              "`/kod` - Kod oluştur\n"
              "`/durum` - Bot durumu\n"
              "`/menü` - Ana menü\n"
              "`/hafıza` - Hafızanı görüntüle",
        inline=False
    )
    
    embed.set_footer(text=f"{bot.user.name} • DeepSeek AI ile güçlendirildi")
    
    await ctx.send(embed=embed)
    db.track_command("help")

@bot.command(name="deepseek")
async def deepseek_command(ctx, *, mesaj: str):
    """!deepseek <mesaj> - DeepSeek'e sor"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        return
    
    async with ctx.typing():
        try:
            if not bot.deepseek.available:
                await ctx.send("❌ DeepSeek API bağlantısı yok!")
                return
            
            # Hafızayı al
            memory = db.get_memory(ctx.author.id)
            
            # DeepSeek'e sor
            response = await bot.deepseek.chat(mesaj, memory)
            
            # Hafızaya kaydet
            db.add_to_memory(ctx.author.id, "user", mesaj)
            db.add_to_memory(ctx.author.id, "assistant", response[:500])
            db.track_command("deepseek")
            
            # Uzun mesajları böl
            if len(response) > 1900:
                for i in range(0, len(response), 1900):
                    await ctx.send(response[i:i+1900])
            else:
                await ctx.send(response)
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name="sohbet")
async def sohbet_command(ctx, *, mesaj: str):
    """!sohbet <mesaj> - DeepSeek ile sohbet et"""
    await deepseek_command(ctx, mesaj=mesaj)

@bot.command(name="kod")
async def kod_command(ctx, dil: str = "python", *, aciklama: str):
    """!kod <dil> <açıklama> - Kod oluştur"""
    if not bot.is_owner(ctx.author.id):
        await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        return
    
    async with ctx.typing():
        try:
            if not bot.deepseek.available:
                await ctx.send("❌ DeepSeek API bağlantısı yok!")
                return
            
            # Kodu oluştur
            code = await bot.deepseek.generate_code(aciklama, dil)
            db.track_command("kod")
            
            # Dosyaya kaydet
            filename = f"kod_{int(time.time())}.{dil}"
            filepath = config.WORKSPACE_DIR / filename
            filepath.write_text(code, encoding='utf-8')
            
            # Embed oluştur
            embed = Embed(
                title=f"💻 {dil.capitalize()} Kodu",
                description=f"**İstek:** {aciklama[:200]}",
                color=0x4D6BFE
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

@bot.tree.command(name="deepseek", description="💬 DeepSeek ile sohbet et")
@app_commands.describe(mesaj="Ne sormak istersin?")
async def deepseek_slash(interaction: discord.Interaction, mesaj: str):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        if not bot.deepseek.available:
            await interaction.followup.send("❌ DeepSeek API bağlantısı yok!")
            return
        
        memory = db.get_memory(interaction.user.id)
        response = await bot.deepseek.chat(mesaj, memory)
        
        db.add_to_memory(interaction.user.id, "user", mesaj)
        db.add_to_memory(interaction.user.id, "assistant", response[:500])
        db.track_command("slash_deepseek")
        
        embed = Embed(
            title="💬 DeepSeek Sohbet",
            description=f"**{interaction.user.name}** sordu:",
            color=0x4D6BFE,
            timestamp=datetime.now()
        )
        embed.add_field(name="📤 Siz", value=f"```{mesaj[:500]}```", inline=False)
        embed.add_field(name="📥 DeepSeek", value=f"{response[:1500]}", inline=False)
        embed.set_footer(text=f"1M token context • ÜCRETSİZ!")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="kod", description="💻 Kod oluştur (DeepSeek Coder)")
@app_commands.describe(prompt="Ne yapmak istiyorsun?", dil="Programlama dili")
async def kod_slash(interaction: discord.Interaction, prompt: str, dil: str = "python"):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        if not bot.deepseek.available:
            await interaction.followup.send("❌ DeepSeek API bağlantısı yok!")
            return
        
        code = await bot.deepseek.generate_code(prompt, dil)
        db.track_command("slash_kod")
        
        filename = f"kod_{int(time.time())}.{dil}"
        filepath = config.WORKSPACE_DIR / filename
        filepath.write_text(code, encoding='utf-8')
        
        embed = Embed(
            title=f"💻 {dil.capitalize()} Kodu",
            description=f"**İstek:** {prompt[:200]}",
            color=0x4D6BFE
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
        color=0x4D6BFE,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="⏰ Çalışma Süresi", value=f"{saat}s {dakika}d", inline=True)
    embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Sunucular", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Kullanıcılar", value=len(bot.users), inline=True)
    embed.add_field(name="🤖 DeepSeek", value="✅ Aktif" if bot.deepseek.available else "❌ Pasif", inline=True)
    embed.add_field(name="📊 API Kullanım", value=f"{db.stats.get('deepseek_calls', 0)} istek", inline=True)
    
    await interaction.response.send_message(embed=embed)
    db.track_command("slash_durum")

@bot.tree.command(name="menü", description="📋 Ana menü")
async def menu_slash(interaction: discord.Interaction):
    if not bot.is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    
    embed = Embed(
        title="📋 DeepSeek Bot Menüsü",
        description="🔥 **1M token context - ÜCRETSİZ!**",
        color=0x4D6BFE
    )
    
    embed.add_field(name="💬 /deepseek", value="Sohbet et", inline=False)
    embed.add_field(name="💻 /kod", value="Kod oluştur (DeepSeek Coder)", inline=False)
    embed.add_field(name="📊 /durum", value="Bot durumu", inline=False)
    embed.add_field(name="🧹 /hafıza", value="Hafızanı görüntüle/temizle", inline=False)
    
    view = View()
    view.add_item(Button(label="💬 Sohbet", style=discord.ButtonStyle.primary, custom_id="menu_deepseek"))
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
        color=0x4D6BFE
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
        
        if custom_id == "menu_deepseek":
            await interaction.response.send_modal(DeepSeekModal())
        
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
                "deepseek": bot.deepseek.available,
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
            
            if heartbeat_age > 300:  # 5 dakika
                logger.warning(f"⚠️ Heartbeat yaşlı: {heartbeat_age:.0f}s")
            
            if heartbeat_age > 900:  # 15 dakika
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
║   🔥 DEEPSEEK DISCORD BOT - RAILWAY EDITION                ║
║   ✨ 1M token context - TAMAMEN ÜCRETSİZ!                   ║
║                                                              ║
║   ✅ Prefix: !ping, !test, !help, !deepseek, !kod           ║
║   ✅ Slash: /deepseek, /kod, /durum, /menü, /hafıza         ║
║   ✅ DeepSeek Coder: Profesyonel kod üretimi                ║
║   ✅ Health Check: Her zaman 200 döndürür                   ║
║   ✅ Watchdog: Otomatik yeniden başlatma                    ║
║   ✅ Hafıza: Son 50 mesajı hatırlar                         ║
║   ✅ Owner Kontrolü: Sadece yetkililer kullanabilir         ║
║   ✅ ekincimhuseyn                                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Token kontrolü
    if not config.DISCORD_TOKEN:
        logger.error("❌ DISCORD_TOKEN bulunamadı!")
        return
    
    if not config.DEEPSEEK_API_KEY:
        logger.warning("⚠️ DEEPSEEK_API_KEY bulunamadı! Bot çalışmayacak.")
        return
    
    # Servisleri başlat
    asyncio.create_task(health_check())
    asyncio.create_task(watchdog())
    
    logger.info("🚀 Bot başlatılıyor...")
    
    try:
        await bot.start(config.DISCORD_TOKEN)
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
