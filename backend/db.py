import os
from decimal import Decimal
from datetime import date
import calendar

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()


def get_connection():
    """
    Crea una conexión a MySQL.

    En local usa variables del archivo .env.
    En GCP estas variables vendrán desde Secret Manager o configuración de Cloud Run.
    """
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "quincena"),
        )
    except Error as exc:
        raise RuntimeError(f"No se pudo conectar a MySQL: {exc}") from exc


def decimal_to_float(value):
    """
    Convierte valores Decimal de MySQL a float para poder devolverlos como JSON.
    """
    if isinstance(value, Decimal):
        return float(value)
    return value


def insertar_gasto(usuario_id: int, monto: float, categoria: str, fecha: str):
    """
    Inserta un gasto en la tabla gastos.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            INSERT INTO gastos (usuario_id, monto, categoria, fecha)
            VALUES (%s, %s, %s, %s)
            """,
            (usuario_id, monto, categoria, fecha),
        )

        conn.commit()

        return {
            "id": cursor.lastrowid,
            "usuario_id": usuario_id,
            "monto": monto,
            "categoria": categoria,
            "fecha": fecha,
        }

    finally:
        cursor.close()
        conn.close()


def calcular_proyeccion_simple(gastado_actual: float):
    """
    Calcula una proyección básica del gasto mensual.

    Esta función sirve para el arranque del proyecto antes de integrar BigQuery ML.
    """
    hoy = date.today()
    dias_del_mes = calendar.monthrange(hoy.year, hoy.month)[1]

    ritmo_diario = gastado_actual / hoy.day
    return ritmo_diario * dias_del_mes


def obtener_dashboard(usuario_id: int):
    """
    Construye el JSON del dashboard usando datos de MySQL.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT presupuesto_mensual
            FROM usuarios
            WHERE id = %s
            """,
            (usuario_id,),
        )
        usuario = cursor.fetchone()

        if not usuario:
            raise ValueError("Usuario no encontrado")

        normal_mensual = decimal_to_float(usuario["presupuesto_mensual"])

        cursor.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS gastado
            FROM gastos
            WHERE usuario_id = %s
              AND MONTH(fecha) = MONTH(CURDATE())
              AND YEAR(fecha) = YEAR(CURDATE())
            """,
            (usuario_id,),
        )
        row_gastado = cursor.fetchone()
        gastado = decimal_to_float(row_gastado["gastado"])

        cursor.execute(
            """
            SELECT categoria, SUM(monto) AS total
            FROM gastos
            WHERE usuario_id = %s
              AND MONTH(fecha) = MONTH(CURDATE())
              AND YEAR(fecha) = YEAR(CURDATE())
            GROUP BY categoria
            ORDER BY total DESC
            """,
            (usuario_id,),
        )
        desglose = [
            {
                "categoria": row["categoria"],
                "total": decimal_to_float(row["total"]),
            }
            for row in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT id, monto, categoria, fecha
            FROM gastos
            WHERE usuario_id = %s
              AND monto > (
                  SELECT COALESCE(AVG(monto) + 2 * STDDEV(monto), 999999)
                  FROM gastos
                  WHERE usuario_id = %s
              )
            ORDER BY fecha DESC
            LIMIT 10
            """,
            (usuario_id, usuario_id),
        )
        anomalias = [
            {
                "id": row["id"],
                "monto": decimal_to_float(row["monto"]),
                "categoria": row["categoria"],
                "fecha": str(row["fecha"]),
            }
            for row in cursor.fetchall()
        ]

        proyectado = calcular_proyeccion_simple(gastado)
        safe_to_spend = max(normal_mensual - proyectado, 0)

        return {
            "usuario_id": usuario_id,
            "proyectado": round(proyectado, 2),
            "normal_mensual": round(normal_mensual, 2),
            "gastado": round(gastado, 2),
            "safe_to_spend": round(safe_to_spend, 2),
            "desglose": desglose,
            "anomalias": anomalias,
        }

    finally:
        cursor.close()
        conn.close()
