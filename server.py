from flask import Flask, request, jsonify
from datetime import datetime
from database import init_db, guardar_logs
import sqlite3

app = Flask(__name__)

TOKENS = {
    "token_a": "servicio01",
    "token_b": "servicio02"
}

def validar_token():
    """Verifica si el token del header es válido."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Token "):
        return None
    return TOKENS.get(auth.replace("Token ", ""))

@app.route("/logs", methods=["POST"])
def recibir_logs():
    servicio = validar_token()
    if not servicio:
        return jsonify({"error": "Quién sos, bro?"}), 401
    
    logs = request.get_json()
    if not isinstance(logs, list):
        return jsonify({"error": "Se esperaba una lista de logs"}), 400
    
    now = datetime.utcnow().isoformat()
    datos = []

    # Armamos la lista para guardar todo de una vez
    for log in logs:
        # Usamos .get() para que si falta un dato, no crashee el server
        if "timestamp" in log and "severity" in log:
            datos.append((log["timestamp"], now, servicio, log["severity"], log.get("message", "")))

    if not datos:
        return jsonify({"error": "No hay logs válidos"}), 400

    guardar_logs(datos) # Inserción masiva: salva tu vida y la del servidor
    return jsonify({"message": "Logs guardados"}), 201

@app.route("/logs", methods=["GET"])
def get_logs():
    """Devuelve los logs filtrando por los parámetros de la URL."""
    query = "SELECT timestamp, received_at, service, severity, message FROM logs WHERE 1=1"
    params = []

    if request.args.get("timestamp_start"):
        query += " AND timestamp >= ?"
        params.append(request.args.get("timestamp_start"))
    if request.args.get("timestamp_end"):
        query += " AND timestamp <= ?"
        params.append(request.args.get("timestamp_end"))

    query += " ORDER BY received_at DESC"

    conn = sqlite3.connect("logs.db")
    # row_factory permite acceder a las columnas por nombre en vez de índice numérico
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    # Transformamos las filas a diccionarios limpios para el JSON
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(logs), 200

init_db()
app.run(debug=True)