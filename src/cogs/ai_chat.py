import os
import discord
import google.generativeai as genai
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2 import OperationalError

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Limpieza profunda de la URL de Neon (evita el error de channel_binding)
        raw_db_url = os.getenv("DATABASE_URL", "")
        self.db_url = raw_db_url.split('?')[0].strip() + "?sslmode=require"

        print(f"--- [INICIO DE CONFIGURACIÓN SHADOWBOT] ---")

        # 1. DETECCIÓN DINÁMICA DE MODELO
        try:
            available_models = [
                m.name for m in genai.list_models()
                if 'generateContent' in m.supported_generation_methods
            ]
            flash_models = [m for m in available_models if "flash" in m]
            self.model_name = flash_models[0] if flash_models else 'models/gemini-1.5-flash'
            print(f"✅ IA: Modelo seleccionado -> {self.model_name}")
        except Exception as e:
            print(f"⚠️ IA: Error listando modelos: {e}")
            self.model_name = 'models/gemini-1.5-flash'

        self.model = genai.GenerativeModel(self.model_name)

        # 2. INICIALIZACIÓN OBLIGATORIA DE DB
        if not self.db_url or "postgresql" not in self.db_url:
            print("❌ DB: DATABASE_URL no es válida o no existe.")
        else:
            self.init_db()

        print(f"--- [SISTEMA SHADOWROOT ONLINE] ---")

    def get_db_connection(self):
        """Intenta conectar a Neon con SSL."""
        return psycopg2.connect(self.db_url)

    def init_db(self):
        """Crea la tabla y lanza error si falla (esto detendrá el bot para debug)."""
        print("🔍 DB: Intentando crear tabla en Neon.tech...")
        conn = None
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS memoria_chat (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            print("✅ DB: ¡TABLA 'memoria_chat' VERIFICADA/CREADA!")
            cur.close()
        except Exception as e:
            print(f"❌ DB: ERROR CRÍTICO EN INICIALIZACIÓN: {e}")
            # Al no capturar el error aquí, el bot fallará y verás el error en GitHub
            raise e 
        finally:
            if conn:
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
            print(f"💾 Memoria: Interacción de {role} guardada.")
        except Exception as e:
            print(f"⚠️ Memoria: No se pudo guardar: {e}")

    def obtener_historial(self, user_id, limite=6):
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
            print(f"⚠️ Memoria: No se pudo recuperar historial: {e}")
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

                    # Recuperar recuerdos de Neon
                    historial = self.obtener_historial(user_id)
                    contexto_memoria = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in historial])

                    instruccion_sistema = (
                        f"SISTEMA: Eres ShadowBot_V1, asistente de ShadowRoot Lab.\n"
                        f"ESTILO: Analítico, Cyberpunk. Responde breve.\n"
                        f"RECUERDOS:\n{contexto_memoria}"
                    )

                    response = self.model.generate_content(f"{instruccion_sistema}\n\nUSUARIO: {prompt_original}")

                    # Guardar en base de datos
                    self.guardar_memoria(user_id, "usuario", prompt_original)
                    self.guardar_memoria(user_id, "bot", response.text)

                    await message.reply(response.text)
                except Exception as e:
                    print(f"🔥 NÚCLEO: Error al procesar: {e}")
                    await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

