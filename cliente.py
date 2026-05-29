import requests
import random
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
URL = "http://127.0.0.1:5000/logs"
# Usamos uno de los tokens válidos que definiste en tu .env o app.py
TOKEN = "token_a" 
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

SEVERIDADES = ["INFO", "DEBUG", "WARNING", "ERROR", "FATAL"]
MENSAJES = [
    "Usuario hizo login exitoso.",
    "Fallo al conectar con la base de datos principal.",
    "Meme mal rankeado detectado en caché.",
    "El puerto 8080 ya está en uso.",
    "Timeout esperando respuesta de la pasarela de pago.",
    "Memoria al 99%, preparate para el impacto."
]

def generar_log_falso():
    """Crea un diccionario con datos simulados de un log."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "severity": random.choice(SEVERIDADES),
        "message": random.choice(MENSAJES)
    }

def iniciar_ataque(batch_size=5, sleep_time=2):
    """Genera logs en lotes y los envía al servidor continuamente."""
    print(f"🚀 Iniciando simulador. Enviando lotes de {batch_size} logs cada {sleep_time} segundos...\n")
    
    while True:
        # Generamos una lista de logs (tu servidor exige recibir una lista)
        logs_batch = [generar_log_falso() for _ in range(batch_size)]
        
        try:
            # Enviamos el POST con el JSON y los headers de autenticación
            response = requests.post(URL, json=logs_batch, headers=HEADERS)
            
            if response.status_code == 201:
                print(f"[+] Éxito: {response.json().get('message')}")
            elif response.status_code == 401:
                print(f"[x] Error de Autenticación: {response.json().get('error')} - Revisá tu token.")
                break # Frenamos el script si el token está mal
            else:
                print(f"[-] Error del servidor ({response.status_code}): {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("[!] El servidor central no responde. ¿Te olvidaste de levantar Flask? Reintentando en 3s...")
            time.sleep(3)
            continue
            
        # Pausa antes del siguiente envío
        time.sleep(sleep_time)

    # Arrancamos tirando 10 logs cada 3 segundos
    iniciar_ataque(batch_size=10, sleep_time=3)