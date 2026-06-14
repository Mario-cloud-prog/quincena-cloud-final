

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

---

---

## Modo multiusuario en frontend

Como mejora final de la demo, el frontend dejó de trabajar con un usuario fijo y ahora permite usar la aplicación con diferentes usuarios reales.

Anteriormente, la web app usaba directamente `usuario_id=1`, por lo que todos los gastos registrados desde la interfaz se guardaban en el mismo usuario demo. Con el cambio multiusuario, el frontend permite seleccionar un usuario existente o crear uno nuevo desde la página web.

### Funcionalidades agregadas

Se agregaron las siguientes funciones en `frontend/index.html`:

| Función             | Descripción                                                           |
| ------------------- | --------------------------------------------------------------------- |
| `cargarUsuarios()`  | Consulta `GET /usuarios` para llenar el selector de usuarios.         |
| `crearUsuario()`    | Envía datos a `POST /usuarios` para crear un usuario nuevo.           |
| `cargarDashboard()` | Consulta `/dashboard?usuario_id=<id>` usando el usuario seleccionado. |
| `guardarGasto()`    | Registra gastos usando el `usuario_id` seleccionado.                  |

### Flujo de uso

El flujo para un usuario real es:

1. Abrir la web app publicada en GitHub Pages.
2. Seleccionar un usuario existente o crear uno nuevo.
3. Registrar gastos desde el formulario.
4. Ver el dashboard actualizado con los datos de ese usuario.
5. Cambiar de usuario para comprobar que los datos están separados.

### Separación de datos

El frontend guarda el usuario seleccionado en `localStorage`, usando la clave:

```js
quincena_usuario_id
```

Esto permite que la página recuerde el último usuario usado en el navegador.

Cada vez que se carga el dashboard, el frontend llama al backend con el identificador seleccionado:

```js
/dashboard?usuario_id=<id>
```

Y cada vez que se registra un gasto, se envía el campo:

```js
usuario_id: Number(usuarioIdActual)
```

De esta forma, el profesor, invitados y usuario demo pueden probar la misma aplicación sin mezclar sus gastos.

### Publicación en GitHub Pages

Después de actualizar `frontend/index.html`, se copió el mismo contenido a:

```txt
docs/index.html
```

Esto permite que GitHub Pages publique la versión multiusuario de la app en:

```txt
https://mario-cloud-prog.github.io/quincena-cloud-final/
```

### Prueba realizada

Se comprobó que `frontend/index.html` y `docs/index.html` tienen el mismo contenido con:

```bash
cmp -s frontend/index.html docs/index.html && echo "Son iguales" || echo "Son diferentes"
```

El resultado fue:

```txt
Son iguales
```

También se verificó que la página pública muestra la sección de usuario, permite seleccionar perfiles como `Usuario Demo` y `Profesor`, y registra gastos usando el usuario seleccionado.

### Consideración importante

Esta versión implementa multiusuario para la demo mediante selección de usuario y creación de perfiles, pero todavía no incluye autenticación con contraseña. Para producción, se debería agregar login para evitar que una persona pueda seleccionar o modificar datos de otro usuario.
