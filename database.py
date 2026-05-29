import sqlite3
from contextlib import closing

DATABASE = "logs.db"


def get_db_connection():
    """Crea una conexion SQLite configurada para el servidor de logs."""
    conn = sqlite3.connect(DATABASE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea la tabla y los indices necesarios para acelerar las busquedas."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                received_at TEXT NOT NULL,
                service TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_received_at ON logs(received_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service ON logs(service);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_severity ON logs(severity);")
        conn.commit()


def guardar_logs_masivo(datos_a_insertar):
    """Inserta muchos logs en una sola transaccion."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO logs (timestamp, received_at, service, severity, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            datos_a_insertar,
        )
        conn.commit()
        return cursor.rowcount


def consultar_logs(query, params):
    """Ejecuta una consulta parametrizada y devuelve filas como diccionarios."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [dict(row) for row in rows]
