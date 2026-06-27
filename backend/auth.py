"""
auth.py

Manejo de tokens JWT para el proyecto Quincena.

Separado de seguridad.py a propósito:
- seguridad.py se encarga del hashing de contraseñas (bcrypt).
- auth.py se encarga de los tokens de sesión (JWT).

El flujo es:
1. El usuario hace login con email + password.
2. Si el password es correcto y su estado es 'aprobado', el backend
   llama a crear_token() y le devuelve un JWT firmado.
3. En cada petición protegida, el backend llama a verificar_token()
   para saber quién es el usuario sin pedirle de nuevo la contraseña.

La clave secreta de firma se lee de la variable de entorno JWT_SECRET,
que en local viene del archivo .env y en Cloud Run viene de Secret Manager.
Nunca se escribe en el código ni se sube a Git.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv


load_dotenv()

# Clave secreta para firmar y verificar tokens.
# Si no existe, es un error de configuración: preferimos fallar claro.
JWT_SECRET = os.getenv("JWT_SECRET")

# Algoritmo de firma simétrica: la misma clave firma y verifica.
# Es el correcto cuando un solo backend hace ambas cosas.
JWT_ALGORITHM = "HS256"

# Tiempo de vida del token. Tras esto, el usuario debe volver a hacer login.
JWT_EXPIRACION_HORAS = 8


def crear_token(usuario_id: int, rol: str) -> str:
    """
    Genera un JWT firmado para un usuario autenticado.

    Mete en el token (payload):
    - sub: el id del usuario (identificador del 'sujeto' del token).
    - rol: para distinguir admin de usuario sin consultar la BD.
    - exp: fecha de expiración. PyJWT la valida automáticamente al verificar.

    Devuelve el token como cadena de texto.
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET no está configurada")

    ahora = datetime.now(timezone.utc)

    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": ahora + timedelta(hours=JWT_EXPIRACION_HORAS),
        "iat": ahora,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verificar_token(token: str) -> dict:
    """
    Verifica un JWT y devuelve su contenido si es válido.

    Comprueba la firma (con la clave secreta) y la expiración.
    PyJWT lanza excepción si el token está alterado o vencido; la
    traducimos a un ValueError con mensaje claro para que el endpoint
    pueda responder 401.

    Devuelve un dict con:
    - usuario_id: int
    - rol: str
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET no está configurada")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("El token expiró, inicia sesión de nuevo") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Token inválido") from exc

    return {
        "usuario_id": int(payload["sub"]),
        "rol": payload["rol"],
    }
