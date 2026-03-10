import os
import discord
import google.generativeai as genai
from discord.ext import commands

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuración de Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # BUSCADOR DE MODELOS GRATUITOS (FLASH)
        try:
            available_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            # Priorizamos 'flash' porque es el que tiene cuota gratuita real y estable
            # Evitamos los modelos 'pro' o '2.5' que suelen dar el error de quota=0
            flash_models = [m for m in available_models if "flash" in m]
            
            if flash_models:
                # Usamos el más reciente de los flash disponibles
                self.model_name = flash_models[0]
            else:
                # Si no hay flash, usamos el estándar básico
                self.model_name = 'models/gemini-1.5-flash'
                
            print(f"✅ Inteligencia cargada usando modelo gratuito: {self.model_name}")
        except Exception as e:
            print(f"⚠️ No pude listar modelos, forzando flash: {e}")
            self.model_name = 'models/gemini-1.5-flash'

        self.model = genai.GenerativeModel(self.model_name)
        self.chat = self.model.start_chat(history=[])

    @commands.Cog.listener()
    async def on_message(self, message):
        # No responder a otros bots ni a comandos
        if message.author.bot or message.content.startswith('!'):
            return

        # Responder si mencionan al bot o es DM
        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                try:
                    # Limpiamos menciones (ambos formatos de Discord)
                    prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()
                    
                    if not prompt:
                        prompt = "Hola"

                    response = self.chat.send_message(
                        f"Tu nombre es ShadowBot_V1. Creado por ShadowRoot07. "
                        f"Responde de forma breve y profesional a: {prompt}"
                    )

                    await message.reply(response.text)
                except Exception as e:
                    # Si vuelve a dar error de cuota, avisamos de forma amigable
                    if "RESOURCE_EXHAUSTED" in str(e):
                        await message.channel.send("⚠️ Mi cerebro gratuito está descansando un momento (límite de cuota). Inténtalo en unos segundos.")
                    else:
                        await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

