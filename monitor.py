import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio
from telegram import Bot
import logging

# ================= CONFIGURACIÓN =================
# Estas variables las leeremos de Render (no pongas nada aquí)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

URLS = [
    "https://www.ticketmaster.co/event/bts-world-tour-venta-general-sabado-3-octubre",
    "https://www.ticketmaster.co/event/bts-world-tour-venta-general-viernes-2-octubre"
]
TIEMPO_ENTRE_CHECKS = 60
# =================================================

# Verificar que las variables existen
if not TELEGRAM_TOKEN or not CHAT_ID:
    raise Exception("Faltan variables de entorno. Configura TELEGRAM_TOKEN y CHAT_ID")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=TELEGRAM_TOKEN)

async def enviar_alerta(url):
    fecha = 'Sábado 3 Oct' if 'sabado' in url else 'Viernes 2 Oct'
    mensaje = f"🎫 ¡BOLETAS LIBERADAS!\n\nFecha: {fecha}\nCorre ya: {url}"
    try:
        await bot.send_message(chat_id=CHAT_ID, text=mensaje)
        logging.info(f"✅ Alerta enviada para: {url}")
    except Exception as e:
        logging.error(f"Error enviando alerta: {e}")

def hay_boletas(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        texto = soup.get_text().lower()
        
        if "agotado" in texto or "no hay entradas" in texto:
            return False
        if "comprar" in texto or "venta general" in texto:
            if "boletas disponibles" in texto or "elige tu ubicación" in texto:
                return True
            return True
        return False
    except Exception as e:
        logging.error(f"Error revisando {url}: {e}")
        return False

async def main():
    logging.info("Iniciando monitoreo de boletas BTS...")
    estados_previos = {url: False for url in URLS}
    
    while True:
        for url in URLS:
            disponible = hay_boletas(url)
            if disponible and not estados_previos[url]:
                logging.info(f"¡LIBERADAS! {url}")
                await enviar_alerta(url)
                estados_previos[url] = True
            elif not disponible:
                estados_previos[url] = False
        await asyncio.sleep(TIEMPO_ENTRE_CHECKS)

if __name__ == "__main__":
    asyncio.run(main())