#!/bin/bash

# deploy.sh
# Script de despliegue del backend FastAPI de Quincena en Cloud Run.

set -e

PROJECT_ID="quincena-final-2026"
REGION="us-central1"
REPOSITORY="quincena-repo"
SERVICE_NAME="quincena-api"
IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:latest"
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:${REGION}:quincena-mysql"

echo "Configurando proyecto..."
gcloud config set project "${PROJECT_ID}"

echo "Activando APIs necesarias..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

echo "Construyendo imagen Docker con Cloud Build..."
gcloud builds submit \
  --tag "${IMAGE}" \
  --file cloud/Dockerfile .

echo "Desplegando servicio en Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances "${INSTANCE_CONNECTION_NAME}" \
  --set-env-vars DB_HOST=127.0.0.1,DB_PORT=3306,DB_USER=quincena_user,DB_NAME=quincena \
  --set-secrets DB_PASSWORD=db-password:latest

echo "Despliegue terminado."
