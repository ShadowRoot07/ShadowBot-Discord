import os
import discord
import google.generativeai as genai
from discord.ext import commands
import psycopg2
from discord.ext.commands import CooldownMapping, BucketType

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        # Sistema de Cooldown corregido: 1 mensaje cada 5 segundos por usuario
        self._cd = CooldownMapping.from_cooldown(1, 5, BucketType.user)

        # Configuración de base de datos
        base_url = os.getenv("DATABASE_URL", "").split('?')[0]
        self.db_url = f"{base_url}?sslmode=require"

        print(f"--- [SHADOWBOT CORE CONFIG] ---")
        self.model = self.buscar_mejor_modelo_flash()
        self.init_db()
        print(f"--- [SISTEMA ONLINE] ---")

    def buscar_mejor_modelo_flash(self):
        """Busca el modelo 1.5-flash para tener cuotas más altas y gratuitas."""
        try:
            print("🔍 Filtrando modelos con cuota estable...")
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

            for m in modelos:
                if "models/gemini-1.5-flash" == m:
                    print(f"✅ Modelo estable seleccionado: {m}")
                    return genai.GenerativeModel(m)

            for m in modelos:
                if "1.5" in m:
                    return genai.GenerativeModel(m)
        except Exception as e:
            print(f"❌ Error buscando modelos: {e}")

        return genai.GenerativeModel('gemini-1.5-flash')

    def get_db_connection(self):
        return psycopg2.connect(self.db_url)

    def init_db(self):
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
            print("✅ DB: Estructura sincronizada con Neon.")
        except Exception as e:
            print(f"❌ DB ERROR FATAL: {e}")
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
        except Exception as e:
            print(f"⚠️ Error guardando: {e}")

    def obtener_historial(self, user_id):
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT role, content FROM memoria_chat WHERE user_id = %s ORDER BY id DESC LIMIT 10",
                        (user_id,)
                    )
                    return [{"role": f[0], "content": f[1]} for f in reversed(cur.fetchall())]
        except:
            return []

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith('!'): 
            return

        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            # Lógica de Cooldown Corregida
            bucket = self._cd.get_bucket(message)
            retry_after = bucket.update_rate_limit()
            
            if retry_after:
                return await message.reply(f"⏳ ¡Cálmate! Estás escribiendo muy rápido. Espera {round(retry_after, 1)}s.")

            async with message.channel.typing():
                user_id = message.author.id
                prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                historial = self.obtener_historial(user_id)
                contexto = "\n".join([f"{m['role']}: {m['content']}" for m in historial])
                instruccion = f"Eres ShadowBot_V1. Estilo Cyberpunk. Contexto previo:\n{contexto}"

                try:
                    response = self.model.generate_content(f"{instruccion}\n\nUsuario: {prompt}")
                    
                    self.guardar_memoria(user_id, "usuario", prompt)
                    self.guardar_memoria(user_id, "bot", response.text)
                    await message.reply(response.text)
                
                except Exception as e:
                    if "429" in str(e):
                        await message.reply("💤 He agotado mi energía cerebral por ahora (Límite de cuota). Inténtalo en un minuto.")
                    else:
                        await message.reply(f"🔥 Error en los sistemas: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

