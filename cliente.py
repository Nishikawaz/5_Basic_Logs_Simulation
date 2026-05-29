import requests
import random
from datetime import datetime

# Definimos la URL de nuestra API local, apuntando al endpoint '/logs' y al puerto 6869 que configuramos en Flask
URL_SERVIDOR = "http://localhost:6869/logs"

# Token único por servicio - Diccionario que aloja el tipo de servicio con el token de autorización correspondiente
TOKENS = {
    "Registro":      "TOKEN_servicio_A",
    "Autenticacion": "TOKEN_servicio_B",
    "Pagos":         "TOKEN_servicio_C",
}

# Mensajes por servicio - Diccionario con Registro | Mensajes simulando interacciones
MENSAJES_POR_SERVICIO = {
    "Registro": [
        "Usuario registrado exitosamente",
        "El email ya estaba en uso",
        "Fallo al enviar correo de confirmación",
        "Registro completado pero sin foto de perfil (clásico)",
    ],
    "Autenticacion": [
        "Usuario logueado exitosamente",
        "Contraseña incorrecta — tercer intento",
        "Token de sesión expirado",
        "Login bloqueado por demasiados intentos fallidos",
    ],
    "Pagos": [
        "Transacción completada exitosamente",
        "La transacción expiró antes de confirmarse",
        "Fallo al conectar con la pasarela de pagos",
        "Pago rechazado por fondos insuficientes",
    ],
}

# Lista con los niveles de severidad estándar que presenta un log
NIVELES = ["INFO", "WARNING", "ERROR", "DEBUG", "CRITICAL"]

# Función de simulación de logs para un servicio específico
def generar_log_falso(nombre_servicio):

    # Retorna un diccionario con la estructura
    return {
        "timestamp": datetime.now().isoformat(),
        "service":   nombre_servicio,
        "severity":  random.choice(NIVELES),
        "message":   random.choice(MENSAJES_POR_SERVICIO[nombre_servicio]),
    }

# Función de envío de logs en el que se indica:
# 1) El servicio (y el mensaje).
# 2) La cantidad de logs a generarse.
def enviar_logs(nombre_servicio, cantidad):
    token = TOKENS.get(nombre_servicio) # --> # Busca el token correspondiente al servicio en el diccionario TOKENS
    if not token: # Si el servicio no tiene un token definido, avisa por consola y detiene la función
        print(f"[{nombre_servicio}] No hay token definido para este servicio. Abortando.")
        return

    headers = {
        "Authorization": f"Token {token}", # --> Header de autorización que la API va a validar
        "Content-Type":  "application/json", # --> Le indicamos a la API que el cuerpo de nuestra petición va a ser un JSON
    }


    logs_a_enviar = [generar_log_falso(nombre_servicio) for _ in range(cantidad)]

    print(f"[{nombre_servicio}] Enviando {cantidad} log(s)...")

    try:
        respuesta = requests.post(
            URL_SERVIDOR, # --> # La URL de destino (http://localhost:6869/logs)
            json=logs_a_enviar, 
            headers=headers, # --> El Autorizador y el formato
            timeout=5,  # Evita que el script quede colgado si el servidor no responde
        )

        print(f"[{nombre_servicio}] Status: {respuesta.status_code}")

        # Parseamos JSON solo si el servidor realmente devolvió JSON
        try:
            print(f"[{nombre_servicio}] Respuesta: {respuesta.json()}")
        except requests.exceptions.JSONDecodeError:
            print(f"[{nombre_servicio}] Respuesta no era JSON: {respuesta.text}")

    except requests.exceptions.ConnectionError:
        print(f"[{nombre_servicio}] No se pudo conectar al servidor. ¿Está corriendo?")
    except requests.exceptions.Timeout:
        print(f"[{nombre_servicio}] El servidor tardó demasiado en responder.")


if __name__ == "__main__":
    # Simulamos los tres servicios enviando distinta cantidad de logs cada uno
    enviar_logs("Registro",      cantidad=333)
    enviar_logs("Autenticacion", cantidad=333)
    enviar_logs("Pagos",         cantidad=333)