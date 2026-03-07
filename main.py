import discord
from discord.ext import commands
import requests
import asyncio
import os
import json
import time
from aiohttp import web

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS","").split(",") if x]

# ==============================
# MEMORY SYSTEM
# ==============================

memory = {}

def add_memory(user, role, text):

    uid = str(user)

    if uid not in memory:
        memory[uid] = []

    memory[uid].append({
        "role": role,
        "content": text
    })

    if len(memory[uid]) > 20:
        memory[uid] = memory[uid][-20:]

def get_memory(user):
    return memory.get(str(user), [])

def clear_memory(user):
    memory[str(user)] = []

# ==============================
# GROK CLIENT
# ==============================

class GrokClient:

    def __init__(self):
        self.url = "https://grok.com/api/chat"

    async def chat(self, message):

        try:

            payload = {
                "messages":[
                    {"role":"user","content":message}
                ]
            }

            loop = asyncio.get_event_loop()

            r = await loop.run_in_executor(
                None,
                lambda: requests.post(self.url,json=payload,timeout=30)
            )

            data = r.json()

            return data.get("response","No response")

        except Exception as e:
            return str(e)

grok = GrokClient()

# ==============================
# DISCORD BOT
# ==============================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

start_time = time.time()

# ==============================
# READY
# ==============================

@bot.event
async def on_ready():

    print("Bot ready:", bot.user)

    await bot.change_presence(
        activity=discord.Game("Grok AI 🤖")
    )

# ==============================
# CHAT
# ==============================

@bot.command()
async def chat(ctx, *, message):

    if ctx.author.id not in OWNER_IDS:
        return await ctx.send("yetki yok")

    async with ctx.typing():

        add_memory(ctx.author.id,"user",message)

        response = await grok.chat(message)

        add_memory(ctx.author.id,"assistant",response)

        if len(response) > 1900:

            for i in range(0,len(response),1900):
                await ctx.send(response[i:i+1900])

        else:

            await ctx.send(response)

# ==============================
# CODE GENERATOR
# ==============================

@bot.command()
async def code(ctx, language="python", *, prompt=""):

    if ctx.author.id not in OWNER_IDS:
        return await ctx.send("yetki yok")

    async with ctx.typing():

        q = f"write {language} code: {prompt}"

        response = await grok.chat(q)

        await ctx.send(f"```{language}\n{response}\n```")

# ==============================
# IMAGE PROMPT
# ==============================

@bot.command()
async def image(ctx, *, prompt):

    async with ctx.typing():

        q = f"write a detailed image prompt for: {prompt}"

        response = await grok.chat(q)

        embed = discord.Embed(
            title="AI Image Prompt",
            description=response
        )

        await ctx.send(embed=embed)

# ==============================
# STATUS
# ==============================

@bot.command()
async def status(ctx):

    uptime = int(time.time() - start_time)

    embed = discord.Embed(
        title="Bot Status"
    )

    embed.add_field(
        name="Ping",
        value=f"{round(bot.latency*1000)}ms"
    )

    embed.add_field(
        name="Uptime",
        value=f"{uptime}s"
    )

    embed.add_field(
        name="Servers",
        value=len(bot.guilds)
    )

    await ctx.send(embed=embed)

# ==============================
# CLEAR MEMORY
# ==============================

@bot.command()
async def clear(ctx):

    clear_memory(ctx.author.id)

    await ctx.send("memory cleared")

# ==============================
# HEALTH SERVER
# ==============================

async def health():

    async def handler(request):

        return web.Response(text="alive")

    app = web.Application()

    app.router.add_get("/", handler)
    app.router.add_get("/health", handler)

    port = int(os.getenv("PORT",8080))

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(runner,"0.0.0.0",port)

    await site.start()

# ==============================
# MAIN
# ==============================

async def main():

    asyncio.create_task(health())

    await bot.start(DISCORD_TOKEN)

asyncio.run(main())
