# Integrante 4 — Frontend, Demo y Presentación

Este documento registra las pruebas, evidencias y pasos de demo realizados por el Integrante 4 para presentar el funcionamiento final del proyecto **Quincena**.

El objetivo de esta parte es comprobar que la API pública funciona, que el usuario puede registrar gastos y que el dashboard se actualiza con los datos almacenados en Cloud SQL.

---

## 1. URL pública de la API

El backend FastAPI fue desplegado en Cloud Run y quedó disponible públicamente en:

```txt
https://quincena-api-533093663517.us-central1.run.app
```

Esta URL permite probar los endpoints principales del sistema.

---

## 2. Prueba de salud del servicio

Se verificó que la API estuviera activa usando el endpoint `/health`.

```bash
curl https://quincena-api-533093663517.us-central1.run.app/health
```

Respuesta obtenida:

```json
{"status":"ok"}
```

Esto confirma que el servicio en Cloud Run está activo y respondiendo.

---

## 3. Consulta inicial del dashboard

Se consultó el dashboard del usuario de prueba con `usuario_id=1`.

```bash
curl "https://quincena-api-533093663517.us-central1.run.app/dashboard?usuario_id=1"
```

Respuesta obtenida antes de registrar el gasto de demo:

```json
{
  "usuario_id": 1,
  "proyectado": 278.08,
  "normal_mensual": 6900.0,
  "gastado": 120.5,
  "safe_to_spend": 6621.92,
  "desglose": [
    {
      "categoria": "comida",
      "total": 120.5
    }
  ],
  "anomalias": []
}
```

Esta consulta muestra:

- gasto acumulado del mes;
- proyección mensual;
- presupuesto mensual normal;
- dinero seguro para gastar;
- desglose por categoría;
- lista de anomalías.

---

## 4. Registro de gasto desde la API pública

Se registró un gasto nuevo usando el endpoint `POST /gastos`.

```bash
curl -X POST https://quincena-api-533093663517.us-central1.run.app/gastos \
  -H "Content-Type: application/json" \
  -d '{"usuario_id":1,"monto":95.00,"categoria":"demo_frontend","fecha":"2026-06-13"}'
```

Respuesta obtenida:

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

Esto confirma que la API puede recibir datos nuevos y guardarlos en la base de datos Cloud SQL.

---

## 5. Consulta del dashboard después del gasto

Después de registrar el gasto, se volvió a consultar el dashboard.

```bash
curl "https://quincena-api-533093663517.us-central1.run.app/dashboard?usuario_id=1"
```

Respuesta obtenida:

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

La respuesta demuestra que el dashboard se actualizó correctamente:

```txt
gastado antes: 120.5
gasto nuevo: 95.0
gastado después: 215.5
```

También se actualizó el desglose por categoría:

```txt
comida = 120.5
demo_frontend = 95.0
```

---

## 6. Evidencia de funcionamiento

La demo confirma que:

- Cloud Run responde públicamente.
- FastAPI está funcionando.
- El endpoint `/health` responde correctamente.
- El endpoint `/gastos` permite registrar gastos.
- El endpoint `/dashboard` consulta datos reales.
- Cloud Run está conectado a Cloud SQL.
- El dashboard refleja los cambios después de insertar datos.

---

## 7. Flujo demostrado

El flujo demostrado por el Integrante 4 fue:

```txt
Usuario / Frontend / curl
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

## 8. Relación con los otros integrantes

El Integrante 4 usa los componentes creados por los demás integrantes:

### Integrante 1 — Backend y Base de Datos

Aporta:

- código FastAPI;
- endpoints `/health`, `/gastos` y `/dashboard`;
- base de datos MySQL;
- tablas `usuarios`, `gastos` y `pronosticos`.

### Integrante 2 — Cloud / DevOps

Aporta:

- Dockerfile;
- Cloud Build;
- Artifact Registry;
- Cloud Run;
- Secret Manager;
- conexión de Cloud Run con Cloud SQL.

### Integrante 3 — Datos, Pub/Sub y BigQuery ML

Aporta:

- Pub/Sub;
- worker;
- BigQuery;
- tablas de analítica;
- pronósticos;
- anomalías;
- consultas BigQuery ML.

### Integrante 4 — Frontend, Demo y Presentación

Aporta:

- pruebas de la API pública;
- evidencia de funcionamiento;
- demo final;
- explicación del flujo;
- documentación para presentación.

---

## 9. Propuesta de frontend sencillo

Aunque la demo se hizo con `curl`, el frontend puede representar los datos del dashboard con tarjetas simples.

Elementos sugeridos:

```txt
Tarjeta 1: Gasto acumulado
Tarjeta 2: Proyección mensual
Tarjeta 3: Safe to spend
Tarjeta 4: Presupuesto mensual normal
Gráfica o lista: Desglose por categoría
Lista: Anomalías detectadas
Formulario: Registrar nuevo gasto
```

Endpoints que consumiría el frontend:

```txt
GET /dashboard?usuario_id=1
POST /gastos
```

---

## 10. Guion corto de demo

Guion sugerido para presentar:

```txt
1. Abrimos la URL pública de Cloud Run.
2. Probamos /health para demostrar que la API está viva.
3. Consultamos /dashboard?usuario_id=1 para ver el estado financiero actual.
4. Registramos un gasto nuevo con POST /gastos.
5. Consultamos nuevamente el dashboard.
6. Mostramos que el gasto acumulado y el desglose cambiaron.
7. Explicamos que los datos vienen desde Cloud SQL.
8. Explicamos que en paralelo el proyecto también tiene Pub/Sub, BigQuery y BigQuery ML para analítica.
```

---

## 11. Comandos usados en la demo

### Health check

```bash
curl https://quincena-api-533093663517.us-central1.run.app/health
```

### Dashboard inicial

```bash
curl "https://quincena-api-533093663517.us-central1.run.app/dashboard?usuario_id=1"
```

### Registrar gasto de demo

```bash
curl -X POST https://quincena-api-533093663517.us-central1.run.app/gastos \
  -H "Content-Type: application/json" \
  -d '{"usuario_id":1,"monto":95.00,"categoria":"demo_frontend","fecha":"2026-06-13"}'
```

### Dashboard actualizado

```bash
curl "https://quincena-api-533093663517.us-central1.run.app/dashboard?usuario_id=1"
```

---

## 12. Servicios de Google Cloud demostrados en la presentación

El proyecto final usa los siguientes servicios:

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

## 13. Arquitectura general para explicar

Arquitectura resumida:

```txt
Cliente / Demo
   ↓
Cloud Run
   ↓
FastAPI
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

## 14. Evidencias sugeridas para capturas

Para la entrega o presentación se recomiendan capturas de:

- Cloud Run con el servicio `quincena-api`.
- Respuesta de `/health`.
- Respuesta de `/dashboard`.
- Respuesta de `POST /gastos`.
- Cloud SQL con instancia `quincena-mysql`.
- BigQuery con dataset `quincena_analytics`.
- Tabla `gastos_eventos`.
- Tabla `pronosticos`.
- Tabla `anomalias`.
- Repositorio GitHub con documentación por integrante.

---

## 15. Estado final del Integrante 4

El Integrante 4 completó:

- Prueba pública de `/health`.
- Prueba pública de `/dashboard`.
- Registro de gasto usando `POST /gastos`.
- Verificación de actualización del dashboard.
- Documentación de evidencia de demo.
- Guion de presentación.
- Resumen de arquitectura para explicar el proyecto.
