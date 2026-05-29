import sqlite3

DATABASE = "logs.db"

def get_db_connection():
    # 1. Agregamos el timeout acá. Ahora TODA conexión que pidas 
    # sabrá esperar hasta 10 segundos si la BD está ocupada.
    conn = sqlite3.connect(DATABASE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea la tabla y los índices necesarios para acelerar las búsquedas."""
    # 2. Usamos 'with' para garantizar que la conexión se cierre pase lo que pase
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                received_at DATETIME NOT NULL,
                service TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_received_at ON logs(received_at);")
        conn.commit()

def guardar_logs_masivo(datos_a_insertar):
    """Inserta una lista de tuplas en una sola transacción."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO logs (timestamp, received_at, service, severity, message) VALUES (?, ?, ?, ?, ?)",
            datos_a_insertar
        )
        conn.commit()

def consultar_logs(query, params):
    """Ejecuta la consulta de filtros y retorna una lista de diccionarios limpios."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
    # El return queda fuera del 'with'. La conexión ya se cerró de forma segura.
    return [dict(row) for row in rows]