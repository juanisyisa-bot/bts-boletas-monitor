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
        
        # Buscar la palabra "Agotado" en el texto visible de la página
        texto_completo = soup.get_text()
        
        # Método 1: Buscar el título de la página
        titulo = soup.find('title')
        if titulo:
            titulo_texto = titulo.get_text().lower()
            if 'agotado' in titulo_texto:
                logging.info(f"Título dice AGOTADO: {titulo_texto[:50]}")
                return False
        
        # Método 2: Buscar en el cuerpo principal
        # Si encuentra "agotado" y NO encuentra "comprar" cerca, asumimos agotado
        if 'agotado' in texto_completo.lower():
            # Verificar si también hay "comprar" muy cerca (menos de 500 caracteres)
            idx_agotado = texto_completo.lower().find('agotado')
            if idx_agotado != -1:
                # Revisar los 1000 caracteres alrededor de "agotado"
                inicio = max(0, idx_agotado - 500)
                fin = min(len(texto_completo), idx_agotado + 500)
                contexto = texto_completo[inicio:fin].lower()
                
                # Si en el contexto aparece "comprar" y NO aparece "agotado" de nuevo
                if 'comprar' in contexto and contexto.count('agotado') <= 1:
                    logging.info("Posible liberación detectada - contexto contiene 'comprar' cerca de 'agotado'")
                    # Hacer una verificación más profunda
                    return _verificar_boton_compra(soup)
        
        # Si no hay "agotado" en todo el texto, asumimos que hay boletas
        if 'agotado' not in texto_completo.lower():
            logging.info("No se encontró la palabra 'agotado' - asumiendo boletas disponibles")
            return True
            
        return False
        
    except Exception as e:
        logging.error(f"Error revisando {url}: {e}")
        return False

def _verificar_boton_compra(soup):
    """Verificación adicional: buscar botones de compra reales"""
    try:
        # Buscar botones que digan "comprar"
        botones = soup.find_all(['button', 'a'], string=lambda x: x and 'comprar' in x.lower())
        if botones:
            logging.info(f"✅ Botón de comprar encontrado: {botones[0].get_text()}")
            return True
        
        # Buscar enlaces que digan "comprar"
        enlaces = soup.find_all('a', href=True)
        for enlace in enlaces:
            texto = enlace.get_text().lower()
            if 'comprar' in texto or 'buy' in texto:
                logging.info(f"✅ Enlace de comprar encontrado: {texto[:50]}")
                return True
                
        return False
    except:
        return False

async def main():
    logging.info("=== INICIANDO MONITOR VERSIÓN CORREGIDA ===")
    logging.info("Detección basada en la palabra 'Agotado'")
    logging.info("===========================================")
    
    # Estado inicial: asumimos que no hay boletas
    estados_previos = {url: False for url in URLS}
    
    while True:
        for url in URLS:
            try:
                disponible = hay_boletas(url)
                fecha = 'Sábado' if 'sabado' in url else 'Viernes'
                
                if disponible:
                    logging.info(f"{fecha}: ✅ DISPONIBLE (enviando alerta si no se envió antes)")
                else:
                    logging.info(f"{fecha}: ❌ AGOTADO")
                
                # Solo enviar alerta si cambió de agotado a disponible
                if disponible and not estados_previos[url]:
                    logging.info(f"🎉 ¡CAMBIÓ A DISPONIBLE! Enviando alerta para {fecha}")
                    await enviar_alerta(url)
                    estados_previos[url] = True
                elif not disponible:
                    estados_previos[url] = False
                    
            except Exception as e:
                logging.error(f"Error procesando {url}: {e}")
                
        await asyncio.sleep(TIEMPO_ENTRE_CHECKS)

if __name__ == "__main__":
    asyncio.run(main())
