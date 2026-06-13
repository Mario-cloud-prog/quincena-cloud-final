# Integrante 3 — Datos, Pub/Sub y BigQuery ML

Este documento registra los comandos usados por el Integrante 3 para implementar el flujo de datos del proyecto **Quincena** usando Pub/Sub, Cloud Run Functions y BigQuery.

El objetivo de esta parte es recibir eventos de gastos, procesarlos con un worker y guardarlos en BigQuery para análisis, pronósticos y detección de anomalías.

---

## 1. Configuración inicial del proyecto

Se configuró el proyecto activo en Cloud Shell.

```bash
cd ~/quincena-cloud-final
gcloud config set project quincena-final-2026
```

---

## 2. Activación de APIs necesarias

Se activaron las APIs necesarias para Pub/Sub, BigQuery, Cloud Run Functions, Cloud Build y Artifact Registry.

```bash
gcloud services enable \
  pubsub.googleapis.com \
  bigquery.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

---

## 3. Creación del tópico Pub/Sub

Se creó un tópico de Pub/Sub para recibir eventos de gastos.

```bash
gcloud pubsub topics create gastos-topic
```

Verificación:

```bash
gcloud pubsub topics list
```

Resultado esperado:

```txt
name: projects/quincena-final-2026/topics/gastos-topic
```

---

## 4. Creación del dataset en BigQuery

Se creó el dataset de analítica en BigQuery.

```bash
bq --location=US mk \
  --dataset \
  quincena-final-2026:quincena_analytics
```

Verificación:

```bash
bq ls quincena-final-2026:
```

Resultado esperado:

```txt
quincena_analytics
```

---

## 5. Creación de tablas en BigQuery

Se crearon tres tablas principales:

- `gastos_eventos`: almacena eventos recibidos desde Pub/Sub.
- `pronosticos`: almacena resultados de proyección.
- `anomalias`: almacena gastos detectados como inusuales.

### Tabla gastos_eventos

```bash
bq mk \
  --table \
  quincena-final-2026:quincena_analytics.gastos_eventos \
  usuario_id:INTEGER,monto:FLOAT,categoria:STRING,fecha:DATE,created_at:TIMESTAMP
```

### Tabla pronosticos

```bash
bq mk \
  --table \
  quincena-final-2026:quincena_analytics.pronosticos \
  usuario_id:INTEGER,mes:STRING,gastado:FLOAT,proyectado:FLOAT,normal_mensual:FLOAT,safe_to_spend:FLOAT,created_at:TIMESTAMP
```

### Tabla anomalias

```bash
bq mk \
  --table \
  quincena-final-2026:quincena_analytics.anomalias \
  usuario_id:INTEGER,monto:FLOAT,categoria:STRING,fecha:DATE,motivo:STRING,created_at:TIMESTAMP
```

Verificación:

```bash
bq ls quincena-final-2026:quincena_analytics
```

Resultado esperado:

```txt
anomalias
gastos_eventos
pronosticos
```

---

## 6. Creación del worker Pub/Sub a BigQuery

Se creó la carpeta del worker.

```bash
cd ~/quincena-cloud-final
mkdir -p worker
```

Se creó el archivo de dependencias:

```bash
cat > worker/requirements.txt << 'EOF'
functions-framework
google-cloud-bigquery
EOF
```

Se creó el archivo principal del worker:

```bash
cat > worker/main.py << 'EOF'
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
EOF
```

Verificación:

```bash
ls -la worker
```

Resultado esperado:

```txt
main.py
requirements.txt
```

---

## 7. Subida del worker a GitHub

Se agregaron únicamente los archivos del worker para evitar subir archivos locales sensibles.

```bash
git add worker/main.py worker/requirements.txt
git commit -m "Agrega worker PubSub a BigQuery"
git push
```

---

## 8. Creación de .gitignore

Se agregó un archivo `.gitignore` para evitar subir variables de entorno, entornos virtuales y caché de Python.

```bash
cat > .gitignore << 'EOF'
# Variables de entorno
.env
backend/.env

# Entornos virtuales
venv/
backend/venv/

# Cache de Python
__pycache__/
backend/__pycache__/
*.pyc

# Logs y temporales
*.log
.DS_Store
EOF
```

Se subió a GitHub:

```bash
git add .gitignore
git commit -m "Agrega gitignore para archivos locales"
git push
```

---

## 9. Despliegue del worker como Cloud Run Function

Se desplegó el worker como función de segunda generación conectada al tópico `gastos-topic`.

```bash
gcloud functions deploy gastos-worker \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=worker \
  --entry-point=pubsub_to_bigquery \
  --trigger-topic=gastos-topic \
  --set-env-vars PROJECT_ID=quincena-final-2026,DATASET_ID=quincena_analytics,TABLE_ID=gastos_eventos
```

Durante el despliegue se activó la API de Cloud Functions cuando Google Cloud lo solicitó.

Resultado esperado:

```txt
state: ACTIVE
url: https://us-central1-quincena-final-2026.cloudfunctions.net/gastos-worker
```

---

## 10. Permisos necesarios para desplegar la función

Durante el despliegue fue necesario otorgar permisos a la cuenta de servicio de Compute Engine usada por Cloud Build y Cloud Run Functions.

### Permiso para construir funciones

```bash
gcloud projects add-iam-policy-binding quincena-final-2026 \
  --member=serviceAccount:533093663517-compute@developer.gserviceaccount.com \
  --role=roles/cloudbuild.builds.builder
```

### Permiso para invocar el servicio interno de Cloud Run

El worker de segunda generación usa Cloud Run internamente. Por eso fue necesario permitir que la cuenta de servicio pudiera invocar el servicio.

```bash
gcloud run services add-iam-policy-binding gastos-worker \
  --region=us-central1 \
  --member="serviceAccount:533093663517-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Permisos para escribir y consultar BigQuery

```bash
gcloud projects add-iam-policy-binding quincena-final-2026 \
  --member="serviceAccount:533093663517-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

```bash
gcloud projects add-iam-policy-binding quincena-final-2026 \
  --member="serviceAccount:533093663517-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

---

## 11. Prueba del flujo Pub/Sub a BigQuery

Se publicó un mensaje de prueba en Pub/Sub.

```bash
gcloud pubsub topics publish gastos-topic \
  --message='{"usuario_id":1,"monto":55.75,"categoria":"cafe","fecha":"2026-06-13"}'
```

Después de esperar unos segundos, se consultó BigQuery.

```bash
bq query --use_legacy_sql=false \
'SELECT usuario_id, monto, categoria, fecha, created_at
 FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
 ORDER BY created_at DESC
 LIMIT 5'
```

Resultado esperado:

```txt
usuario_id | monto | categoria | fecha
1          | 55.75 | cafe      | 2026-06-13
```

Esto confirmó el flujo:

```txt
Pub/Sub → Cloud Run Function / worker → BigQuery
```

---

## 12. Archivo de consultas de BigQuery

Se creó el archivo:

```txt
analytics/consultas_bigquery.sql
```

Este archivo contiene consultas para:

- ver eventos recientes;
- calcular gasto total;
- calcular gasto por categoría;
- calcular gasto diario;
- detectar anomalías;
- insertar anomalías;
- insertar pronósticos simples;
- crear un modelo ARIMA_PLUS con BigQuery ML;
- consultar pronósticos y anomalías.

Commit usado:

```txt
Agrega consultas de BigQuery ML
```

---

## 13. Prueba de proyección mensual simple

Se insertó un pronóstico simple en la tabla `pronosticos`.

```bash
bq query --use_legacy_sql=false \
'INSERT INTO `quincena-final-2026.quincena_analytics.pronosticos`
  (usuario_id, mes, gastado, proyectado, normal_mensual, safe_to_spend, created_at)
SELECT
  usuario_id,
  FORMAT_DATE("%Y-%m", CURRENT_DATE()) AS mes,
  ROUND(SUM(monto), 2) AS gastado,
  ROUND(
    SUM(monto) / EXTRACT(DAY FROM CURRENT_DATE())
    * EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE())),
    2
  ) AS proyectado,
  6900.00 AS normal_mensual,
  ROUND(
    GREATEST(
      6900.00 - (
        SUM(monto) / EXTRACT(DAY FROM CURRENT_DATE())
        * EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE()))
      ),
      0
    ),
    2
  ) AS safe_to_spend,
  CURRENT_TIMESTAMP() AS created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
WHERE EXTRACT(MONTH FROM fecha) = EXTRACT(MONTH FROM CURRENT_DATE())
  AND EXTRACT(YEAR FROM fecha) = EXTRACT(YEAR FROM CURRENT_DATE())
GROUP BY usuario_id'
```

Verificación:

```bash
bq query --use_legacy_sql=false \
'SELECT *
 FROM `quincena-final-2026.quincena_analytics.pronosticos`
 ORDER BY created_at DESC
 LIMIT 5'
```

Resultado obtenido:

```txt
usuario_id: 1
mes: 2026-06
gastado: 111.5
proyectado: 257.31
normal_mensual: 6900.0
safe_to_spend: 6642.69
```

---

## 14. Prueba de detección de anomalías

Primero se ejecutó una regla conservadora:

```txt
gasto > promedio + 2 desviaciones estándar
```

Con pocos datos, no detectó anomalías. Esto es esperado porque el gasto extremo puede inflar el promedio y la desviación estándar.

Para demostrar la funcionalidad con pocos datos, se publicó un gasto alto de prueba:

```bash
gcloud pubsub topics publish gastos-topic \
  --message='{"usuario_id":1,"monto":2500.00,"categoria":"emergencia","fecha":"2026-06-13"}'
```

Se verificó que llegara a BigQuery:

```bash
bq query --use_legacy_sql=false \
'SELECT usuario_id, monto, categoria, fecha, created_at
 FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
 ORDER BY created_at DESC
 LIMIT 5'
```

Resultado esperado:

```txt
usuario_id | monto  | categoria
1          | 2500.0 | emergencia
```

Después se usó una regla ajustada para demo:

```txt
gasto > promedio + 1 desviación estándar
```

Consulta usada:

```bash
bq query --use_legacy_sql=false \
'INSERT INTO `quincena-final-2026.quincena_analytics.anomalias`
  (usuario_id, monto, categoria, fecha, motivo, created_at)
SELECT
  g.usuario_id,
  g.monto,
  g.categoria,
  g.fecha,
  "Gasto mayor al promedio + 1 desviación estándar" AS motivo,
  CURRENT_TIMESTAMP() AS created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos` AS g
JOIN (
  SELECT
    usuario_id,
    AVG(monto) AS promedio,
    STDDEV(monto) AS desviacion
  FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
  GROUP BY usuario_id
) AS stats
ON g.usuario_id = stats.usuario_id
WHERE g.monto > stats.promedio + 1 * stats.desviacion'
```

Verificación:

```bash
bq query --use_legacy_sql=false \
'SELECT *
 FROM `quincena-final-2026.quincena_analytics.anomalias`
 ORDER BY created_at DESC
 LIMIT 5'
```

Resultado obtenido:

```txt
usuario_id: 1
monto: 2500.0
categoria: emergencia
motivo: Gasto mayor al promedio + 1 desviación estándar
```

---

## 15. Nota sobre el umbral estadístico

La regla `promedio + 2 desviaciones estándar` es más conservadora y suele marcar valores muy extremos.

La regla `promedio + 1.6 desviaciones estándar` puede interpretarse como una aproximación al percentil 95 si se asume normalidad en una prueba de una cola.

Para la demo se usó `promedio + 1 desviación estándar` porque había muy pocos datos. Con pocos registros, un gasto extremo puede inflar el promedio y la desviación estándar, haciendo más difícil detectar anomalías. En producción conviene usar más historial o métodos más robustos.

---

## 16. BigQuery ML

Se dejó preparada una consulta para crear un modelo de BigQuery ML usando ARIMA_PLUS.

Archivo:

```txt
analytics/consultas_bigquery.sql
```

Consulta principal:

```sql
CREATE OR REPLACE MODEL `quincena-final-2026.quincena_analytics.modelo_gasto_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='fecha',
  TIME_SERIES_DATA_COL='gasto_diario',
  TIME_SERIES_ID_COL='usuario_id',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT
  usuario_id,
  fecha,
  SUM(monto) AS gasto_diario
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
GROUP BY usuario_id, fecha;
```

Consulta de pronóstico:

```sql
SELECT
  *
FROM ML.FORECAST(
  MODEL `quincena-final-2026.quincena_analytics.modelo_gasto_arima`,
  STRUCT(30 AS horizon, 0.8 AS confidence_level)
);
```

Nota: ARIMA_PLUS necesita más datos históricos para producir un pronóstico útil. En el proyecto se deja como evidencia de integración con BigQuery ML y como base para crecimiento futuro.

---

## 17. Estado final del Integrante 3

El Integrante 3 completó:

- Activación de APIs necesarias.
- Creación de tópico Pub/Sub.
- Creación de dataset en BigQuery.
- Creación de tablas `gastos_eventos`, `pronosticos` y `anomalias`.
- Creación del worker `worker/main.py`.
- Despliegue del worker como Cloud Run Function Gen 2.
- Configuración de permisos IAM necesarios.
- Flujo funcionando de Pub/Sub a BigQuery.
- Inserción de eventos de gastos.
- Consulta de pronóstico simple.
- Detección de anomalías.
- Archivo `analytics/consultas_bigquery.sql` con consultas de analítica y BigQuery ML.
