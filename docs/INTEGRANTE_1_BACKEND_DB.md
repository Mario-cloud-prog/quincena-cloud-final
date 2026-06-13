# Integrante 1 — Backend y Base de Datos

Este documento registra los comandos usados por el Integrante 1 para crear, probar y verificar el backend y la base de datos del proyecto **Quincena**.

---

## 1. Configuración del proyecto activo

Se configuró el proyecto activo en Cloud Shell para evitar crear recursos en otro proyecto de Google Cloud.

```bash
gcloud config set project quincena-final-2026
```

Verificación:

```bash
gcloud config get-value project
```

Resultado esperado:

```txt
quincena-final-2026
```

---

## 2. Clonar el repositorio

Se clonó el repositorio de GitHub en Cloud Shell para probar el backend.

```bash
git clone https://github.com/Mario-cloud-prog/quincena-cloud-final.git
cd quincena-cloud-final/backend
```

Verificación de archivos:

```bash
ls -la
```

Archivos esperados:

```txt
.env.example
db.py
main.py
requirements.txt
schema.sql
```

---

## 3. Crear entorno virtual e instalar dependencias

Se creó un entorno virtual para instalar las dependencias del backend sin afectar el sistema base.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Crear Cloud SQL MySQL

Se activó la API de Cloud SQL.

```bash
gcloud services enable sqladmin.googleapis.com
```

Se creó la instancia MySQL:

```bash
gcloud sql instances create quincena-mysql \
  --database-version=MYSQL_8_0 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB \
  --root-password=QuincenaRoot123!
```

Datos de la instancia:

```txt
Instancia: quincena-mysql
Motor: MySQL 8.0
Región: us-central1
Base de datos: quincena
```

---

## 5. Crear base de datos

```bash
gcloud sql databases create quincena \
  --instance=quincena-mysql
```

---

## 6. Crear usuario de base de datos

Se creó un usuario específico para la aplicación en lugar de usar `root`.

```bash
gcloud sql users create quincena_user \
  --instance=quincena-mysql \
  --password=quincena123
```

Usuario usado por FastAPI:

```txt
DB_USER=quincena_user
```

---

## 7. Conectarse a Cloud SQL

```bash
gcloud sql connect quincena-mysql --user=quincena_user
```

Dentro de MySQL:

```sql
USE quincena;
SHOW TABLES;
SELECT * FROM usuarios;
```

---

## 8. Verificación de tablas

Se verificó que existieran las tablas principales:

```txt
gastos
pronosticos
usuarios
```

También se verificó el usuario demo:

```txt
id: 1
nombre: Usuario Demo
ingreso_mensual: 12000.00
presupuesto_mensual: 6900.00
```

---

## 9. Configuración local del backend

Se creó un archivo `.env` local usando como base `.env.example`.

```bash
cp .env.example .env
```

Configuración usada para pruebas en Cloud Shell con Cloud SQL Auth Proxy:

```txt
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=quincena_user
DB_PASSWORD=quincena123
DB_NAME=quincena
```

El archivo `.env` real no se sube a GitHub.

---

## 10. Cloud SQL Auth Proxy

Se usó Cloud SQL Auth Proxy para que FastAPI pudiera conectarse a Cloud SQL desde Cloud Shell.

```bash
cloud-sql-proxy quincena-final-2026:us-central1:quincena-mysql --port 3306
```

---

## 11. Ejecutar FastAPI con Uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## 12. Probar endpoint de salud

```bash
curl http://localhost:8080/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

---

## 13. Probar registro de gasto

```bash
curl -X POST http://localhost:8080/gastos \
  -H "Content-Type: application/json" \
  -d '{"usuario_id":1,"monto":120.50,"categoria":"comida","fecha":"2026-06-13"}'
```

Respuesta obtenida:

```json
{
  "message": "Gasto registrado correctamente",
  "gasto": {
    "id": 1,
    "usuario_id": 1,
    "monto": 120.5,
    "categoria": "comida",
    "fecha": "2026-06-13"
  }
}
```

---

## 14. Probar dashboard

```bash
curl "http://localhost:8080/dashboard?usuario_id=1"
```

Respuesta obtenida:

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

---

## 15. Detener Cloud SQL para reducir costos

Al terminar la sesión de trabajo, se detuvo Cloud SQL para reducir costos.

```bash
gcloud sql instances patch quincena-mysql --activation-policy=NEVER
```

Verificación:

```bash
gcloud sql instances describe quincena-mysql \
  --format="value(settings.activationPolicy,state)"
```

Resultado obtenido:

```txt
NEVER
STOPPED
```

Para volver a encender la instancia:

```bash
gcloud sql instances patch quincena-mysql --activation-policy=ALWAYS
```

---

## Estado final del Integrante 1

El Integrante 1 completó:

* Backend FastAPI.
* Conexión a Cloud SQL MySQL.
* Esquema de base de datos.
* Código comentado.
* Pruebas funcionales de `/health`, `/gastos` y `/dashboard`.
