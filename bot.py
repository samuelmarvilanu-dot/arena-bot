import discord
import os
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN", "")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.filas",
    "cogs.mediadores",
    "cogs.partidas",
    "cogs.economia",
    "cogs.central",
    "cogs.apostas",
    "cogs.ranking",
    "cogs.admin",
]

@bot.event
async def on_ready():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Módulo carregado: {cog}")
        except Exception as e:
            print(f"❌ Erro ao carregar {cog}: {e}")
    await bot.tree.sync()
    print(f"\n🤖 Bot online como {bot.user}")
    print(f"📡 Servidores: {len(bot.guilds)}")

bot.run(TOKEN)
