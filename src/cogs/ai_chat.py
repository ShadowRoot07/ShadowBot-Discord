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
        
        # Selección de modelo ultra-estable
        self.model = self.obtener_modelo_dinamico()
        self.init_db()
        print(f"--- [SHADOWBOT CORE READY] ---")

    def obtener_modelo_dinamico(self):
        """Busca el modelo 1.5-flash usando los alias más compatibles."""
        try:
            # Listamos para ver qué nombres prefiere tu entorno actual
            modelos_en_red = [m.name for m in genai.list_models()]
            print(f"📡 Modelos detectados en la red: {modelos_en_red}")

            # Lista de candidatos en orden de estabilidad para el plan GRATUITO
            # Probamos nombres con y sin prefijo 'models/'
            candidatos = [
                "gemini-1.5-flash-latest",
                "gemini-1.5-flash",
                "models/gemini-1.5-flash-latest",
                "models/gemini-1.5-flash"
            ]

            for candidato in candidatos:
                if candidato in modelos_en_red or f"models/{candidato}" in modelos_en_red:
                    print(f"✅ Enlace establecido con éxito: {candidato}")
                    return genai.GenerativeModel(candidato)

        except Exception as e:
            print(f"⚠️ Error en escaneo dinámico: {e}")
            
        # Si la lista falla, el nombre más estándar para la v1beta es este:
        print("⚠️ Usando dirección de emergencia estándar.")
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

                    if len(respuesta_final) > 1950:
                        respuesta_final = respuesta_final[:1950] + "\n\n*(Transmisión cortada por exceso de datos...)*"

                    self.guardar_memoria(user_id, "usuario", raw_content)
                    self.guardar_memoria(user_id, "bot", respuesta_final)
                    await message.reply(respuesta_final)
                except Exception as e:
                    await message.reply(f"🔥 Error en la matriz de IA: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

