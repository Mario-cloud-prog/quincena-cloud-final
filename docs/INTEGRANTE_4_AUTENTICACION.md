# Integrante 4 — Autenticación y Control de Acceso

Este documento registra el trabajo de autenticación, contraseñas y control de
acceso agregado al proyecto **Quincena**. Antes de este cambio, la aplicación
era una demo multiusuario sin contraseñas: cualquiera podía consultar o
modificar los datos de cualquier usuario pasando `usuario_id` en la URL.

El objetivo fue cerrar ese hueco con tres capacidades:

1. **Registro con contraseña**, una por usuario, guardada de forma segura.
2. **Login** que entrega un token de sesión (JWT).
3. **Control de administrador**: aprobar o desactivar usuarios, de modo que
   nadie acceda sin autorización previa.

---

## 1. Cambios en el esquema de la base de datos

Se agregaron cuatro columnas a la tabla `usuarios` en Cloud SQL MySQL.

```sql
ALTER TABLE usuarios
  ADD COLUMN email VARCHAR(255) NULL UNIQUE AFTER nombre,
  ADD COLUMN password_hash VARCHAR(255) NULL AFTER email,
  ADD COLUMN rol ENUM('admin','usuario') NOT NULL DEFAULT 'usuario' AFTER password_hash,
  ADD COLUMN estado ENUM('pendiente','aprobado','desactivado') NOT NULL DEFAULT 'pendiente' AFTER rol;
```

Decisiones de diseño:

- **`email` con `UNIQUE`**: es el identificador de login. La restricción única
  impide dos cuentas con el mismo correo. Se guarda normalizado (minúsculas,
  sin espacios) para evitar duplicados tipo `Mario@x.com` vs `mario@x.com`.
- **`password_hash`, no `password`**: el nombre deja explícito que ahí va el
  *hash* bcrypt, nunca la contraseña en claro.
- **`rol`**: distingue `admin` de `usuario`. Solo un admin puede aprobar o
  desactivar a otros.
- **`estado`**: un usuario nuevo nace `pendiente` y no puede iniciar sesión
  hasta que un admin lo pase a `aprobado`. `desactivado` quita el acceso
  conservando el historial (es reversible).
- Las columnas se dejaron `NULL`-ables para no romper a los usuarios demo
  que ya existían sin correo ni contraseña.

El usuario administrador se marcó manualmente:

```sql
UPDATE usuarios SET rol = 'admin', estado = 'aprobado' WHERE id = 1;
```

---

## 2. Hashing de contraseñas (`seguridad.py`)

Se creó `backend/seguridad.py` con dos funciones basadas en **bcrypt**.

```python
import bcrypt


def hashear_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)
```

Puntos clave:

- bcrypt agrega un *salt* aleatorio a cada hash, así que dos usuarios con la
  misma contraseña generan hashes distintos.
- El hash es de una sola vía: `checkpw` re-hashea lo tecleado y compara, sin
  descifrar. Aunque se robe la base, las contraseñas no se pueden recuperar.
- bcrypt solo usa los primeros 72 bytes de la contraseña.

Dependencia agregada a `requirements.txt`:

```txt
bcrypt==4.2.0
```

---

## 3. Tokens de sesión JWT (`auth.py`)

Se creó `backend/auth.py` para manejar los tokens de sesión, separado de
`seguridad.py` (uno hace contraseñas, el otro tokens).

```python
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRACION_HORAS = 8


def crear_token(usuario_id: int, rol: str) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": ahora + timedelta(hours=JWT_EXPIRACION_HORAS),
        "iat": ahora,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verificar_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("El token expiró, inicia sesión de nuevo") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Token inválido") from exc
    return {"usuario_id": int(payload["sub"]), "rol": payload["rol"]}
```

Decisiones de diseño:

- Un JWT es un texto firmado con una **clave secreta** que solo el backend
  conoce. Si alguien altera el token, la firma deja de cuadrar y se rechaza.
- **Algoritmo HS256**: firma simétrica (la misma clave firma y verifica),
  correcto cuando un solo backend hace ambas cosas.
- **Expiración de 8 horas**: balance entre comodidad y seguridad. Un token
  robado no sirve para siempre.
- El backend es **stateless**: no guarda sesiones en memoria. Cada petición se
  valida sola con la firma del token, lo que encaja con Cloud Run.

Dependencia agregada a `requirements.txt`:

```txt
pyjwt[crypto]
```

---

## 4. Clave secreta en Secret Manager

La clave que firma los JWT no se escribe en el código ni se sube a Git. Se
generó aleatoria y se guardó en Secret Manager, igual que `db-password`.

```bash
openssl rand -hex 32
```

```bash
printf "LA_CLAVE_GENERADA" | gcloud secrets create jwt-secret --data-file=-
```

En local, la misma clave se puso en `backend/.env` como `JWT_SECRET`. El
archivo `.env` está protegido por `.gitignore` y no se sube al repositorio.

> Importante: la misma clave debe estar en Secret Manager y en `.env`, o los
> tokens firmados en local no servirían en Cloud Run.

---

## 5. Registro de usuarios

### Funcion en db.py

Normaliza el email, hashea la contraseña, e inserta. El usuario nace en estado
`pendiente` por el default del esquema. Atrapa el error de email duplicado
(MySQL 1062) y lo convierte en un mensaje legible. Nunca devuelve el
`password_hash`.

### Endpoint POST /registro

Recibe `nombre`, `email`, `password`, `ingreso_mensual`, `presupuesto_mensual`.
Valida el formato del email con `EmailStr` de Pydantic y exige contraseña de
8 a 72 caracteres.

Respuestas:

- `200`: usuario registrado, queda pendiente de aprobación.
- `409`: el correo ya está registrado.
- `422`: el JSON no cumple el formato (email inválido, contraseña corta).

Dependencia agregada para validar emails:

```txt
email-validator
```

Prueba realizada: registrar un usuario nuevo lo creó en estado `pendiente` sin
exponer el hash. Un segundo intento con el mismo correo devolvió `409 Conflict`.

---

## 6. Login

### Funcion en db.py

`buscar_usuario_por_email` hace un SELECT por email y devuelve id, rol, estado y
password_hash, o None si no existe. Trae el hash solo para compararlo.

### Endpoint POST /login

Lógica:

1. Busca el usuario por email. Si no existe, responde `401` genérico.
2. Verifica la contraseña con bcrypt. Si no coincide, responde `401` genérico.
   (Mismo mensaje en ambos casos para no revelar si el email existe.)
3. Revisa el estado. Si no es `aprobado`, responde `403`.
4. Si todo bien, genera y devuelve un JWT.

Pruebas realizadas:

- Login de un usuario `pendiente` con contraseña correcta dio `403`.
- Login con contraseña incorrecta dio `401` ("Credenciales inválidas").
- Tras aprobar al usuario, login con contraseña correcta dio `200` con token.

---

## 7. Endpoints de administrador

### Guardia obtener_admin en main.py

Es una dependencia de FastAPI que se ejecuta antes de los endpoints de admin.
Lee el token del header `Authorization: Bearer <token>`, lo verifica y exige
`rol == admin`. Si falla, responde `401` (token inválido o ausente) o `403`
(token válido pero no es admin), y el endpoint no se ejecuta.

### Funciones en db.py

- `listar_usuarios_admin()`: lista id, nombre, email, rol y estado (sin hash).
- `cambiar_estado_usuario(id, nuevo_estado)`: actualiza el estado; devuelve
  None si no existe el usuario, para responder `404`.

### Endpoints

- `GET /admin/usuarios`: lista el padrón con estado y rol.
- `POST /admin/usuarios/{id}/aprobar`: cambia el estado a `aprobado`.
- `POST /admin/usuarios/{id}/desactivar`: cambia el estado a `desactivado`.

Salvaguarda: un admin no puede desactivarse a sí mismo (responde `400`), para
no quedarse sin acceso al control de la aplicación.

Pruebas realizadas:

- `GET /admin/usuarios` con token de admin dio `200` y el padrón completo.
- La misma petición sin token dio `401` ("Not authenticated").

---

## 8. Archivos del backend tras este trabajo

```txt
backend/
  main.py          # endpoints, ahora con /registro, /login y /admin/*
  db.py            # consultas, ahora con registro, login y admin
  seguridad.py     # hashing bcrypt (nuevo)
  auth.py          # tokens JWT (nuevo)
  requirements.txt # mas bcrypt, email-validator, pyjwt[crypto]
  .env             # mas JWT_SECRET (no se sube a Git)
```

---

## 9. Despliegue a Cloud Run

Se redeployó el backend en Cloud Run para que la autenticación viviera en
producción, inyectando `JWT_SECRET` desde Secret Manager (igual que
`db-password`).

### Permiso para leer el secreto

La cuenta de servicio de Cloud Run necesitaba permiso para leer `jwt-secret`.
Se le dio el rol `secretAccessor` solo sobre ese secreto (los permisos en
Secret Manager son por secreto).

```bash
gcloud secrets add-iam-policy-binding jwt-secret \
  --member="serviceAccount:533093663517-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Reconstrucción de la imagen

El código nuevo (con `auth.py`, `seguridad.py`, login y admin) se empaquetó en
una imagen nueva. El Dockerfile copia toda la carpeta `backend/`, así que los
archivos nuevos se incluyen automáticamente. El `.dockerignore` excluye `.env`,
por lo que las credenciales no entran a la imagen.

```bash
cd ~/quincena-cloud-final
cp cloud/Dockerfile Dockerfile
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/quincena-final-2026/quincena-repo/quincena-api:latest .
rm Dockerfile
```

### Deploy

Se agregó `JWT_SECRET=jwt-secret:latest` a `--set-secrets`. Importante: esa
bandera reemplaza toda la lista de secretos, así que hay que listar
`db-password` y `jwt-secret` juntos. Lo mismo aplica a `--set-env-vars`.

```bash
gcloud run deploy quincena-api \
  --image us-central1-docker.pkg.dev/quincena-final-2026/quincena-repo/quincena-api:latest \
  --region us-central1 \
  --platform managed \
  --execution-environment gen2 \
  --allow-unauthenticated \
  --add-cloudsql-instances quincena-final-2026:us-central1:quincena-mysql \
  --set-env-vars DB_SOCKET=/cloudsql/quincena-final-2026:us-central1:quincena-mysql,DB_USER=quincena_user,DB_NAME=quincena \
  --set-secrets DB_PASSWORD=db-password:latest,JWT_SECRET=jwt-secret:latest
```

### Pruebas en producción

- `GET /health` respondió `{"status":"ok"}` (el contenedor arrancó leyendo
  ambos secretos).
- `POST /login` con la cuenta de admin respondió `200` con un token y
  `"rol":"admin"`. Esto confirma que el login funciona de punta a punta en la
  nube: recibe la petición, consulta Cloud SQL, verifica el password y firma el
  JWT con la clave de Secret Manager.

URL pública del servicio:

```txt
https://quincena-api-533093663517.us-central1.run.app
```

---

## 10. Pantalla de login en el frontend

Se agregó una pantalla de login a `frontend/index.html` (y su copia
`docs/index.html`, que es la que publica GitHub Pages). Esto es el "Nivel 1":
la puerta de entrada de la web app.

### Cambios

- **Pantalla de login primero**: al abrir la app, si no hay token válido se
  muestra un formulario de correo y contraseña. El dashboard queda oculto hasta
  iniciar sesión.
- **Se quitó el selector de usuarios** y la creación de usuarios sin
  contraseña. Ese selector era justamente el hueco: cualquiera elegía cualquier
  usuario. Ahora quién eres lo decide tu token.
- **El usuario se lee del token**: el frontend decodifica el payload del JWT en
  el navegador (base64url) para obtener el `usuario_id` (campo `sub`). No hace
  falta un endpoint nuevo.
- **Cada petición manda el token** en el header `Authorization: Bearer <token>`.
  Aunque `/dashboard` y `/gastos` todavía no lo verifican (ver Nivel 2), el
  frontend ya queda listo para cuando se protejan.
- **Botón de cerrar sesión**: borra el token y regresa al login.
- **Sesión vencida**: si una petición devuelve `401`, el frontend cierra la
  sesión y vuelve al login.

El token se guarda en `localStorage` con la clave `quincena_token`, y el correo
en `quincena_email` (solo para mostrar quién tiene la sesión).

### Pruebas realizadas

Se probó local con Web Preview en Cloud Shell:

```bash
python3 -m http.server 8081 --directory frontend
```

- Al abrir, mostró la pantalla de login (no el dashboard).
- Login con la cuenta de admin llevó al dashboard con datos reales.
- Cerrar sesión regresó al login.
- Registrar un gasto funcionó y refrescó las tarjetas.

Después se publicó en GitHub Pages:

```txt
https://mario-cloud-prog.github.io/quincena-cloud-final/
```

---

## 11. Pendientes

- **Nivel 2 de seguridad**: proteger `/dashboard` y `/gastos` en el backend
  para que lean el usuario del token en vez del `usuario_id` del query. Esto
  cierra el hueco del todo a nivel API; hoy el candado está en el frontend.
- Probar el caso `403` con un token de usuario no-admin (usuario autenticado
  pero sin permisos de administrador).
- Considerar cambiar la contraseña del admin si se reutiliza en otros
  servicios, como buena práctica de seguridad.
