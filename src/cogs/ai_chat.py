import os
import google.generativeai as genai
from discord.ext import commands

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuración de Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        # Pequeña memoria local para mantener el hilo (opcional)
        self.chat = self.model.start_chat(history=[])

    @commands.Cog.listener()
    async def on_message(self, message):
        # Reglas básicas: No responder a bots y no responder si es un comando (!)
        if message.author.bot or message.content.startswith('!'):
            return

        # Solo responder si mencionan al bot o si es un mensaje directo
        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                try:
                    # Limpiamos la mención del texto para que la IA no se confunda
                    prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').strip()
                    
                    response = self.chat.send_message(
                        f"Eres ShadowBot_V1, un asistente avanzado creado por ShadowRoot07. "
                        f"Responde de forma concisa y profesional a: {prompt}"
                    )
                    
                    await message.reply(response.text)
                except Exception as e:
                    await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

