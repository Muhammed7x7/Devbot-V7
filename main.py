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

🔰 Version 7.0 - Railway Edition
👑 Geliştirici modu - DALL-E 3 + GPT-4
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import json
import time
import base64
import signal
from typing import Optional, Dict, List, Any

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from discord import Embed, Color

from openai import OpenAI
from aiohttp import web

=========================

RAILWAY KONFİGÜRASYON

=========================

RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT") is not None
PORT = int(os.getenv("PORT", 8080))
BASE_DIR = "/tmp" if RAILWAY_ENV else "."

=========================

KONFİGÜRASYON

=========================

class Config:
def init(self):
self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
self.OWNER_ID = int(os.getenv('OWNER_ID', '0'))

# Railway uyumlu çalışma alanı  
    self.WORKSPACE_DIR = Path(BASE_DIR) / "workspace"  
    self.DATA_DIR = Path(BASE_DIR) / "data"  
    self.LOGS_DIR = Path(BASE_DIR) / "logs"  
      
    self.WORKSPACE_DIR.mkdir(exist_ok=True)  
    self.DATA_DIR.mkdir(exist_ok=True)  
    self.LOGS_DIR.mkdir(exist_ok=True)

config = Config()

=========================

LOGGING

=========================

logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
handlers=[
logging.FileHandler(config.LOGS_DIR / "bot.log"),
logging.StreamHandler(sys.stdout)
]
)
logger = logging.getLogger("DevBot")

=========================

VERİ YÖNETİMİ

=========================

class DataManager:
def init(self):
self.stats_file = config.DATA_DIR / "stats.json"
self.stats = self._load_stats()

def _load_stats(self):  
    if self.stats_file.exists():  
        try:  
            with open(self.stats_file, 'r') as f:  
                return json.load(f)  
        except:  
            pass  
    return {  
        "start_time": datetime.now().isoformat(),  
        "chats": 0,  
        "images": 0,  
        "codes": 0,  
        "commands": {}  
    }  
  
def save(self):  
    with open(self.stats_file, 'w') as f:  
        json.dump(self.stats, f, indent=2)  
  
def track(self, command: str):  
    self.stats["commands"][command] = self.stats["commands"].get(command, 0) + 1  
    self.save()

db = DataManager()

=========================

OPENAI İSTEMCİSİ

=========================

class OpenAIClient:
def init(self, api_key: str):
self.api_key = api_key
self.client = None
self.chat_model = "gpt-4o-mini"
self.image_model = "dall-e-3"
self.image_history = []

if api_key:  
        try:  
            self.client = OpenAI(api_key=api_key)  
            logger.info("✅ OpenAI bağlantısı kuruldu")  
            logger.info(f"🎨 DALL-E 3 hazır")  
            logger.info(f"💬 GPT-4o-mini hazır")  
        except Exception as e:  
            logger.error(f"OpenAI hatası: {e}")  
  
async def chat(self, message: str, context: list = None) -> str:  
    if not self.client:  
        return "OpenAI API anahtarı gerekli"  
      
    try:  
        messages = [{  
            "role": "system",   
            "content": "Sen bir yardımsever asistan"  
        }]  
          
        if context:  
            for msg in context[-10:]:  
                messages.append(msg)  
          
        messages.append({"role": "user", "content": message})  
          
        response = await asyncio.get_event_loop().run_in_executor(  
            None,  
            lambda: self.client.chat.completions.create(  
                model=self.chat_model,  
                messages=messages,  
                max_tokens=4000,  
                temperature=0.7  
            )  
        )  
          
        return response.choices[0].message.content  
          
    except Exception as e:  
        logger.error(f"AI hatası: {e}")  
        return f"Hata: {str(e)}"  
  
async def generate_code(self, prompt: str, language: str = "python") -> str:  
    if not self.client:  
        return "# API anahtarı gerekli"  
      
    try:  
        system = f"Sen bir {language} uzmanı. Sadece kod üret, açıklama yapma."  
          
        response = await asyncio.get_event_loop().run_in_executor(  
            None,  
            lambda: self.client.chat.completions.create(  
                model=self.chat_model,  
                messages=[  
                    {"role": "system", "content": system},  
                    {"role": "user", "content": prompt}  
                ],  
                max_tokens=4000,  
                temperature=0.2  
            )  
        )  
          
        return response.choices[0].message.content  
          
    except Exception as e:  
        return f"# Hata: {str(e)}"  
  
async def generate_image(self, prompt: str, size: str = "1024x1024") -> dict:  
    if not self.client:  
        raise Exception("OpenAI bağlantısı yok")  
      
    try:  
        logger.info(f"🎨 Görsel üretiliyor: {prompt[:50]}...")  
          
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]  
        if size not in valid_sizes:  
            size = "1024x1024"  
          
        response = await asyncio.get_event_loop().run_in_executor(  
            None,  
            lambda: self.client.images.generate(  
                model=self.image_model,  
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
            "revised_prompt": response.data[0].revised_prompt if hasattr(response.data[0], 'revised_prompt') else prompt  
        }  
          
        self.image_history.append(result)  
        if len(self.image_history) > 20:  
            self.image_history = self.image_history[-20:]  
          
        logger.info(f"✅ Görsel oluşturuldu: {size}")  
        return result  
          
    except Exception as e:  
        logger.error(f"Görsel hatası: {e}")  
        raise Exception(f"DALL-E hatası: {str(e)}")  
  
def get_recent_images(self, limit: int = 5) -> list:  
    return self.image_history[-limit:]

=========================

DİSCORD BOT

=========================

class DevBot(commands.Bot):
def init(self):
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

super().__init__(  
        command_prefix="!",  
        intents=intents,  
        help_command=None  
    )  
      
    self.start_time = datetime.now()  
    self.version = "7.0-railway"  
    self.ai = OpenAIClient(config.OPENAI_API_KEY)  
    self.owner_id = config.OWNER_ID  
    self.last_heartbeat = time.time()  
  
async def setup_hook(self):  
    await self.tree.sync()  
    logger.info(f"{len(self.tree.get_commands())} komut yüklendi")  
  
async def on_ready(self):  
    self.last_heartbeat = time.time()  
    logger.info(f"✅ Bot hazır: {self.user}")  
    logger.info(f"🎨 DALL-E 3 aktif")  
    logger.info(f"💬 GPT-4o-mini aktif")  
      
    await self.change_presence(  
        activity=discord.Activity(  
            type=discord.ActivityType.playing,  
            name="🎨 /image | 💬 /chat | 💻 /code"  
        )  
    )  
  
async def on_message(self, message):  
    if message.author.bot:  
        return  
    self.last_heartbeat = time.time()  
    await self.process_commands(message)

bot = DevBot()

=========================

YARDIMCI FONKSİYONLAR

=========================

def is_owner(interaction: discord.Interaction) -> bool:
if bot.owner_id and interaction.user.id != bot.owner_id:
return False
return True

=========================

GÖRSEL MODAL

=========================

class ImageModal(Modal, title="🎨 Görsel Oluştur"):
prompt = TextInput(
label="Ne görmek istersin?",
style=discord.TextStyle.paragraph,
placeholder="Örnek: Uzaylı bir kedi, neon ışıklar, cyberpunk şehir...",
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
    await image_command(  
        interaction,   
        self.prompt.value,   
        self.size.value if self.size.value else "1024x1024"  
    )

=========================

KOMUTLAR - GÖRSEL

=========================

@bot.tree.command(name="image", description="🎨 Görsel oluştur (DALL-E 3)")
@app_commands.describe(
prompt="Ne görmek istersin?",
size="Boyut (1024x1024, 1792x1024, 1024x1792)"
)
async def image_command(interaction: discord.Interaction, prompt: str, size: str = "1024x1024"):
if not is_owner(interaction):
await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)
return

await interaction.response.defer()  
  
try:  
    await interaction.followup.send(f"🎨 **Oluşturuluyor:** *{prompt[:100]}*")  
      
    result = await bot.ai.generate_image(prompt, size)  
    db.track("image")  
      
    embed = Embed(  
        title="🖼️ DALL-E 3",  
        description=f"**Prompt:** {prompt}",  
        color=0x5865F2,  
        timestamp=datetime.now()  
    )  
      
    embed.set_image(url=result["url"])  
    embed.add_field(name="📐 Boyut", value=result["size"], inline=True)  
      
    if result["revised_prompt"] != prompt:  
        embed.add_field(  
            name="📝 Düzenlenmiş",   
            value=f"```{result['revised_prompt'][:100]}```",   
            inline=False  
        )  
      
    view = View()  
    view.add_item(Button(label="📥 İndir", style=discord.ButtonStyle.success, url=result["url"]))  
    view.add_item(Button(label="🔄 Tekrar", style=discord.ButtonStyle.primary, custom_id=f"again_{prompt[:50]}"))  
      
    await interaction.followup.send(embed=embed, view=view)  
      
except Exception as e:  
    await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.tree.command(name="imagine", description="⚡ Hızlı görsel")
@app_commands.describe(prompt="Ne görmek istersin?")
async def imagine_command(interaction: discord.Interaction, prompt: str):
await image_command(interaction, prompt, "1024x1024")

@bot.tree.command(name="recent", description="📸 Son görseller")
async def recent_command(interaction: discord.Interaction, limit: int = 5):
if not is_owner(interaction):
await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)
return

images = bot.ai.get_recent_images(limit)  
  
if not images:  
    await interaction.response.send_message("📸 Henüz görsel yok")  
    return  
  
embed = Embed(  
    title="📸 Son Görseller",  
    color=0x5865F2  
)  
  
for i, img in enumerate(images, 1):  
    embed.add_field(  
        name=f"{i}. {img['prompt'][:50]}...",  
        value=f"Boyut: {img['size']}",  
        inline=False  
    )  
  
await interaction.response.send_message(embed=embed)

=========================

KOMUTLAR - SOHBET

=========================

@bot.tree.command(name="chat", description="💬 Sohbet et")
@app_commands.describe(message="Mesajınız")
async def chat_command(interaction: discord.Interaction, message: str):
if not is_owner(interaction):
await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)
return

await interaction.response.defer()  
  
try:  
    response = await bot.ai.chat(message)  
    db.track("chat")  
      
    if len(response) > 1900:  
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]  
        for chunk in chunks:  
            await interaction.followup.send(chunk)  
    else:  
        await interaction.followup.send(response)  
          
except Exception as e:  
    await interaction.followup.send(f"❌ Hata: {e}")

=========================

KOMUTLAR - KOD

=========================

@bot.tree.command(name="code", description="💻 Kod oluştur")
@app_commands.describe(
prompt="Ne yapmak istiyorsun?",
language="Programlama dili"
)
async def code_command(interaction: discord.Interaction, prompt: str, language: str = "python"):
if not is_owner(interaction):
await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)
return

await interaction.response.defer()  
  
try:  
    code = await bot.ai.generate_code(prompt, language)  
    db.track("code")  
      
    filename = f"code_{int(time.time())}.{language}"  
    filepath = config.WORKSPACE_DIR / filename  
    filepath.write_text(code)  
      
    if len(code) < 1900:  
        await interaction.followup.send(f"```{language}\n{code}\n```")  
    else:  
        await interaction.followup.send(  
            f"✅ Kod oluşturuldu",  
            file=discord.File(filepath, filename)  
        )  
          
except Exception as e:  
    await interaction.followup.send(f"❌ Hata: {e}")

=========================

KOMUTLAR - SİSTEM

=========================

@bot.tree.command(name="status", description="📊 Bot durumu")
async def status_command(interaction: discord.Interaction):
if not is_owner(interaction):
await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)
return

uptime = datetime.now() - bot.start_time  
hours = int(uptime.total_seconds() / 3600)  
minutes = int((uptime.total_seconds() % 3600) / 60)  
  
embed = Embed(  
    title="📊 Bot Durumu",  
    color=0x5865F2  
)  
  
embed.add_field(name="⏰ Çalışma", value=f"{hours}s {minutes}d", inline=True)  
embed.add_field(name="📊 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)  
embed.add_field(name="💬 Sohbetler", value=db.stats["commands"].get("chat", 0), inline=True)  
embed.add_field(name="🎨 Görseller", value=db.stats["commands"].get("image", 0), inline=True)  
embed.add_field(name="💻 Kodlar", value=db.stats["commands"].get("code", 0), inline=True)  
  
await interaction.response.send_message(embed=embed)

@bot.tree.command(name="menu", description="📋 Ana menü")
async def menu_command(interaction: discord.Interaction):
if not is_owner(interaction):
await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)
return

embed = Embed(  
    title="📋 Ana Menü",  
    description="""  
    🎨 **GÖRSELLER**  
    `/image` - Detaylı görsel  
    `/imagine` - Hızlı görsel  
    `/recent` - Son görseller  
      
    💬 **SOHBET**  
    `/chat` - Sohbet et  
      
    💻 **KOD**  
    `/code` - Kod oluştur  
      
    📊 **SİSTEM**  
    `/status` - Bot durumu  
    """,  
    color=0x5865F2  
)  
  
view = View()  
view.add_item(Button(label="🎨 Görsel", style=discord.ButtonStyle.primary, custom_id="menu_image"))  
view.add_item(Button(label="💬 Sohbet", style=discord.ButtonStyle.success, custom_id="menu_chat"))  
view.add_item(Button(label="📊 Durum", style=discord.ButtonStyle.secondary, custom_id="menu_status"))  
  
await interaction.response.send_message(embed=embed, view=view)

=========================

BUTON İŞLEYİCİLERİ

=========================

@bot.event
async def on_interaction(interaction: discord.Interaction):
if interaction.type == discord.InteractionType.component:
custom_id = interaction.data.get("custom_id", "")

if not is_owner(interaction):  
        await interaction.response.send_message("❌ Yetkiniz yok", ephemeral=True)  
        return  
      
    if custom_id == "menu_image":  
        await interaction.response.send_modal(ImageModal())  
      
    elif custom_id == "menu_chat":  
        modal = Modal(title="💬 Hızlı Sohbet")  
        msg = TextInput(label="Mesajınız", style=discord.TextStyle.paragraph, required=True)  
        modal.add_item(msg)  
          
        async def modal_submit(m_interaction):  
            await chat_command(m_interaction, msg.value)  
          
        modal.on_submit = modal_submit  
        await interaction.response.send_modal(modal)  
      
    elif custom_id == "menu_status":  
        await status_command(interaction)  
      
    elif custom_id.startswith("again_"):  
        prompt = custom_id[6:]  
        await image_command(interaction, prompt, "1024x1024")

=========================

HEALTH CHECK

=========================

async def health_check():
async def handler(request):
if bot.is_ready() and (time.time() - bot.last_heartbeat) < 120:
return web.Response(text="OK")
return web.Response(status=503)

app = web.Application()  
app.router.add_get("/", handler)  
app.router.add_get("/health", handler)  
  
runner = web.AppRunner(app)  
await runner.setup()  
site = web.TCPSite(runner, "0.0.0.0", PORT)  
await site.start()  
logger.info(f"Health check aktif: {PORT}")

=========================

WATCHDOG

=========================

async def watchdog():
while True:
await asyncio.sleep(60)
if time.time() - bot.last_heartbeat > 180:
logger.warning("⚠️ Bot yanıt vermiyor, yeniden başlatılıyor...")
os._exit(1)

=========================

GÜVENLİ KAPANMA

=========================

def shutdown_handler(signum, frame):
logger.info("Kapatılıyor...")
loop = asyncio.get_event_loop()
loop.create_task(bot.close())
time.sleep(2)
sys.exit(0)

=========================

ANA FONKSİYON

=========================

async def main():
print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ██████╗ ███████╗██╗   ██╗██████╗  ██████╗ ████████╗  ║
║   ██╔══██╗██╔════╝██║   ██║██╔══██╗██╔═══██╗╚══██╔══╝  ║
║   ██║  ██║█████╗  ██║   ██║██████╔╝██║   ██║   ██║     ║
║   ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██║   ██║   ██║     ║
║   ██████╔╝███████╗ ╚████╔╝ ██████╔╝╚██████╔╝   ██║     ║
║   ╚═════╝ ╚══════╝  ╚═══╝  ╚═════╝  ╚═══╝    ╚═╝     ║
║                                                          ║
║              RAILWAY EDITION v7.0                       ║
║                 🎨 DALL-E 3 AKTİF                        ║
║                 💬 GPT-4o-mini AKTİF                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")

if not config.DISCORD_TOKEN:  
    print("❌ Discord token gerekli")  
    return  
  
if not config.OPENAI_API_KEY:  
    print("⚠️ OpenAI API anahtarı yok - görsel ve sohbet çalışmaz")  
  
# Sinyal işleyiciler  
signal.signal(signal.SIGINT, shutdown_handler)  
signal.signal(signal.SIGTERM, shutdown_handler)  
  
# Arkaplan görevleri  
asyncio.create_task(health_check())  
asyncio.create_task(watchdog())  
  
try:  
    await bot.start(config.DISCORD_TOKEN)  
except KeyboardInterrupt:  
    logger.info("Kapatılıyor...")  
    await bot.close()  
except Exception as e:  
    logger.error(f"Hata: {e}")  
    await bot.close()

if name == "main":
asyncio.run(main())

Requirements.txt

discord.py>=2.3.0
openai>=1.0.0
aiohttp>=3.9.0

railway.json

{
"$schema": "https://railway.app/railway.schema.json",
"build": {
"builder": "NIXPACKS",
"buildCommand": "pip install -r requirements.txt"
},
"deploy": {
"startCommand": "python main.py",
"healthcheckPath": "/health",
"healthcheckTimeout": 100,
"restartPolicyType": "ON_FAILURE",
"restartPolicyMaxRetries": 10
}
}

Railway kurulum adimlari
