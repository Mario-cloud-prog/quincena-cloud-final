# Dockerfile
# Imagen para desplegar la API FastAPI de Quincena en Cloud Run.

FROM python:3.11-slim

# Evita archivos .pyc y mejora la salida de logs en Cloud Run.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Carpeta de trabajo dentro del contenedor.
WORKDIR /app

# Copiamos primero requirements.txt para aprovechar cache de Docker.
COPY backend/requirements.txt .

# Instalamos las dependencias del backend.
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código del backend.
COPY backend/ .

# Cloud Run inyecta la variable PORT. Si no existe, usamos 8080.
ENV PORT=8080

# Ejecuta la API FastAPI con Uvicorn.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
