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
from mysql.connector import Error, errorcode

from seguridad import hashear_password


load_dotenv()


def get_connection():
    """
    Crea una conexión a MySQL usando variables de entorno.

    Modo local / Cloud Shell:
    - Usa DB_HOST y DB_PORT.
    - Normalmente DB_HOST=127.0.0.1 y DB_PORT=3306.
    - Esto funciona cuando usamos Cloud SQL Auth Proxy localmente.

    Modo Cloud Run:
    - Usa DB_SOCKET.
    - Cloud Run monta Cloud SQL en /cloudsql/PROJECT_ID:REGION:INSTANCE.
    - Esto evita intentar conectarse a 127.0.0.1 dentro del contenedor.
    """
    try:
        db_socket = os.getenv("DB_SOCKET")

        if db_socket:
            return mysql.connector.connect(
                unix_socket=db_socket,
                user=os.getenv("DB_USER", "quincena_user"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "quincena"),
            )

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


def listar_usuarios():
    """
    Devuelve todos los usuarios registrados para el modo multiusuario.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, nombre, ingreso_mensual, presupuesto_mensual
            FROM usuarios
            ORDER BY id ASC
            """
        )

        usuarios = []

        for row in cursor.fetchall():
            usuarios.append(
                {
                    "id": row["id"],
                    "nombre": row["nombre"],
                    "ingreso_mensual": decimal_to_float(row["ingreso_mensual"]),
                    "presupuesto_mensual": decimal_to_float(row["presupuesto_mensual"]),
                }
            )

        return usuarios

    finally:
        cursor.close()
        conn.close()


def crear_usuario(nombre: str, ingreso_mensual: float, presupuesto_mensual: float):
    """
    Crea un usuario nuevo. MySQL asigna el id automáticamente.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            INSERT INTO usuarios (nombre, ingreso_mensual, presupuesto_mensual)
            VALUES (%s, %s, %s)
            """,
            (nombre, ingreso_mensual, presupuesto_mensual),
        )

        conn.commit()

        return {
            "id": cursor.lastrowid,
            "nombre": nombre,
            "ingreso_mensual": ingreso_mensual,
            "presupuesto_mensual": presupuesto_mensual,
        }

    finally:
        cursor.close()
        conn.close()


def registrar_usuario(nombre: str, email: str, password: str,
                      ingreso_mensual: float, presupuesto_mensual: float):
    """
    Registra un usuario nuevo con email único y contraseña hasheada.

    El usuario nace en estado 'pendiente' y rol 'usuario' (defaults del esquema).
    No puede iniciar sesión hasta que un admin lo apruebe.

    El email se normaliza (minúsculas, sin espacios) antes de guardar para
    evitar cuentas duplicadas del tipo 'Mario@x.com' vs 'mario@x.com'.

    La contraseña nunca se guarda en claro: se almacena solo el hash bcrypt.
    """
    email_norm = email.strip().lower()
    password_hash = hashear_password(password)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            INSERT INTO usuarios
                (nombre, email, password_hash, ingreso_mensual, presupuesto_mensual)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (nombre, email_norm, password_hash, ingreso_mensual, presupuesto_mensual),
        )

        conn.commit()

        return {
            "id": cursor.lastrowid,
            "nombre": nombre,
            "email": email_norm,
            "estado": "pendiente",
        }

    except mysql.connector.IntegrityError as exc:
        # Error 1062 = entrada duplicada. Como email es UNIQUE, esto significa
        # que el correo ya está registrado. Lo traducimos a un mensaje claro
        # para que el endpoint devuelva 409 en vez de un 500 con el error crudo.
        if exc.errno == errorcode.ER_DUP_ENTRY:
            raise ValueError("Ese correo ya está registrado") from exc
        raise

    finally:
        cursor.close()
        conn.close()
