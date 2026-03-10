import os
import discord
import google.generativeai as genai
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import psycopg2 # <--- Para la base de datos

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.db_url = os.getenv("DATABASE_URL")
        
        # Inicializar Base de Datos
        self.init_db()

        # Configuración de modelo (igual que antes)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.chat = self.model.start_chat(history=[])

    def init_db(self):
        """Crea la tabla de memoria si no existe en Neon."""
        conn = psycopg2.connect(self.db_url)
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
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        cur.execute("INSERT INTO memoria_chat (user_id, role, content) VALUES (%s, %s, %s)", 
                    (user_id, role, content))
        conn.commit()
        cur.close()
        conn.close()

    def obtener_historial(self, user_id, limite=10):
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        cur.execute("SELECT role, content FROM memoria_chat WHERE user_id = %s ORDER BY id DESC LIMIT %s", 
                    (user_id, limite))
        filas = cur.fetchall()
        cur.close()
        conn.close()
        # Los devolvemos en orden cronológico (del más viejo al más nuevo)
        return [{"role": f[0], "content": f[1]} for f in reversed(filas)]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith('!'):
            return

        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                try:
                    user_id = message.author.id
                    prompt_original = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                    # 1. Recuperar memoria del usuario
                    historial = self.obtener_historial(user_id)
                    contexto_memoria = "\n".join([f"{m['role']}: {m['content']}" for m in historial])

                    # 2. Instrucción de Sistema
                    instruccion_sistema = (
                        f"SISTEMA: Eres ShadowBot_V1. Tienes acceso a la memoria de ShadowRoot Lab.\n"
                        f"MEMORIA RECIENTE:\n{contexto_memoria}\n"
                        f"Crea código en bloques Markdown. Responde con estilo Cyberpunk."
                    )

                    response = self.model.generate_content(f"{instruccion_sistema}\nUsuario: {prompt_original}")

                    # 3. Guardar en la base de datos (lo que dijiste tú y lo que dijo él)
                    self.guardar_memoria(user_id, "usuario", prompt_original)
                    self.guardar_memoria(user_id, "bot", response.text)

                    await message.reply(response.text)
                except Exception as e:
                    await message.channel.send(f"⚠️ Error en mi memoria: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

