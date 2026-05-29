from datetime import datetime, timezone

from flask import Flask, jsonify, request

from database import consultar_logs, guardar_logs_masivo, init_db

app = Flask(__name__)

# Lista manual de tokens validos. Cada token identifica a un servicio.
TOKENS = {
    "token_a": "servicio01",
    "token_b": "servicio02",
    "token_c": "servicio03",
}

SEVERIDADES_VALIDAS = {"DEBUG", "INFO", "WARNING", "ERROR", "FATAL", "CRITICAL"}
MAX_BATCH_SIZE = 1000


def fecha_utc_actual():
    """Devuelve una fecha ISO-8601 en UTC para que SQLite pueda ordenarla bien."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalizar_fecha(valor, nombre_campo):
    """Valida fechas ISO-8601 y las normaliza a UTC."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nombre_campo} debe ser una fecha ISO-8601 no vacia")

    texto = valor.strip()
    texto_parseable = texto[:-1] + "+00:00" if texto.endswith("Z") else texto

    try:
        fecha = datetime.fromisoformat(texto_parseable)
    except ValueError as error:
        raise ValueError(f"{nombre_campo} debe tener formato ISO-8601") from error

    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    else:
        fecha = fecha.astimezone(timezone.utc)

    return fecha.isoformat(timespec="seconds").replace("+00:00", "Z")


def validar_token():
    """Verifica si el header Authorization trae un token valido."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Token "):
        return None

    token = auth.replace("Token ", "", 1).strip()
    return TOKENS.get(token)


def validar_log(log, servicio_autenticado, indice):
    """Valida un log recibido y lo transforma en una tupla lista para guardar."""
    if not isinstance(log, dict):
        raise ValueError(f"El log #{indice} debe ser un objeto JSON")

    campos_requeridos = ["timestamp", "service", "severity", "message"]
    faltantes = [campo for campo in campos_requeridos if campo not in log]
    if faltantes:
        raise ValueError(f"Al log #{indice} le faltan campos: {', '.join(faltantes)}")

    service = str(log["service"]).strip()
    if service != servicio_autenticado:
        raise PermissionError(
            f"El log #{indice} dice ser '{service}', pero el token pertenece a '{servicio_autenticado}'"
        )

    severity = str(log["severity"]).strip().upper()
    if severity not in SEVERIDADES_VALIDAS:
        raise ValueError(f"El log #{indice} tiene severity invalido: {severity}")

    message = log["message"]
    if not isinstance(message, str) or not message.strip():
        raise ValueError(f"El log #{indice} debe tener un message no vacio")

    timestamp = normalizar_fecha(log["timestamp"], f"log #{indice}.timestamp")
    return (timestamp, fecha_utc_actual(), service, severity, message.strip())


@app.route("/logs", methods=["POST"])
def recibir_logs():
    servicio = validar_token()
    if not servicio:
        return jsonify({"error": "Quién sos, bro?"}), 401

    logs = request.get_json(silent=True)
    if isinstance(logs, dict):
        logs = [logs]
    if not isinstance(logs, list):
        return jsonify({"error": "Se esperaba un log o una lista de logs"}), 400
    if not logs:
        return jsonify({"error": "No hay logs para guardar"}), 400
    if len(logs) > MAX_BATCH_SIZE:
        return jsonify({"error": f"El batch no puede superar {MAX_BATCH_SIZE} logs"}), 400

    try:
        datos = [validar_log(log, servicio, indice) for indice, log in enumerate(logs, start=1)]
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    cantidad = guardar_logs_masivo(datos)
    return jsonify({"message": "Logs guardados", "stored": cantidad, "service": servicio}), 201


@app.route("/logs", methods=["GET"])
def get_logs():
    """Devuelve logs filtrados por fecha de evento y fecha de recepcion."""
    servicio = validar_token()
    if not servicio:
        return jsonify({"error": "Quién sos, bro?"}), 401

    query = """
        SELECT id, timestamp, received_at, service, severity, message
        FROM logs
        WHERE 1 = 1
    """
    params = []
    filtros_fecha = {
        "timestamp_start": ("timestamp >= ?", "timestamp_start"),
        "timestamp_end": ("timestamp <= ?", "timestamp_end"),
        "received_at_start": ("received_at >= ?", "received_at_start"),
        "received_at_end": ("received_at <= ?", "received_at_end"),
    }

    try:
        for parametro, (condicion, nombre_campo) in filtros_fecha.items():
            valor = request.args.get(parametro)
            if valor:
                query += f" AND {condicion}"
                params.append(normalizar_fecha(valor, nombre_campo))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if request.args.get("service"):
        query += " AND service = ?"
        params.append(request.args["service"])

    if request.args.get("severity"):
        query += " AND severity = ?"
        params.append(request.args["severity"].upper())

    query += " ORDER BY received_at DESC, id DESC"
    logs = consultar_logs(query, params)

    return jsonify({"total": len(logs), "logs": logs}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
