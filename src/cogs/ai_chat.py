import os
import discord
import google.generativeai as genai
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import psycopg2

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.db_url = os.getenv("DATABASE_URL")

        # 1. ALGORITMO DE DETECCIÓN DE MODELO (Solución al 404)
        try:
            available_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            # Priorizamos flash para evitar errores de cuota
            flash_models = [m for m in available_models if "flash" in m]
            self.model_name = flash_models[0] if flash_models else 'models/gemini-1.5-flash'
            print(f"✅ IA detectada: {self.model_name}")
        except Exception as e:
            print(f"⚠️ Error listando modelos: {e}")
            self.model_name = 'models/gemini-1.5-flash'

        self.model = genai.GenerativeModel(self.model_name)

        # 2. Inicializar Base de Datos con SSL
        try:
            self.init_db()
            print("✅ Memoria en Neon.tech lista.")
        except Exception as e:
            print(f"❌ Error en DB: {e}")

    def get_db_connection(self):
        return psycopg2.connect(self.db_url, sslmode='require')

    def init_db(self):
        conn = self.get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS memoria_chat (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()

    def guardar_memoria(self, user_id, role, content):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO memoria_chat (user_id, role, content) VALUES (%s, %s, %s)", 
                        (user_id, role, content))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ No pude guardar en memoria: {e}")

    def obtener_historial(self, user_id, limite=8):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT role, content FROM memoria_chat WHERE user_id = %s ORDER BY id DESC LIMIT %s", 
                        (user_id, limite))
            filas = cur.fetchall()
            cur.close()
            conn.close()
            return [{"role": f[0], "content": f[1]} for f in reversed(filas)]
        except Exception as e:
            return []

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith('!'):
            return

        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                try:
                    user_id = message.author.id
                    prompt_original = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                    # Recuperar memoria
                    historial = self.obtener_historial(user_id)
                    contexto_memoria = "\n".join([f"{m['role']}: {m['content']}" for m in historial])

                    # Instrucción de Sistema con Personalidad y Formato de Código
                    instruccion_sistema = (
                        f"SISTEMA: Eres ShadowBot_V1 de ShadowRoot Lab.\n"
                        f"CONSTRICCIONES: Responde breve, estilo Cyberpunk. Usa bloques de código Markdown con comentarios.\n"
                        f"MEMORIA DE CONVERSACIÓN:\n{contexto_memoria}"
                    )

                    response = self.model.generate_content(f"{instruccion_sistema}\n\nUsuario: {prompt_original}")

                    # Guardar en DB
                    self.guardar_memoria(user_id, "usuario", prompt_original)
                    self.guardar_memoria(user_id, "bot", response.text)

                    await message.reply(response.text)
                except Exception as e:
                    await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

