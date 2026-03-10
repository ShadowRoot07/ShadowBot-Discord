# 🕷️ ShadowBot Discord V2

Professional automation and scraping project developed entirely in Termux.
   
## 🚀 Features
- **Built-in AI:** Fluid conversation powered by the Gemini engine.

- **Web Scraping:** On-demand data extraction.

- **24/7:** Ready for GitHub Actions.

## 🛠️ Installation
```bash
pip install -r requirements.txt
python main.py

```

## Project Directory Organization Plan.

```txt
ShadowBot-Discord/
├── .env                # Variables sensibles (Token, API Keys)
├── .gitignore          # Archivos que Git debe ignorar
├── requirements.txt    # Lista de librerías necesarias
├── README.md           # La "cara" del proyecto (Documentación)
├── main.py             # Punto de entrada principal
└── src/                # Código fuente organizado
    ├── __init__.py
    ├── bot.py          # Configuración del Bot y Cogs
    └── cogs/           # Módulos separados (Saludos, Scraping, IA)
        ├── general.py
        └── ai_chat.py
```


