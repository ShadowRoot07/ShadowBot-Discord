import os
import discord
import google.generativeai as genai
from discord.ext import commands
import psycopg2
import re
from discord.ext.commands import CooldownMapping, BucketType

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self._cd = CooldownMapping.from_cooldown(1, 5, BucketType.user)
        
        # Configuración de base de datos
        base_url = os.getenv("DATABASE_URL", "").split('?')[0]
        self.db_url = f"{base_url}?sslmode=require"
        
        # Inicialización de sistemas
        self.model = self.obtener_modelo_dinamico()
        self.init_db()
        print(f"--- [SHADOWBOT CORE READY] ---")

    def obtener_modelo_dinamico(self):
        """Busca dinámicamente el mejor modelo Gemini gratuito disponible."""
        try:
            modelos_disponibles = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            for m in modelos_disponibles:
                if "1.5-flash" in m and "latest" in m:
                    return genai.GenerativeModel(m)
            
            for m in modelos_disponibles:
                if "flash" in m:
                    return genai.GenerativeModel(m)
        except:
            pass
        return genai.GenerativeModel('gemini-1.5-flash')

    def get_db_connection(self):
        return psycopg2.connect(self.db_url)

    def init_db(self):
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''CREATE TABLE IF NOT EXISTS memoria_chat (
                        id SERIAL PRIMARY KEY, 
                        user_id BIGINT, 
                        role TEXT, 
                        content TEXT, 
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );''')
                    conn.commit()
        except Exception as e:
            print(f"❌ DB ERROR: {e}")

    def guardar_memoria(self, user_id, role, content):
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO memoria_chat (user_id, role, content) VALUES (%s, %s, %s)", (user_id, role, content))
                    conn.commit()
        except Exception as e: 
            print(f"⚠️ Error guardando memoria: {e}")

    def obtener_historial(self, user_id):
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT role, content FROM memoria_chat WHERE user_id = %s ORDER BY id DESC LIMIT 10", (user_id,))
                    return [{"role": f[0], "content": f[1]} for f in reversed(cur.fetchall())]
        except: 
            return []

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith('!'): 
            return

        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            bucket = self._cd.get_bucket(message)
            retry_after = bucket.update_rate_limit()
            if retry_after: 
                return await message.reply(f"⏳ Espera {round(retry_after, 1)}s.")

            async with message.channel.typing():
                user_id = message.author.id
                raw_content = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()

                # --- Lógica de Scraping Automático ---
                urls = re.findall(r'(https?://\S+)', raw_content)
                contexto_web = ""
                
                if urls:
                    scraper = self.bot.get_cog('WebScraper')
                    if scraper:
                        datos = await scraper.extraer_contenido(urls[0])
                        if "error" not in datos:
                            contexto_web = f"\n[DATOS EXTRAÍDOS DE LA RED]\nSitio: {datos['titulo']}\nContenido: {datos['texto']}\n"

                historial = self.obtener_historial(user_id)
                memoria_str = "\n".join([f"{m['role']}: {m['content']}" for m in historial])
                
                instruccion = (
                    f"Eres ShadowBot_V1. Estilo Cyberpunk Verde Neón. "
                    f"Contexto previo: {memoria_str}\n"
                    f"{contexto_web}"
                    f"Instrucción: Sé conciso pero técnico. Si el texto es muy largo, resúmelo."
                )

                try:
                    response = self.model.generate_content(f"{instruccion}\n\nUsuario: {raw_content}")
                    respuesta_final = response.text

                    # --- CORRECCIÓN DE LÍMITE DE DISCORD ---
                    if len(respuesta_final) > 1950:
                        respuesta_final = respuesta_final[:1950] + "\n\n*(Transmisión cortada por exceso de datos...)*"

                    self.guardar_memoria(user_id, "usuario", raw_content)
                    self.guardar_memoria(user_id, "bot", respuesta_final)
                    await message.reply(respuesta_final)
                except Exception as e:
                    await message.reply(f"🔥 Error en la matriz de IA: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

