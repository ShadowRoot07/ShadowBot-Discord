import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class ShadowBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents, help_command=None)

        # ... (mismo código inicial de src/bot.py)

    async def setup_hook(self):
        print(f"--- Cargando módulos para {self.user} ---")
        # Cargamos el archivo de IA
        await self.load_extension('src.cogs.ai_chat')
        print("✅ Módulo AI_Chat cargado.")


    async def on_ready(self):
        print(f'✅ Sistema operativo: {self.user.name} (ID: {self.user.id})')
        await self.change_presence(activity=discord.Game(name="!help | ShadowRoot Lab"))

bot = ShadowBot()

