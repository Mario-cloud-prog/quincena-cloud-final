

## 16. Frontend funcional

Además de las pruebas con `curl`, se creó un frontend básico en HTML, CSS y JavaScript para demostrar la aplicación visualmente.

Archivo creado:

```txt
frontend/index.html
```

El frontend consume la API pública desplegada en Cloud Run:

```txt
https://quincena-api-533093663517.us-central1.run.app
```

Funcionalidades del frontend:

- consulta el dashboard del usuario;
- muestra gasto acumulado;
- muestra proyección mensual;
- muestra safe to spend;
- muestra presupuesto mensual normal;
- muestra desglose por categoría;
- muestra anomalías;
- permite registrar un gasto nuevo con formulario;
- actualiza el dashboard después de registrar un gasto.

---

## 17. Prueba local del frontend

Para probar el frontend desde Cloud Shell se ejecutó:

```bash
cd ~/quincena-cloud-final
python3 -m http.server 8081 --directory frontend
```

Después se abrió **Web Preview** en el puerto:

```txt
8081
```

Esto abrió la interfaz web de Quincena desde Cloud Shell.

---

## 18. Evidencia del frontend funcionando

El frontend cargó correctamente los datos reales del dashboard desde la API pública.

Valores mostrados en la interfaz:

```txt
Gastado: $215.50
Proyectado: $497.31
Safe to spend: $6402.69
Presupuesto normal: $6900.00
```

Esto confirma que el flujo funciona correctamente:

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

## 19. Corrección de CORS

Al principio el frontend abría correctamente, pero las tarjetas aparecían en cero porque el navegador no podía leer la API pública desde otro origen.

El problema era CORS.

CORS significa **Cross-Origin Resource Sharing**, es decir, el mecanismo que permite o bloquea peticiones entre dominios distintos desde el navegador.

El frontend estaba corriendo desde Cloud Shell Web Preview:

```txt
8081-...cloudshell.dev
```

y la API estaba en Cloud Run:

```txt
quincena-api-533093663517.us-central1.run.app
```

Por eso fue necesario habilitar CORS en FastAPI.

En `backend/main.py` se agregó el import:

```python
from fastapi.middleware.cors import CORSMiddleware
```

Y después de crear la app FastAPI se agregó:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Después se hizo commit y redeploy del backend en Cloud Run.

Comandos usados:

```bash
git add backend/main.py
git commit -m "Habilita CORS para frontend"
git push
bash cloud/deploy.sh
```

---

## 20. Frontend agregado al repositorio

Se agregó la carpeta:

```txt
frontend/
```

Con el archivo:

```txt
frontend/index.html
```

Comandos usados:

```bash
cd ~/quincena-cloud-final
mkdir -p frontend
```

Después se creó el archivo `frontend/index.html` con la interfaz web.

Se subió a GitHub con:

```bash
git add frontend/index.html
git commit -m "Agrega frontend demo de Quincena"
git push
```

---

## 21. Estado final actualizado del Integrante 4

El Integrante 4 completó:

- prueba pública de `/health`;
- prueba pública de `/dashboard`;
- registro de gasto usando `POST /gastos`;
- verificación de actualización del dashboard;
- creación de frontend visual en `frontend/index.html`;
- conexión del frontend con la API pública de Cloud Run;
- corrección de CORS en FastAPI;
- prueba del frontend desde Cloud Shell Web Preview;
- documentación de evidencia de demo;
- guion de presentación;
- resumen de arquitectura para explicar el proyecto.
