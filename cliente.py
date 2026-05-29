import argparse
import random
import time
from datetime import datetime, timezone

import requests

# --- CONFIGURACION ---
URL = "http://127.0.0.1:5000/logs"

# Tokens que coinciden con la lista manual del servidor.
SERVICIOS = {
    "servicio01": "token_a",
    "servicio02": "token_b",
    "servicio03": "token_c",
}

SEVERIDADES = ["INFO", "DEBUG", "WARNING", "ERROR", "FATAL"]
MENSAJES = {
    "servicio01": [
        "Usuario hizo login exitoso.",
        "Token vencido mientras alguien juraba que funcionaba ayer.",
        "Intento de login bloqueado por demasiados errores seguidos.",
    ],
    "servicio02": [
        "Meme mal rankeado detectado en cache.",
        "Catalogo sincronizado sin incidentes visibles.",
        "Busqueda devolvio cero resultados y una mirada incomoda.",
    ],
    "servicio03": [
        "Timeout esperando respuesta de la pasarela de pago.",
        "Pago aprobado por el procesador externo.",
        "Fallo al conectar con la base de datos principal.",
    ],
}


def fecha_utc_actual():
    """Devuelve una fecha ISO-8601 en UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def generar_log_falso(servicio):
    """Crea un diccionario con datos simulados de un log."""
    return {
        "timestamp": fecha_utc_actual(),
        "service": servicio,
        "severity": random.choice(SEVERIDADES),
        "message": random.choice(MENSAJES[servicio]),
    }


def enviar_batch(servicio, batch_size):
    """Genera un lote de logs y lo envia al servidor central."""
    token = SERVICIOS[servicio]
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }
    logs_batch = [generar_log_falso(servicio) for _ in range(batch_size)]

    response = requests.post(URL, json=logs_batch, headers=headers, timeout=10)
    if response.status_code == 201:
        data = response.json()
        print(f"[+] {servicio}: guardados={data.get('stored')} mensaje={data.get('message')}")
        return

    print(f"[-] {servicio}: error HTTP {response.status_code}: {response.text}")


def iniciar_simulador(servicios, batch_size=10, sleep_time=3, ciclos=1):
    """Genera logs en lotes para uno o varios servicios."""
    print(f"Iniciando simulador: servicios={', '.join(servicios)} batch_size={batch_size} ciclos={ciclos}")

    for ciclo in range(1, ciclos + 1):
        print(f"\nCiclo {ciclo}/{ciclos}")
        for servicio in servicios:
            try:
                enviar_batch(servicio, batch_size)
            except requests.exceptions.ConnectionError:
                print("[!] El servidor central no responde. Levanta Flask con: python server.py")
                return
            except requests.exceptions.Timeout:
                print("[!] El servidor tardo demasiado en responder.")
                return

        if ciclo < ciclos:
            time.sleep(sleep_time)


def parse_args():
    parser = argparse.ArgumentParser(description="Simulador de servicios que envian logs por HTTP")
    parser.add_argument("--service", choices=SERVICIOS.keys(), help="Servicio especifico a simular")
    parser.add_argument("--all", action="store_true", help="Simula todos los servicios disponibles")
    parser.add_argument("--batch-size", type=int, default=10, help="Cantidad de logs por request")
    parser.add_argument("--ciclos", type=int, default=1, help="Cantidad de ciclos de envio")
    parser.add_argument("--sleep", type=float, default=3, help="Segundos entre ciclos")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    servicios = list(SERVICIOS.keys()) if args.all else [args.service or "servicio01"]
    iniciar_simulador(servicios, batch_size=args.batch_size, sleep_time=args.sleep, ciclos=args.ciclos)
