import discord
from discord.ext import commands
from playwright.async_api import async_playwright

class WebScraper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def extraer_contenido(self, url):
        """Extrae el texto de una URL usando Chromium en la nube."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36")
            page = await context.new_page()
            
            try:
                # Tiempo de espera de 20s para evitar cuelgues
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                titulo = await page.title()
                # Extraemos solo el texto visible para no saturar el prompt
                contenido = await page.evaluate("() => document.body.innerText")
                await browser.close()
                return {"titulo": titulo, "texto": contenido[:1500]} # Límite de 1500 caracteres
            except Exception as e:
                await browser.close()
                return {"error": str(e)}

async def setup(bot):
    await bot.add_cog(WebScraper(bot))

