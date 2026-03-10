import discord
from discord.ext import commands, tasks
import psycopg2
import os
from playwright.async_api import async_playwright

class Monitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        base_url = os.getenv("DATABASE_URL", "").split('?')[0]
        self.db_url = f"{base_url}?sslmode=require"
        self.init_db()
        self.vigilancia_loop.start() # Inicia el latido del monitor

    def init_db(self):
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TABLE IF NOT EXISTS monitoreo (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    url TEXT,
                    last_content TEXT,
                    channel_id BIGINT
                );''')
                conn.commit()

    def cog_unload(self):
        self.vigilancia_loop.cancel()

    @tasks.loop(minutes=1.0)
    async def vigilancia_loop(self):
        """Bucle de escaneo constante de la red."""
        print("👁️ ShadowBot: Escaneando objetivos...")
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, user_id, url, last_content, channel_id FROM monitoreo")
                    objetivos = cur.fetchall()

            if not objetivos: return

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                for obj_id, user_id, url, last_content, channel_id in objetivos:
                    page = await browser.new_page()
                    try:
                        await page.goto(url, timeout=25000)
                        current_content = await page.evaluate("() => document.body.innerText")
                        current_content = current_content[:1000].strip()

                        # Si el contenido cambió y ya teníamos un registro previo
                        if last_content and current_content != last_content:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.send(
                                    f"⚠️ **SISTEMA DE VIGILANCIA: CAMBIO DETECTADO**\n"
                                    f"<@{user_id}>, la estructura de datos en `{url}` ha variado.\n"
                                    f"ID de rastreo: `{obj_id}`"
                                )
                        
                        # Actualizar la huella digital en la DB
                        with psycopg2.connect(self.db_url) as conn:
                            with conn.cursor() as cur:
                                cur.execute("UPDATE monitoreo SET last_content = %s WHERE id = %s", (current_content, obj_id))
                                conn.commit()
                    except Exception as e:
                        print(f"❌ Error en objetivo {obj_id}: {e}")
                    finally:
                        await page.close()
                await browser.close()
        except Exception as e:
            print(f"🔥 Fallo en el núcleo de monitoreo: {e}")

    @commands.command(name="watch")
    async def watch(self, ctx, url: str):
        """Fija un objetivo para vigilancia constante."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO monitoreo (user_id, url, channel_id) VALUES (%s, %s, %s)",
                        (ctx.author.id, url, ctx.channel.id)
                    )
                    conn.commit()
            await ctx.send(f"✅ **Objetivo fijado.** Escaneando `{url}` cada 60 segundos.")
        except Exception as e:
            await ctx.send(f"🔥 Error al fijar objetivo: {e}")

    @commands.command(name="listwatch")
    async def listwatch(self, ctx):
        """Muestra tus objetivos de vigilancia actuales."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, url FROM monitoreo WHERE user_id = %s", (ctx.author.id,))
                    rows = cur.fetchall()
            
            if not rows:
                return await ctx.send("📭 No tienes objetivos en vigilancia activa.")
            
            lista = "\n".join([f"🆔 `{r[0]}` - URL: {r[1]}" for r in rows])
            await ctx.send(f"🛰️ **Tus objetivos activos:**\n{lista}")
        except Exception as e:
            await ctx.send(f"🔥 Error al leer la base de datos: {e}")

    @commands.command(name="unwatch")
    async def unwatch(self, ctx, target_id: int):
        """Elimina un objetivo usando su ID."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM monitoreo WHERE id = %s AND user_id = %s", (target_id, ctx.author.id))
                    conn.commit()
            await ctx.send(f"🗑️ Objetivo `{target_id}` eliminado de la red de vigilancia.")
        except Exception as e:
            await ctx.send(f"🔥 No se pudo eliminar el objetivo: {e}")

async def setup(bot):
    await bot.add_cog(Monitor(bot))

