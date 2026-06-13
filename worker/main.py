"""
Worker de datos para el proyecto Quincena.

Este worker recibe eventos desde Pub/Sub y guarda los gastos en BigQuery.
Forma parte del Integrante 3: Datos, Pub/Sub y BigQuery ML.
"""

import base64
import json
import os
from datetime import datetime, timezone

from google.cloud import bigquery


PROJECT_ID = os.getenv("PROJECT_ID", "quincena-final-2026")
DATASET_ID = os.getenv("DATASET_ID", "quincena_analytics")
TABLE_ID = os.getenv("TABLE_ID", "gastos_eventos")

client = bigquery.Client(project=PROJECT_ID)


def pubsub_to_bigquery(event, context):
    """
    Función ejecutada por Pub/Sub.

    Pub/Sub envía el mensaje codificado en base64.
    El worker lo decodifica, lo convierte a JSON y lo inserta en BigQuery.
    """
    if "data" not in event:
        print("Evento sin data. No se procesa.")
        return

    payload = base64.b64decode(event["data"]).decode("utf-8")
    gasto = json.loads(payload)

    row = {
        "usuario_id": int(gasto["usuario_id"]),
        "monto": float(gasto["monto"]),
        "categoria": gasto["categoria"],
        "fecha": gasto["fecha"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    errors = client.insert_rows_json(table_ref, [row])

    if errors:
        raise RuntimeError(f"Error insertando en BigQuery: {errors}")

    print(f"Gasto insertado en BigQuery: {row}")
