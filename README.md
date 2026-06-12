Este proyecto demuestra:

Backend con FastAPI.
Base de datos desacoplada con Cloud SQL MySQL.
Despliegue serverless con Cloud Run.
Comunicación asíncrona con Pub/Sub.
Pronóstico y análisis con BigQuery ML.
Seguridad usando Secret Manager, IAM y VPC Connector.
Escalabilidad con Cloud Run, Pub/Sub y Redis.


# Quincena — Proyecto Final de Cloud Computing

## Descripción

Quincena es una app de finanzas personales que ayuda al usuario a responder una pregunta concreta:

> ¿Voy a llegar a fin de mes?

El usuario registra sus gastos diarios y la aplicación muestra un dashboard con:

- Gasto acumulado del mes.
- Proyección de gasto mensual.
- Dinero seguro restante para gastar.
- Desglose por categoría.
- Detección de gastos inusuales.
- Pronóstico usando BigQuery ML.

Frase principal del proyecto:

> Útil desde el primer día, más inteligente con cada gasto.

---

## Stack tecnológico

- FastAPI
- Cloud Run
- Cloud SQL MySQL
- Pub/Sub
- BigQuery ML
- Secret Manager
- Serverless VPC Access Connector
- Cloud Build
- Memorystore Redis

---

## Project ID de GCP

```txt
quincena-final-2026





Integrantes y responsabilidades

| Integrante   | Rol                     | Responsabilidad                                         |
| ------------ | ----------------------- | ------------------------------------------------------- |
| Integrante 1 | Backend y base de datos | FastAPI, endpoints, Cloud SQL MySQL, schema.sql         |
| Integrante 2 | Cloud / DevOps          | Docker, Cloud Run, VPC Connector, Secret Manager, IAM   |
| Integrante 3 | Ciencia de Datos        | Pub/Sub worker, BigQuery ML, anomalías, reentrenamiento |
| Integrante 4 | Frontend, Pitch y Demo  | index.html, seed_data.sql, README, DEMO.md, pitch       |

Arquitectura general

El usuario accede a la aplicación desde navegador o móvil. La petición llega por HTTPS al backend en Cloud Run, donde corre una API desarrollada con FastAPI.

Cuando el usuario registra un gasto:

FastAPI valida los datos.
El gasto se guarda en Cloud SQL MySQL.
La API publica un evento en Pub/Sub.
Un worker procesa el evento de forma asíncrona.
BigQuery ML calcula pronósticos y anomalías.
Los resultados se guardan/cachean para mostrarse en el dashboard.

La arquitectura separa tres ritmos:

Registro instantáneo del gasto.
Procesamiento asíncrono con Pub/Sub.
Reentrenamiento programado del modelo en BigQuery ML.





Contrato de datos

POST /gastos

Registra un gasto nuevo.

Request:

{
  "usuario_id": 1,
  "monto": 120.50,
  "categoria": "comida",
  "fecha": "2026-06-11"
}

Response:

{
  "message": "Gasto registrado correctamente",
  "gasto": {
    "id": 1,
    "usuario_id": 1,
    "monto": 120.50,
    "categoria": "comida",
    "fecha": "2026-06-11"
  }
}
GET /dashboard?usuario_id=1

Devuelve el resumen financiero del usuario.

Response:

{
  "usuario_id": 1,
  "proyectado": 8400.00,
  "normal_mensual": 6900.00,
  "gastado": 3200.00,
  "safe_to_spend": 1500.00,
  "desglose": [
    {
      "categoria": "comida",
      "total": 1200.00
    }
  ],
  "anomalias": [
    {
      "id": 7,
      "monto": 1200.00,
      "categoria": "transporte",
      "fecha": "2026-06-10"
    }
  ]
}
GET /health

Endpoint para verificar que la API esté funcionando.

Response:

{
  "status": "ok"
}





Modelo de base de datos
Tabla usuarios

| Campo               | Tipo          | Descripción                     |
| ------------------- | ------------- | ------------------------------- |
| id                  | INT           | Identificador del usuario       |
| nombre              | VARCHAR(100)  | Nombre del usuario              |
| ingreso_mensual     | DECIMAL(10,2) | Ingreso mensual aproximado      |
| presupuesto_mensual | DECIMAL(10,2) | Gasto mensual normal o esperado |
| created_at          | TIMESTAMP     | Fecha de creación               |

Tabla gastos

| Campo      | Tipo          | Descripción                      |
| ---------- | ------------- | -------------------------------- |
| id         | INT           | Identificador del gasto          |
| usuario_id | INT           | Usuario asociado al gasto        |
| monto      | DECIMAL(10,2) | Cantidad gastada                 |
| categoria  | VARCHAR(50)   | Categoría elegida por el usuario |
| fecha      | DATE          | Fecha del gasto                  |
| created_at | TIMESTAMP     | Fecha de registro                |

Tabla pronosticos

| Campo          | Tipo          | Descripción                         |
| -------------- | ------------- | ----------------------------------- |
| id             | INT           | Identificador del pronóstico        |
| usuario_id     | INT           | Usuario asociado                    |
| mes            | VARCHAR(7)    | Mes del pronóstico, formato YYYY-MM |
| proyectado     | DECIMAL(10,2) | Gasto proyectado                    |
| normal_mensual | DECIMAL(10,2) | Gasto mensual normal                |
| safe_to_spend  | DECIMAL(10,2) | Dinero seguro restante              |
| mensaje        | VARCHAR(255)  | Mensaje para el dashboard           |
| created_at     | TIMESTAMP     | Fecha de creación                   |



Estructura del repositorio

quincena-cloud-final/
├── README.md
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── schema.sql
│   └── requirements.txt
├── worker/
│   ├── main.py
│   ├── forecast.sql
│   ├── anomaly.sql
│   └── retrain_scheduled_query.sql
├── frontend/
│   └── index.html
├── cloud/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── deploy.sh
│   └── cloudbuild.yaml
├── docs/
│   ├── DEMO.md
│   ├── ARQUITECTURA.md
│   └── CONTRATO_DATOS.md
└── seed/
    └── seed_data.sql



Cómo correr el backend

cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8080

Probar health check:
curl http://localhost:8080/health


Comandos útiles de GCP
Los comandos completos para configurar servicios de Google Cloud están documentados en:

- `cloud/deploy.sh`
- `docs/ARQUITECTURA.md`

Comando para seleccionar el proyecto:

```bash
gcloud config set project quincena-final-2026


