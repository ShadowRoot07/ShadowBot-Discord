import os
from src.bot import bot

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Error al iniciar el bot: {e}")
    else:
        print("❌ Error: No se encontró DISCORD_TOKEN en el entorno.")

