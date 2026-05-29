from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

# Instancia de la aplicación Flask
app = Flask(__name__)

TOKENS_VALIDOS = {
    "TOKEN_servicio_A": "Servicio_A", 
    "TOKEN_servicio_B": "Servicio_B",
    "TOKEN_servicio_C": "Servicio_C",
    "Consultas": "consulta"
}

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

# Función de verificación de Token
def verificar_token(auth_header):
    if not auth_header: # --> Si el header no es de autenticación, tira False
        return False
    # Divide el contenido del encabezado por el espacio
    partes = auth_header.split(" ")
    # Verifica que haya exactamente 2 partes y que la primera palabra sea exactamente "Token"
    if len(partes) == 2 and partes[0] == "Token":
        # Extrae la segunda parte, que es el token en sí
        token = partes[1]
        # Retorna True si el token existe como llave en nuestro diccionario TOKENS_VALIDOS, de lo contrario False
        return token in TOKENS_VALIDOS
    return False

# Función donde se define un endpoint o ruta en '/logs' que solo acepta peticiones HTTP de tipo POST (para crear/enviar datos)
@app.route('/logs', methods=['POST'])
def recibir_logs():
    # Extrae el valor del encabezado 'Authorization' de la petición entrante
    auth_header = request.headers.get('Authorization')
    if not verificar_token(auth_header): # Llama a la función de verificación. Si da False (no autorizado)...
        return jsonify({"error": "Quién sos, bro?"}), 401 # Devuelve un json con un mensaje de error y el status code correspondiente (No autorizado)

    # Parsea la petición como json, si no cumple con la estructura o está vacío...
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "No enviaste datos JSON"}), 400 # Devuelve un json con error y status code correspondiente (Bad Request)

    if isinstance(datos, dict):
        datos = [datos]

    conn = db_connection()
    cursor = conn.cursor()

    # Convertimos la fecha a string en formato ISO
    fecha_recepcion = datetime.now().isoformat()

    # Parametrización con los placeholders
    for log in datos:
        cursor.execute(
            'INSERT INTO logs (timestamp, service, severity, message, received_at) VALUES (?, ?, ?, ?, ?)',
            (log.get('timestamp'), log.get('service'), log.get('severity'), log.get('message'), fecha_recepcion)
        )
    
    conn.commit()
    conn.close()

    return jsonify({"mensaje": f"{len(datos)} logs guardados con éxito"}), 201 # --> Se guardan los cambios y responde con status code 201 (Created)

# Define el endpoint en '/logs', pero esta vez para peticiones de tipo GET (para consultar o pedir datos)
@app.route('/logs', methods=['GET'])
def consultar_logs():
    # Al igual que en POST, leemos el encabezado de autorización
    auth_header = request.headers.get('Authorization') # Lectura del header de autenticación
    if not verificar_token(auth_header): 
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
    app.run(debug=True, port=6869)