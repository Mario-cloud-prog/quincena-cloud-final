# Comandos utilizados en Google Cloud Platform

Este documento funciona como índice de los comandos usados por cada integrante del proyecto **Quincena**.

## Project ID

```txt
quincena-final-2026
```

---

## Integrante 1 — Backend y Base de Datos

Documento:

```txt
docs/INTEGRANTE_1_BACKEND_DB.md
```

Incluye comandos relacionados con:

* configuración del proyecto;
* creación de Cloud SQL MySQL;
* creación de base de datos `quincena`;
* creación del usuario `quincena_user`;
* conexión a MySQL;
* carga y verificación de `schema.sql`;
* prueba del backend con Uvicorn;
* prueba de endpoints `/health`, `/gastos` y `/dashboard`;
* apagado de Cloud SQL para reducir costos.

---

## Integrante 2 — Cloud / DevOps

Documento:

```txt
docs/INTEGRANTE_2_CLOUD_RUN.md
```

Incluirá comandos relacionados con:

* Secret Manager;
* Artifact Registry;
* Dockerfile;
* Cloud Build;
* Cloud Run;
* conexión de Cloud Run con Cloud SQL;
* variables de entorno;
* despliegue público de la API.

---

## Integrante 3 — Datos, Pub/Sub y BigQuery ML

Documento:

```txt
docs/INTEGRANTE_3_DATOS_ML.md
```

Incluirá comandos relacionados con:

* Pub/Sub;
* Cloud Run Function o worker;
* BigQuery;
* BigQuery ML;
* consultas SQL de pronóstico;
* consultas SQL de anomalías;
* jobs programados o reentrenamiento.

---

## Integrante 4 — Frontend, Demo y Presentación

Documento:

```txt
docs/INTEGRANTE_4_FRONTEND_DEMO.md
```

Incluirá comandos o pasos relacionados con:

* frontend;
* pruebas contra la URL pública de Cloud Run;
* datos demo;
* documentación de demo;
* preparación del pitch;
* evidencia de funcionamiento.

---

## Nota de seguridad

No se deben subir credenciales reales al repositorio.

El archivo real:

```txt
backend/.env
```

no debe subirse a GitHub.

Solo se conserva la plantilla:

```txt
backend/.env.example
```
