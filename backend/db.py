"""
db.py

Funciones de acceso a datos para el proyecto Quincena.

Este archivo concentra la conexión a MySQL y las consultas SQL usadas por la API.
La idea es mantener main.py limpio: main.py recibe HTTP, db.py habla con la base.

En despliegue final, esta conexión apuntará a Cloud SQL MySQL usando variables
de entorno configuradas en Cloud Run y secretos almacenados en Secret Manager.
"""

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
    Crea una conexión a MySQL usando variables de entorno.

    Variables esperadas:
    - DB_HOST
    - DB_PORT
    - DB_USER
    - DB_PASSWORD
    - DB_NAME

    En local pueden vivir en un archivo .env.
    En Cloud Run se configurarán como variables de entorno o secretos.
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
    Convierte Decimal a float para que FastAPI pueda serializar la respuesta.

    MySQL devuelve los DECIMAL como objetos Decimal de Python.
    JSON no puede enviarlos directamente sin convertirlos.
    """
    if isinstance(value, Decimal):
        return float(value)
    return value


def insertar_gasto(usuario_id: int, monto: float, categoria: str, fecha: str):
    """
    Inserta un gasto en la tabla gastos.

    Esta función implementa la parte principal del endpoint POST /gastos.
    Usa SQL parametrizado (%s) para evitar concatenar valores directamente
    dentro de la consulta.
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
    Calcula una proyección simple del gasto mensual.

    Fórmula:
    gasto proyectado = ritmo diario actual * días del mes

    Esta versión es útil para el arranque progresivo del sistema:
    - Funciona desde el día 1.
    - No depende todavía de BigQuery ML.
    - Después puede reemplazarse o complementarse con ARIMA_PLUS.
    """
    hoy = date.today()
    dias_del_mes = calendar.monthrange(hoy.year, hoy.month)[1]

    ritmo_diario = gastado_actual / hoy.day
    return ritmo_diario * dias_del_mes


def obtener_dashboard(usuario_id: int):
    """
    Construye el JSON del endpoint GET /dashboard.

    Consulta:
    - presupuesto mensual del usuario;
    - gasto acumulado del mes actual;
    - desglose por categoría;
    - gastos anómalos usando AVG() + 2 * STDDEV();
    - proyección simple para estimar cierre de mes.

    Esta función mantiene el contrato que usará el frontend.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener el presupuesto normal del usuario.
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

        # Calcular el gasto total del mes actual.
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

        # Agrupar gastos por categoría para alimentar el dashboard.
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

        # Detectar gastos inusuales con una regla estadística simple:
        # un gasto se marca como anomalía si supera promedio + 2 desviaciones estándar.
        # Esto funciona desde el día 1 y cumple la opción principal del documento.
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

        # Proyección preliminar mientras BigQuery ML no esté integrado.
        proyectado = calcular_proyeccion_simple(gastado)

        # safe_to_spend representa cuánto puede gastar sin rebasar su gasto normal.
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
