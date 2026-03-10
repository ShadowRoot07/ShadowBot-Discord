import os
import discord
import google.generativeai as genai
from discord.ext import commands
import psycopg2
from psycopg2 import OperationalError

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Limpiamos la URL por si quedó algún residuo de parámetros conflictivos
        raw_db_url = os.getenv("DATABASE_URL", "")
        self.db_url = raw_db_url.split('?')[0].strip() + "?sslmode=require"

        print(f"--- [INICIO DE CONFIGURACIÓN SHADOWBOT] ---")

        # 1. DETECCIÓN DINÁMICA DE MODELO (Solución 404)
        try:
            available_models = [
                m.name for m in genai.list_models()
                if 'generateContent' in m.supported_generation_methods
            ]
            flash_models = [m for m in available_models if "flash" in m]
            self.model_name = flash_models[0] if flash_models else 'models/gemini-1.5-flash'
            print(f"✅ IA: Modelo cargado -> {self.model_name}")
        except Exception as e:
            print(f"⚠️ IA: Error detectando modelos: {e}")
            self.model_name = 'models/gemini-1.5-flash'

        self.model = genai.GenerativeModel(self.model_name)

        # 2. INICIALIZACIÓN DE BASE DE DATOS
        if not self.db_url or "postgresql" not in self.db_url:
            print("❌ DB: DATABASE_URL no es válida. Revisa tus Secrets.")
        else:
            self.init_db()

        print(f"--- [SISTEMA ONLINE] ---")

    def get_db_connection(self):
        """Conexión limpia con SSL."""
        return psycopg2.connect(self.db_url)

    def init_db(self):
        """Asegura que la tabla exista antes de arrancar."""
        print("🔍 DB: Verificando tabla en Neon.tech...")
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
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
            print("✅ DB: Estructura de memoria verificada.")
        except Exception as e:
            print(f"❌ DB ERROR CRÍTICO: {e}")
            # Mantenemos el raise para ver el error real en GitHub Actions
            raise e

    def guardar_memoria(self, user_id, role, content):
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO memoria_chat (user_id, role, content) VALUES (%s, %s, %s)",
                        (user_id, role, content)
                    )
                    conn.commit()
            print(f"💾 Memoria: {role} guardado correctamente.")
        except Exception as e:
            print(f"⚠️ Memoria: Error al guardar: {e}")

    def obtener_historial(self, user_id, limite=10):
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT role, content FROM memoria_chat WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                        (user_id, limite)
                    )
                    filas = cur.fetchall()
            # Invertimos para que el historial sea cronológico (viejo -> nuevo)
            return [{"role": f[0], "content": f[1]} for f in reversed(filas)]
        except Exception as e:
            print(f"⚠️ Memoria: Error al recuperar historial: {e}")
            return []

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith('!'):
            return

        # Responder a menciones o MD
        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                try:
                    user_id = message.author.id
                    prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                    # Recuperar contexto de Neon.tech
                    historial = self.obtener_historial(user_id)
                    contexto_memoria = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in historial])

                    # Personalidad ShadowRoot Lab + Inyección de contexto
                    instruccion_sistema = (
                        f"SISTEMA: Eres ShadowBot_V1. Creador: ShadowRoot07.\n"
                        f"CONSTRICCIONES: Estilo Cyberpunk, respuestas breves y técnicas.\n"
                        f"CONTEXTO DE CONVERSACIÓN ANTERIOR:\n{contexto_memoria}\n"
                        f"--- FIN DEL CONTEXTO ---"
                    )

                    response = self.model.generate_content(f"{instruccion_sistema}\n\nUSUARIO: {prompt}")

                    # Guardar la interacción actual para que no se olvide en el próximo mensaje
                    self.guardar_memoria(user_id, "usuario", prompt)
                    self.guardar_memoria(user_id, "bot", response.text)

                    await message.reply(response.text)
                except Exception as e:
                    print(f"🔥 NÚCLEO: Error procesando mensaje: {e}")
                    await message.channel.send(f"⚠️ Error en mi núcleo cerebral: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

