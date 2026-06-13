# Integrante 2 — Cloud / DevOps

Este documento registra los comandos usados por el Integrante 2 para construir, publicar y desplegar el backend FastAPI del proyecto **Quincena** en Cloud Run.

---

## 1. Actualizar repositorio local en Cloud Shell

Se descargaron los cambios más recientes del repositorio de GitHub.

```bash
cd ~/quincena-cloud-final
git pull
```

Verificación de archivos principales:

```bash
ls
```

Resultado esperado:

```txt
backend  cloud  docs  README.md
```

---

## 2. Archivos de despliegue creados

Se creó la carpeta `cloud/` con los archivos necesarios para despliegue.

```txt
cloud/Dockerfile
cloud/.dockerignore
cloud/deploy.sh
```

El archivo `Dockerfile` define la imagen Docker del backend FastAPI.

El archivo `.dockerignore` evita subir archivos innecesarios o sensibles a la imagen.

El archivo `deploy.sh` documenta el flujo automatizado de despliegue.

---

## 3. Activar Cloud SQL

Antes de probar o desplegar la aplicación, se encendió la instancia de Cloud SQL.

```bash
gcloud sql instances patch quincena-mysql --activation-policy=ALWAYS
```

Verificación:

```bash
gcloud sql instances describe quincena-mysql \
  --format="value(settings.activationPolicy,state)"
```

Resultado esperado:

```txt
ALWAYS
RUNNABLE
```

---

## 4. Crear secreto en Secret Manager

Se creó un secreto para guardar la contraseña de la base de datos sin exponerla en el código.

Primero se activó la API de Secret Manager:

```bash
gcloud services enable secretmanager.googleapis.com
```

Después se creó el secreto:

```bash
printf "quincena123" | gcloud secrets create db-password \
  --data-file=-
```

Verificación:

```bash
gcloud secrets list
```

Resultado esperado:

```txt
db-password
```

---

## 5. Crear Artifact Registry

Artifact Registry se usa para almacenar la imagen Docker construida para Cloud Run.

Se creó el repositorio Docker:

```bash
gcloud artifacts repositories create quincena-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Repositorio Docker para Quincena"
```

Si Google Cloud solicitó activar la API, se respondió:

```txt
Y
```

Verificación:

```bash
gcloud artifacts repositories list --location=us-central1
```

Resultado esperado:

```txt
quincena-repo
```

---

## 6. Construir imagen Docker con Cloud Build

Como el `Dockerfile` estaba dentro de la carpeta `cloud/`, se copió temporalmente a la raíz del repositorio para construir la imagen.

```bash
cd ~/quincena-cloud-final
cp cloud/Dockerfile Dockerfile
```

Se construyó y subió la imagen a Artifact Registry:

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/quincena-final-2026/quincena-repo/quincena-api:latest .
```

Si Google Cloud solicitó activar la API de Cloud Build, se respondió:

```txt
Y
```

Resultado esperado:

```txt
SUCCESS
```

Después del build exitoso, se eliminó el `Dockerfile` temporal de la raíz:

```bash
rm Dockerfile
```

El archivo original se conserva en:

```txt
cloud/Dockerfile
```

---

## 7. Permisos necesarios para Cloud Build

Durante el proceso se otorgaron permisos a la cuenta activa para ejecutar builds y subir imágenes.

```bash
gcloud projects add-iam-policy-binding quincena-final-2026 \
  --member="user:ididnotwantthisuselessmail@gmail.com" \
  --role="roles/cloudbuild.builds.editor"
```

```bash
gcloud projects add-iam-policy-binding quincena-final-2026 \
  --member="user:ididnotwantthisuselessmail@gmail.com" \
  --role="roles/artifactregistry.writer"
```

También se otorgaron permisos a la cuenta de servicio usada por Cloud Build para leer objetos de Cloud Storage y escribir en Artifact Registry.

```bash
PROJECT_ID="quincena-final-2026"

PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo $COMPUTE_SA
```

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/storage.objectViewer"
```

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/artifactregistry.writer"
```

---

## 8. Primer despliegue en Cloud Run

Se desplegó el backend FastAPI en Cloud Run usando la imagen publicada en Artifact Registry.

```bash
gcloud run deploy quincena-api \
  --image us-central1-docker.pkg.dev/quincena-final-2026/quincena-repo/quincena-api:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances quincena-final-2026:us-central1:quincena-mysql \
  --set-env-vars DB_HOST=127.0.0.1,DB_PORT=3306,DB_USER=quincena_user,DB_NAME=quincena \
  --set-secrets DB_PASSWORD=db-password:latest
```

Cloud Run se desplegó correctamente, pero el endpoint `/dashboard` no podía conectarse a MySQL usando `127.0.0.1`.

El endpoint `/health` sí respondió correctamente:

```bash
curl https://quincena-api-533093663517.us-central1.run.app/health
```

Respuesta:

```json
{"status":"ok"}
```

---

## 9. Corrección de conexión Cloud Run a Cloud SQL

Se actualizó `backend/db.py` para soportar conexión por socket Unix usando la variable:

```txt
DB_SOCKET
```

En Cloud Run, Cloud SQL se monta en:

```txt
/cloudsql/quincena-final-2026:us-central1:quincena-mysql
```

Después del cambio, se reconstruyó la imagen:

```bash
cd ~/quincena-cloud-final
git pull
cp cloud/Dockerfile Dockerfile
```

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/quincena-final-2026/quincena-repo/quincena-api:latest .
```

```bash
rm Dockerfile
```

---

## 10. Permisos para Secret Manager

Cloud Run necesitaba permiso para leer el secreto `db-password`.

Se otorgó el rol `secretAccessor` a la cuenta de servicio usada por Cloud Run:

```bash
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:533093663517-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 11. Permiso para conectarse a Cloud SQL

Cloud Run también necesitaba permiso para conectarse a Cloud SQL.

Se otorgó el rol `cloudsql.client`:

```bash
gcloud projects add-iam-policy-binding quincena-final-2026 \
  --member="serviceAccount:533093663517-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

---

## 12. Despliegue final usando DB_SOCKET

Se redeployó Cloud Run usando `DB_SOCKET` en lugar de `DB_HOST`.

```bash
gcloud run deploy quincena-api \
  --image us-central1-docker.pkg.dev/quincena-final-2026/quincena-repo/quincena-api:latest \
  --region us-central1 \
  --platform managed \
  --execution-environment gen2 \
  --allow-unauthenticated \
  --add-cloudsql-instances quincena-final-2026:us-central1:quincena-mysql \
  --set-env-vars DB_SOCKET=/cloudsql/quincena-final-2026:us-central1:quincena-mysql,DB_USER=quincena_user,DB_NAME=quincena \
  --set-secrets DB_PASSWORD=db-password:latest
```

Resultado esperado:

```txt
Service quincena-api has been deployed and is serving 100 percent of traffic.
```

URL pública del servicio:

```txt
https://quincena-api-533093663517.us-central1.run.app
```

---

## 13. Pruebas finales de la API pública

Prueba de salud:

```bash
curl https://quincena-api-533093663517.us-central1.run.app/health
```

Respuesta:

```json
{"status":"ok"}
```

Prueba del dashboard:

```bash
curl "https://quincena-api-533093663517.us-central1.run.app/dashboard?usuario_id=1"
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

## 14. Estado final del Integrante 2

El Integrante 2 completó:

* Dockerfile para Cloud Run.
* Archivo `.dockerignore`.
* Script inicial de despliegue.
* Secret Manager para contraseña de MySQL.
* Artifact Registry para imagen Docker.
* Cloud Build para construir la imagen.
* Cloud Run para publicar la API.
* Permisos IAM necesarios.
* Conexión exitosa entre Cloud Run y Cloud SQL.
* Pruebas públicas de `/health` y `/dashboard`.
