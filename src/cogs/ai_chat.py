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
        # Limpiamos la URL de posibles espacios o parámetros conflictivos
        raw_db_url = os.getenv("DATABASE_URL", "")
        self.db_url = raw_db_url.split('&channel_binding')[0].strip()

        print(f"--- [INICIO DE CONFIGURACIÓN SHADOWBOT] ---")

        # 1. ALGORITMO DE DETECCIÓN DE MODELO (Solución 404 de ayer)
        try:
            available_models = [
                m.name for m in genai.list_models()
                if 'generateContent' in m.supported_generation_methods
            ]
            flash_models = [m for m in available_models if "flash" in m]
            self.model_name = flash_models[0] if flash_models else 'models/gemini-1.5-flash'
            print(f"✅ IA: Modelo cargado -> {self.model_name}")
        except Exception as e:
            print(f"⚠️ IA: Error listando modelos: {e}")
            self.model_name = 'models/gemini-1.5-flash'

        self.model = genai.GenerativeModel(self.model_name)

        # 2. Inicializar Base de Datos
        if not self.db_url:
            print("❌ DB: DATABASE_URL no encontrada en Secrets.")
        else:
            try:
                self.init_db()
            except Exception as e:
                print(f"❌ DB: Error fatal inicial: {e}")

        print(f"--- [SISTEMA ONLINE] ---")

    def get_db_connection(self):
        """Crea conexión con SSL forzado para Neon."""
        return psycopg2.connect(self.db_url, sslmode='require')

    def init_db(self):
        print("🔍 DB: Verificando conexión a Neon.tech...")
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
            print("✅ DB: Tabla lista y puente establecido.")
            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ DB: Falló la creación de tabla: {e}")
            raise

    def guardar_memoria(self, user_id, role, content):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO memoria_chat (user_id, role, content) VALUES (%s, %s, %s)",
                        (user_id, role, content))
            conn.commit()
            cur.close()
            conn.close()
            print(f"💾 Memoria: {role} guardado.")
        except Exception as e:
            print(f"⚠️ Memoria: Error al guardar: {e}")

    def obtener_historial(self, user_id, limite=6):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT role, content FROM memoria_chat WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                        (user_id, limite))
            filas = cur.fetchall()
            cur.close()
            conn.close()
            # Ordenamos cronológicamente para el prompt
            return [{"role": f[0], "content": f[1]} for f in reversed(filas)]
        except Exception as e:
            print(f"⚠️ Memoria: Error al recuperar: {e}")
            return []

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith('!'):
            return

        # Responder si lo mencionan o es DM
        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                try:
                    user_id = message.author.id
                    # Limpiar menciones del texto
                    prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                    # Cargar recuerdos de Neon
                    historial = self.obtener_historial(user_id)
                    contexto = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in historial])

                    # Sistema de Personalidad ShadowRoot Lab
                    instruccion = (
                        f"SISTEMA: Eres ShadowBot_V1. Creador: ShadowRoot07 (1.92m, heterocromía).\n"
                        f"ESTILO: Cyberpunk, analítico, profesional. Usa bloques de código Python si se pide.\n"
                        f"HISTORIAL RECIENTE:\n{contexto}"
                    )

                    response = self.model.generate_content(f"{instruccion}\n\nUSUARIO: {prompt}")

                    # Guardar nueva interacción
                    self.guardar_memoria(user_id, "usuario", prompt)
                    self.guardar_memoria(user_id, "bot", response.text)

                    await message.reply(response.text)
                except Exception as e:
                    print(f"🔥 Error Crítico: {e}")
                    await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

