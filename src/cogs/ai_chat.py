import os
import discord
import google.generativeai as genai
from discord.ext import commands
import psycopg2

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        # Usamos la URL tal cual, solo aseguramos el modo SSL
        base_url = os.getenv("DATABASE_URL", "").split('?')[0]
        self.db_url = f"{base_url}?sslmode=require"

        print(f"--- [SHADOWBOT CORE CONFIG] ---")
        
        # 1. Configurar IA
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 2. Forzar Base de Datos (Si falla aquí, el bot no encenderá)
        self.init_db()
        print(f"--- [SISTEMA ONLINE] ---")

    def get_db_connection(self):
        return psycopg2.connect(self.db_url)

    def init_db(self):
        """Crea la tabla. Si hay error, detiene el bot para que lo veas en 'gh run watch'."""
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
            raise e # Esto hace que falle el Action y lo veas en Termux

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
        if message.author.bot or message.content.startswith('!'): return

        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                user_id = message.author.id
                prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                # Recuperar historial real de la DB
                historial = self.obtener_historial(user_id)
                contexto = "\n".join([f"{m['role']}: {m['content']}" for m in historial])

                instruccion = f"Eres ShadowBot_V1. Estilo Cyberpunk. Contexto previo:\n{contexto}"
                
                try:
                    response = self.model.generate_content(f"{instruccion}\n\nUsuario: {prompt}")
                    
                    # GUARDAR AMBOS EN LA DB (Vital)
                    self.guardar_memoria(user_id, "usuario", prompt)
                    self.guardar_memoria(user_id, "bot", response.text)
                    
                    await message.reply(response.text)
                except Exception as e:
                    await message.reply(f"🔥 Error: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

