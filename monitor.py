import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio
from telegram import Bot
import logging

# ================= CONFIGURACIÓN =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

URLS = [
    "https://www.ticketmaster.co/event/bts-world-tour-venta-general-sabado-3-octubre",
    "https://www.ticketmaster.co/event/bts-world-tour-venta-general-viernes-2-octubre"
]
TIEMPO_ENTRE_CHECKS = 60
# =================================================

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise Exception("Faltan variables de entorno")

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
        
        # PRIMERO: Si dice explícitamente "agotado" -> NO hay boletas
        if "agotado" in texto:
            # Buscar que no sea parte de "no agotado" o texto similar
            if "todas las localidades están agotadas" in texto or "entradas agotadas" in texto:
                return False
        
        # Si encuentra un botón de compra real (señal más confiable)
        botones = soup.find_all('button', string=lambda x: x and 'comprar' in x.lower())
        if botones:
            return True
            
        # Si hay un enlace o texto que indica compra activa
        if "comprar boletas" in texto or "comprar entradas" in texto:
            # Verificar que NO diga "agotado" cerca
            if "agotado" not in texto[texto.find("comprar"):texto.find("comprar")+200]:
                return True
                
        return False
    except Exception as e:
        logging.error(f"Error revisando {url}: {e}")
        return False

async def main():
    logging.info("Iniciando monitoreo de boletas BTS...")
    logging.info("Versión mejorada - detección más precisa")
    estados_previos = {url: False for url in URLS}
    
    while True:
        for url in URLS:
            disponible = hay_boletas(url)
            fecha = 'Sábado' if 'sabado' in url else 'Viernes'
            logging.info(f"{fecha}: {'DISPONIBLE' if disponible else 'AGOTADO'}")
            
            if disponible and not estados_previos[url]:
                logging.info(f"¡LIBERADAS! {url}")
                await enviar_alerta(url)
                estados_previos[url] = True
            elif not disponible:
                estados_previos[url] = False
        await asyncio.sleep(TIEMPO_ENTRE_CHECKS)

if __name__ == "__main__":
    asyncio.run(main())
