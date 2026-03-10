import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Cargamos variables de entorno (.env o Secrets de GitHub)
load_dotenv()

class ShadowBot(commands.Bot):
    def __init__(self):
        # Configuramos los permisos (Intents)
        intents = discord.Intents.default()
        intents.message_content = True  # Permiso para leer mensajes
        intents.members = True          # Permiso para ver miembros
        
        super().__init__(
            command_prefix='!', 
            intents=intents, 
            help_command=None
        )

    async def setup_hook(self):
        """Se ejecuta antes de que el bot se conecte a Discord."""
        print(f"--- Iniciando ShadowBot_V1 ---")
        try:
            # Cargamos el módulo de IA
            await self.load_extension('src.cogs.ai_chat')
            print("✅ Módulo AI_Chat cargado correctamente.")
        except Exception as e:
            print(f"❌ Error al cargar AI_Chat: {e}")

    async def on_ready(self):
        """Se ejecuta cuando el bot ya está en línea."""
        print(f'✅ Conexión establecida como: {self.user.name}')
        print(f'🆔 ID del Bot: {self.user.id}')
        
        # Estado personalizado en Discord
        await self.change_presence(
            activity=discord.Game(name="!help | ShadowRoot Lab")
        )

# Instanciamos el bot para que main.py lo use
bot = ShadowBot()

