import os
import discord
import google.generativeai as genai
from discord.ext import commands

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuración de Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # BUSCADOR AUTOMÁTICO DE MODELO
        try:
            # Listamos modelos que soportan 'generateContent'
            available_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            # Prioridad: 1.5-flash, luego pro, luego el primero que aparezca
            if any("1.5-flash" in m for m in available_models):
                self.model_name = [m for m in available_models if "1.5-flash" in m][0]
            elif any("pro" in m for m in available_models):
                self.model_name = [m for m in available_models if "pro" in m][0]
            else:
                self.model_name = available_models[0]
                
            print(f"✅ Inteligencia cargada usando: {self.model_name}")
        except Exception as e:
            print(f"⚠️ No pude listar modelos, usando default: {e}")
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
                    # Limpiamos la mención del bot
                    prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()
                    
                    if not prompt:
                        prompt = "Hola"

                    response = self.chat.send_message(
                        f"Tu nombre es ShadowBot_V1. Fuiste creado por ShadowRoot07. "
                        f"Responde de forma útil y breve a: {prompt}"
                    )

                    await message.reply(response.text)
                except Exception as e:
                    await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

