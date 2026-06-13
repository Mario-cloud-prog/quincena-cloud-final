# Quincena — Proyecto Final de Cloud Computing

**Quincena** es una aplicación de finanzas personales que ayuda al usuario a responder una pregunta concreta:

> ¿Voy a llegar a fin de mes?

El sistema permite registrar gastos, consultar un dashboard financiero, proyectar el gasto mensual, detectar anomalías y almacenar eventos para análisis usando servicios de Google Cloud.

---

## Descripción general

El usuario registra sus gastos diarios y la aplicación muestra un dashboard con:

* gasto acumulado del mes;
* proyección de gasto mensual;
* presupuesto mensual normal;
* dinero seguro para gastar;
* desglose por categoría;
* detección de gastos anómalos.

El proyecto integra backend, frontend, base de datos, despliegue serverless, mensajería asíncrona, analítica en BigQuery y preparación de BigQuery ML.

---

## Arquitectura general

```txt
Frontend HTML
        ↓
API pública en Cloud Run
        ↓
Backend FastAPI
        ↓
Cloud SQL MySQL

Pub/Sub
        ↓
Cloud Run Function / Worker
        ↓
BigQuery
        ↓
Consultas analíticas / BigQuery ML
```

---

## Servicios de Google Cloud utilizados

El proyecto usa los siguientes servicios:

```txt
Cloud SQL
Cloud Run
Secret Manager
Artifact Registry
Cloud Build
Pub/Sub
Cloud Run Functions
BigQuery
BigQuery ML
IAM
```

---

## Estructura del repositorio

```txt
quincena-cloud-final/
│
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── requirements.txt
│   ├── schema.sql
│   └── .env.example
│
├── cloud/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── deploy.sh
│
├── frontend/
│   └── index.html
│
├── worker/
│   ├── main.py
│   └── requirements.txt
│
├── analytics/
│   └── consultas_bigquery.sql
│
├── docs/
│   ├── COMANDOS_GCP.md
│   ├── INTEGRANTE_1_BACKEND_DB.md
│   ├── INTEGRANTE_2_CLOUD_RUN.md
│   ├── INTEGRANTE_3_DATOS_ML.md
│   └── INTEGRANTE_4_FRONTEND_DEMO.md
│
├── .gitignore
└── README.md
```

---

## Backend FastAPI

El backend está construido con **FastAPI** y expone endpoints para registrar gastos y consultar el dashboard.

Endpoints principales:

```txt
GET  /health
POST /gastos
GET  /dashboard?usuario_id=1
```

También se habilitó CORS para que el frontend pueda consumir la API pública desde el navegador.

CORS significa **Cross-Origin Resource Sharing**, es decir, el mecanismo que permite o bloquea peticiones entre dominios distintos desde el navegador.

En `backend/main.py` se agregó:

```python
from fastapi.middleware.cors import CORSMiddleware
```

y:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Base de datos

La base de datos usa **Cloud SQL MySQL**.

Tablas principales:

```txt
usuarios
gastos
pronosticos
```

El backend se conecta a Cloud SQL desde Cloud Run usando socket Unix:

```txt
/cloudsql/quincena-final-2026:us-central1:quincena-mysql
```

---

## API pública

La API se desplegó en Cloud Run:

```txt
https://quincena-api-533093663517.us-central1.run.app
```

### Health check

```bash
curl https://quincena-api-533093663517.us-central1.run.app/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

### Consultar dashboard

```bash
curl "https://quincena-api-533093663517.us-central1.run.app/dashboard?usuario_id=1"
```

Ejemplo de respuesta:

```json
{
  "usuario_id": 1,
  "proyectado": 497.31,
  "normal_mensual": 6900.0,
  "gastado": 215.5,
  "safe_to_spend": 6402.69,
  "desglose": [
    {
      "categoria": "comida",
      "total": 120.5
    },
    {
      "categoria": "demo_frontend",
      "total": 95.0
    }
  ],
  "anomalias": []
}
```

### Registrar gasto

```bash
curl -X POST https://quincena-api-533093663517.us-central1.run.app/gastos \
  -H "Content-Type: application/json" \
  -d '{"usuario_id":1,"monto":95.00,"categoria":"demo_frontend","fecha":"2026-06-13"}'
```

Ejemplo de respuesta:

```json
{
  "message": "Gasto registrado correctamente",
  "gasto": {
    "id": 2,
    "usuario_id": 1,
    "monto": 95.0,
    "categoria": "demo_frontend",
    "fecha": "2026-06-13"
  }
}
```

---

## Frontend demo

Además de las pruebas con `curl`, el proyecto incluye un frontend básico en HTML, CSS y JavaScript.

Archivo:

```txt
frontend/index.html
```

El frontend consume la API pública desplegada en Cloud Run:

```txt
https://quincena-api-533093663517.us-central1.run.app
```

Funcionalidades del frontend:

* consulta el dashboard del usuario;
* muestra gasto acumulado;
* muestra proyección mensual;
* muestra safe to spend;
* muestra presupuesto mensual normal;
* muestra desglose por categoría;
* muestra anomalías;
* permite registrar un gasto nuevo desde formulario;
* actualiza el dashboard después de registrar un gasto.

Para probarlo desde Cloud Shell:

```bash
python3 -m http.server 8081 --directory frontend
```

Después se abre **Web Preview** en el puerto:

```txt
8081
```

Evidencia de funcionamiento:

```txt
Gastado: $215.50
Proyectado: $497.31
Safe to spend: $6402.69
Presupuesto normal: $6900.00
```

Esto confirma el flujo:

```txt
Frontend HTML
      ↓
API pública en Cloud Run
      ↓
Backend FastAPI
      ↓
Cloud SQL MySQL
      ↓
Dashboard actualizado
```

---

## Flujo de datos con Pub/Sub y BigQuery

Además del backend principal, el proyecto incluye un flujo de datos asíncrono:

```txt
Pub/Sub → Cloud Run Function / Worker → BigQuery
```

Se creó el tópico:

```txt
gastos-topic
```

El worker recibe eventos de gastos y los inserta en BigQuery.

Dataset:

```txt
quincena_analytics
```

Tablas:

```txt
gastos_eventos
pronosticos
anomalias
```

---

## Prueba de Pub/Sub a BigQuery

Publicar evento:

```bash
gcloud pubsub topics publish gastos-topic \
  --message='{"usuario_id":1,"monto":55.75,"categoria":"cafe","fecha":"2026-06-13"}'
```

Consultar BigQuery:

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

---

## Pronóstico y anomalías

El proyecto incluye:

* proyección simple mensual;
* detección de anomalías usando promedio y desviación estándar;
* consultas preparadas para BigQuery ML con ARIMA_PLUS.

Archivo de consultas:

```txt
analytics/consultas_bigquery.sql
```

### Proyección simple

La proyección simple estima:

```txt
gasto proyectado = gasto acumulado / día actual * días del mes
```

Ejemplo de resultado guardado en BigQuery:

```txt
usuario_id: 1
mes: 2026-06
gastado: 111.5
proyectado: 257.31
normal_mensual: 6900.0
safe_to_spend: 6642.69
```

### Detección de anomalías

Para la demo se usó una regla ajustada:

```txt
gasto > promedio + 1 desviación estándar
```

Ejemplo detectado:

```txt
usuario_id: 1
monto: 2500.0
categoria: emergencia
motivo: Gasto mayor al promedio + 1 desviación estándar
```

Nota: con pocos datos, un gasto extremo puede inflar el promedio y la desviación estándar. En producción conviene usar más historial o métodos más robustos.

---

## BigQuery ML

Se dejó preparada una consulta para crear un modelo ARIMA_PLUS en BigQuery ML.

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

Nota: ARIMA_PLUS necesita más datos históricos para generar pronósticos útiles. En este proyecto se deja como evidencia de integración con BigQuery ML y como base para crecimiento futuro.

---

## Seguridad

El proyecto evita subir credenciales reales al repositorio.

Se usa:

```txt
Secret Manager
.gitignore
.env.example
IAM
```

El archivo real:

```txt
backend/.env
```

no debe subirse a GitHub.

La contraseña de la base de datos se maneja mediante Secret Manager:

```txt
db-password
```

---

## Documentación por integrante

La documentación detallada está en la carpeta `docs/`.

### Integrante 1 — Backend y Base de Datos

```txt
docs/INTEGRANTE_1_BACKEND_DB.md
```

Incluye:

* FastAPI;
* endpoints principales;
* Cloud SQL MySQL;
* usuario de base de datos;
* tablas;
* conexión local;
* pruebas del backend.

### Integrante 2 — Cloud / DevOps

```txt
docs/INTEGRANTE_2_CLOUD_RUN.md
```

Incluye:

* Dockerfile;
* Artifact Registry;
* Cloud Build;
* Cloud Run;
* Secret Manager;
* conexión Cloud Run a Cloud SQL;
* permisos IAM;
* despliegue final.

### Integrante 3 — Datos, Pub/Sub y BigQuery ML

```txt
docs/INTEGRANTE_3_DATOS_ML.md
```

Incluye:

* Pub/Sub;
* worker;
* Cloud Run Functions;
* BigQuery;
* tablas de analítica;
* pronósticos;
* anomalías;
* BigQuery ML.

### Integrante 4 — Frontend, Demo y Presentación

```txt
docs/INTEGRANTE_4_FRONTEND_DEMO.md
```

Incluye:

* pruebas públicas de la API;
* registro de gastos;
* verificación del dashboard;
* frontend visual en `frontend/index.html`;
* corrección de CORS;
* guion de demo;
* evidencias sugeridas;
* arquitectura para presentación.

### Índice general de comandos

```txt
docs/COMANDOS_GCP.md
```

Resume los documentos por integrante y centraliza la referencia de comandos usados.

---

## Cómo correr localmente

Entrar a la carpeta del backend:

```bash
cd backend
```

Crear o activar entorno virtual:

```bash
python -m venv venv
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear archivo `.env` local basado en `.env.example`.

Ejemplo:

```txt
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=quincena_user
DB_PASSWORD=quincena123
DB_NAME=quincena
```

Ejecutar FastAPI localmente:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

Probar el frontend localmente:

```bash
python3 -m http.server 8081 --directory frontend
```

Abrir Web Preview en el puerto:

```txt
8081
```

---

## Cómo desplegar

El script de despliegue está en:

```txt
cloud/deploy.sh
```

Ejecutar:

```bash
bash cloud/deploy.sh
```

Este script:

* configura el proyecto;
* activa APIs necesarias;
* construye la imagen Docker;
* sube la imagen a Artifact Registry;
* despliega el servicio en Cloud Run;
* configura conexión con Cloud SQL;
* usa Secret Manager para la contraseña.

---

## Estado final del proyecto

El proyecto final demuestra:

```txt
Frontend HTML funcionando ✅
Backend con FastAPI ✅
Base de datos desacoplada con Cloud SQL ✅
Despliegue serverless con Cloud Run ✅
Imagen Docker en Artifact Registry ✅
Build automatizado con Cloud Build ✅
Credenciales protegidas con Secret Manager ✅
Mensajería asíncrona con Pub/Sub ✅
Worker con Cloud Run Function ✅
Analítica con BigQuery ✅
Preparación de BigQuery ML ✅
Documentación completa por integrante ✅
Demo pública funcionando ✅
```

---

## Limpieza de recursos

Para reducir costos después de la demo, se puede apagar Cloud SQL:

```bash
gcloud sql instances patch quincena-mysql --activation-policy=NEVER
```

Para volver a encenderlo:

```bash
gcloud sql instances patch quincena-mysql --activation-policy=ALWAYS
```

Otros recursos como Cloud Run, Pub/Sub, BigQuery y Artifact Registry deben revisarse antes de eliminarlos para no perder evidencia del proyecto.


