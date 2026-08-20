from flask import Flask, request, jsonify
import os
import sqlite3
from datetime import datetime

# Instancia de la aplicación Flask
app = Flask(__name__)

# Cada token de servicio queda ATADO al nombre de servicio que tiene permitido escribir.
# Los valores deben coincidir exactamente con el campo "service" que manda cliente.py:
# si no coinciden, el servicio no puede publicar ni sus propios logs.
TOKENS_VALIDOS = {
    "TOKEN_servicio_A": "Registro",
    "TOKEN_servicio_B": "Autenticacion",
    "TOKEN_servicio_C": "Pagos",
    "Consultas": None,   # None = token de solo lectura, no puede hacer POST
}

# Campos que un log debe traer sí o sí para ser aceptado
CAMPOS_REQUERIDOS = ("timestamp", "service", "severity", "message")

# Configuración y conexión de la BD
def db_connection():
    conn = sqlite3.connect('logs.db')
    # Cambia el formato de salida de las filas: permite acceder a los datos por el nombre de la columna en lugar de por índice numérico
    conn.row_factory = sqlite3.Row # --> Para poder acceder por nombre de columna (más intuitivo)
    return conn 

# Creación de la tabla
def inicializar_bd():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            timestamp TEXT, 
            service TEXT,
            severity TEXT,
            message TEXT,
            received_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Centinela para distinguir "token invalido" de "token valido de solo lectura".
# Sin esto, un token de consulta (cuyo servicio es None) sería indistinguible de un token inexistente.
TOKEN_INVALIDO = object()

# Función de verificación de Token.
# Devuelve TOKEN_INVALIDO si no autentica; si autentica, devuelve el servicio
# habilitado a escribir (o None si es un token de solo lectura).
def verificar_token(auth_header):
    if not auth_header: # --> Si el header no es de autenticación, no autentica
        return TOKEN_INVALIDO
    # Divide el contenido del encabezado por el espacio
    partes = auth_header.split(" ")
    # Verifica que haya exactamente 2 partes y que la primera palabra sea exactamente "Token"
    if len(partes) == 2 and partes[0] == "Token":
        # Extrae la segunda parte, que es el token en sí
        token = partes[1]
        if token in TOKENS_VALIDOS:
            return TOKENS_VALIDOS[token]
    return TOKEN_INVALIDO

# Función donde se define un endpoint o ruta en '/logs' que solo acepta peticiones HTTP de tipo POST (para crear/enviar datos)
@app.route('/logs', methods=['POST'])
def recibir_logs():
    # Extrae el valor del encabezado 'Authorization' de la petición entrante
    auth_header = request.headers.get('Authorization')
    servicio_autorizado = verificar_token(auth_header) # Devuelve el servicio habilitado, None, o TOKEN_INVALIDO
    if servicio_autorizado is TOKEN_INVALIDO:
        return jsonify({"error": "Quién sos, bro?"}), 401 # Devuelve un json con un mensaje de error y el status code correspondiente (No autorizado)

    # El token autentica, pero es de solo lectura: no puede escribir logs
    if servicio_autorizado is None:
        return jsonify({"error": "Este token es de solo lectura"}), 403 # Forbidden

    # Parsea la petición como json, si no cumple con la estructura o está vacío...
    # silent=True evita que un cuerpo malformado levante una excepción y termine en un 500.
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "No enviaste datos JSON"}), 400 # Devuelve un json con error y status code correspondiente (Bad Request)

    if isinstance(datos, dict):
        datos = [datos]

    if not isinstance(datos, list):
        return jsonify({"error": "Se esperaba un objeto JSON o una lista de objetos"}), 400

    # Validación previa: se revisa TODO el lote antes de escribir nada, así un log
    # inválido no deja la mitad del lote insertada y la otra mitad no.
    for indice, log in enumerate(datos):
        if not isinstance(log, dict):
            return jsonify({"error": f"El elemento {indice} no es un objeto JSON"}), 400

        faltantes = [campo for campo in CAMPOS_REQUERIDOS if not log.get(campo)]
        if faltantes:
            return jsonify({"error": f"Al elemento {indice} le faltan campos: {faltantes}"}), 400

        # Un servicio solo puede escribir logs a su propio nombre
        if log["service"] != servicio_autorizado:
            return jsonify({
                "error": f"El token de '{servicio_autorizado}' no puede escribir logs de '{log['service']}'"
            }), 403

    conn = db_connection()
    cursor = conn.cursor()

    # Convertimos la fecha a string en formato ISO
    fecha_recepcion = datetime.now().isoformat()

    # Parametrización con los placeholders
    for log in datos:
        cursor.execute(
            'INSERT INTO logs (timestamp, service, severity, message, received_at) VALUES (?, ?, ?, ?, ?)',
            (log['timestamp'], log['service'], log['severity'], log['message'], fecha_recepcion)
        )

    conn.commit()
    conn.close()

    return jsonify({"mensaje": f"{len(datos)} logs guardados con éxito"}), 201 # --> Se guardan los cambios y responde con status code 201 (Created)

# Define el endpoint en '/logs', pero esta vez para peticiones de tipo GET (para consultar o pedir datos)
@app.route('/logs', methods=['GET'])
def consultar_logs():
    # Al igual que en POST, leemos el encabezado de autorización
    auth_header = request.headers.get('Authorization') # Lectura del header de autenticación
    # Para leer alcanza con cualquier token válido, sea de servicio o de consulta
    if verificar_token(auth_header) is TOKEN_INVALIDO:
        return jsonify({"error": "Quién sos, bro?"}), 401 # Devuelve un json con un mensaje de error y el status code correspondiente (No autorizado)
    
    # Se extraen los parámetros de búsqueda de la URL (/logs[?severity]=[XYZ])
    timestamp_start = request.args.get('timestamp_start') # Fecha inicio
    timestamp_end = request.args.get('timestamp_end') # Fecha fin
    severity = request.args.get('severity') # Severidad / Gravedad

    query = 'SELECT * FROM logs WHERE 1=1' # Concatenación con AND
    parametros = [] # --> # Lista vacía donde iremos guardando los valores que filtrarán la consulta

    # Condicional de tiempo inicial
    if timestamp_start:
        query += ' AND timestamp >= ?'
        parametros.append(timestamp_start)
    # Condicional de tiempo final
    if timestamp_end:
        query += ' AND timestamp <= ?'
        parametros.append(timestamp_end)
    # Condicional de severidad / gravedad
    if severity:
        query += ' AND severity = ?'
        parametros.append(severity.upper()) # Usamos upper() para asegurarnos que sea en mayúsculas

    query += ' ORDER BY id DESC'

    conn = db_connection()
    cursor = conn.cursor()
    
    # Ejecutamos la consulta SQL final, convirtiendo la lista 'parametros' en una tupla porque así lo exige sqlite3
    cursor.execute(query, tuple(parametros)) # --> Convierte la lista en una tupla (Es lo que espera SQLite)
    logs_db = cursor.fetchall()
    
    # Flask necesita que los sqlite3.Row sean explícitamente convertidos a diccionarios normales para usar jsonify
    resultados = [dict(row) for row in logs_db]
    
    conn.close()

    return jsonify(resultados), 200 


if __name__ == '__main__':
    inicializar_bd()
    # debug se activa solo si se pide explícitamente (FLASK_DEBUG=1). Con debug=True fijo,
    # el servidor expone una consola interactiva que ejecuta código arbitrario.
    modo_debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=modo_debug, port=6869)