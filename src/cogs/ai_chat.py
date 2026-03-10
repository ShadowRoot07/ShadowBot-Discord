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

        # Intentar inicializar la base de datos
        try:
            self.init_db()
            print("✅ Conexión a Neon.tech exitosa.")
        except Exception as e:
            print(f"❌ Error crítico conectando a Neon: {e}")

        self.model = genai.GenerativeModel('gemini-1.5-flash')
        # Ya no usamos self.chat = self.model.start_chat porque ahora la memoria la manejas tú con SQL

    def get_db_connection(self):
        """Crea una conexión con SSL requerido para Neon."""
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
            print(f"⚠️ Error guardando memoria: {e}")

    def obtener_historial(self, user_id, limite=10):
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
            print(f"⚠️ Error recuperando historial: {e}")
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

                    # 1. Recuperar memoria
                    historial = self.obtener_historial(user_id)
                    contexto_memoria = ""
                    for m in historial:
                        role_label = "Sroot" if m['role'] == "usuario" else "Sbot"
                        contexto_memoria += f"{role_label}: {m['content']}\n"

                    # 2. Instrucción de Sistema
                    instruccion_sistema = (
                        f"SISTEMA: Eres ShadowBot_V1 de ShadowRoot Lab.\n"
                        f"MEMORIA DE CONVERSACIÓN:\n{contexto_memoria}\n"
                        f"Responde de forma concisa, Cyberpunk y usa bloques Markdown para código."
                    )

                    response = self.model.generate_content(f"{instruccion_sistema}\n\nUsuario: {prompt_original}")

                    # 3. Guardar en DB
                    self.guardar_memoria(user_id, "usuario", prompt_original)
                    self.guardar_memoria(user_id, "bot", response.text)

                    await message.reply(response.text)
                except Exception as e:
                    await message.channel.send(f"⚠️ Error en mi núcleo: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

