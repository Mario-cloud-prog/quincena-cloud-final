"""
main.py

API principal del proyecto Quincena.

Este archivo define los endpoints que usarán:
- El frontend para registrar gastos y consultar el dashboard.
- Cloud Run para revisar que la aplicación está funcionando.
- El worker de datos de forma indirecta, cuando después se agregue Pub/Sub.

Rol del Integrante 1:
Mantener estable el contrato de datos del backend.
"""

from datetime import date

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from db import (
    insertar_gasto,
    obtener_dashboard,
    listar_usuarios,
    crear_usuario,
    registrar_usuario,
    buscar_usuario_por_email,
    listar_usuarios_admin,
    cambiar_estado_usuario,
)
from seguridad import verificar_password
from auth import crear_token, verificar_token


app = FastAPI(
    title="Quincena API",
    description="API para registrar gastos y consultar si el usuario llega a fin de mes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Esquema de seguridad: indica a FastAPI que estos endpoints esperan
# un header "Authorization: Bearer <token>". Tambien hace que la
# documentacion automatica (/docs) muestre el candado para meter el token.
bearer_scheme = HTTPBearer()


def obtener_admin(credenciales: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Dependencia que protege los endpoints de administrador.

    Funciona como un guardia en la puerta: se ejecuta ANTES del endpoint.
    1. FastAPI extrae el token del header Authorization (gracias a bearer_scheme).
    2. Verificamos el token con verificar_token (firma + expiracion).
    3. Exigimos que el rol sea 'admin'.

    Si algo falla, lanzamos 401 (token invalido/expirado) o 403 (no es admin),
    y el endpoint protegido nunca llega a ejecutarse.

    Devuelve los datos del admin (usuario_id, rol) por si el endpoint los necesita.
    """
    token = credenciales.credentials

    try:
        datos = verificar_token(token)
    except ValueError as exc:
        # Token alterado o expirado.
        raise HTTPException(status_code=401, detail=str(exc))

    if datos.get("rol") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Se requieren permisos de administrador",
        )

    return datos


class GastoCreate(BaseModel):
    """
    Modelo de entrada para registrar un gasto.

    Este modelo valida automáticamente el JSON recibido en POST /gastos.
    Si falta un campo o el monto no es positivo, FastAPI responde con error 422.
    """

    usuario_id: int = Field(..., example=1)
    monto: float = Field(..., gt=0, example=120.50)
    categoria: str = Field(..., min_length=1, max_length=50, example="comida")
    fecha: date = Field(..., example="2026-06-11")


@app.get("/health")
def health():
    """
    Endpoint de health check.

    Cloud Run puede usar este endpoint para confirmar que la API está viva.
    También sirve para pruebas rápidas durante la demo.
    """
    return {"status": "ok"}


@app.post("/gastos")
def crear_gasto(gasto: GastoCreate):
    """
    Registra un gasto nuevo en Cloud SQL MySQL.

    Flujo actual:
    1. Recibe y valida el JSON del gasto.
    2. Inserta el gasto en la tabla gastos.
    3. Devuelve el gasto registrado.

    Flujo esperado en la versión integrada:
    Después de guardar el gasto, este endpoint publicará un evento en Pub/Sub
    para que el worker del Integrante 3 calcule pronósticos y anomalías
    sin bloquear la respuesta al usuario.
    """
    try:
        nuevo_gasto = insertar_gasto(
            usuario_id=gasto.usuario_id,
            monto=gasto.monto,
            categoria=gasto.categoria,
            fecha=str(gasto.fecha),
        )

        return {
            "message": "Gasto registrado correctamente",
            "gasto": nuevo_gasto,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/dashboard")
def dashboard(usuario_id: int):
    """
    Devuelve el resumen financiero del usuario.

    Este endpoint mantiene el contrato que usará el frontend:
    - proyectado
    - normal_mensual
    - gastado
    - safe_to_spend
    - desglose
    - anomalias
    """
    try:
        return obtener_dashboard(usuario_id)

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



class UsuarioCreate(BaseModel):
    """
    Modelo para crear usuarios desde la web app.
    """

    nombre: str = Field(..., min_length=1, max_length=100, example="Profesor")
    ingreso_mensual: float = Field(..., ge=0, example=15000.00)
    presupuesto_mensual: float = Field(..., ge=0, example=8000.00)


@app.get("/usuarios")
def usuarios():
    """
    Lista los usuarios disponibles.
    """
    try:
        return listar_usuarios()

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/usuarios")
def nuevo_usuario(usuario: UsuarioCreate):
    """
    Crea un usuario nuevo para separar gastos y proyecciones.
    """
    try:
        usuario_creado = crear_usuario(
            nombre=usuario.nombre,
            ingreso_mensual=usuario.ingreso_mensual,
            presupuesto_mensual=usuario.presupuesto_mensual,
        )

        return {
            "message": "Usuario creado correctamente",
            "usuario": usuario_creado,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



class RegistroCreate(BaseModel):
    """
    Modelo de entrada para registrar un usuario con autenticación.

    A diferencia de UsuarioCreate (que crea perfiles sin contraseña para la
    demo multiusuario), este modelo exige email y contraseña.

    Validaciones automáticas de Pydantic:
    - email: debe tener forma válida de correo (EmailStr).
    - password: entre 8 y 72 caracteres. El tope de 72 existe porque bcrypt
      solo usa los primeros 72 bytes; pedir más sería engañoso.
    """

    nombre: str = Field(..., min_length=1, max_length=100, example="Mario")
    email: EmailStr = Field(..., example="mario@ejemplo.com")
    password: str = Field(..., min_length=8, max_length=72, example="contrasena123")
    ingreso_mensual: float = Field(..., ge=0, example=15000.00)
    presupuesto_mensual: float = Field(..., ge=0, example=8000.00)


@app.post("/registro")
def registro(datos: RegistroCreate):
    """
    Registra un usuario nuevo con email único y contraseña hasheada.

    El usuario queda en estado 'pendiente' y NO puede iniciar sesión hasta
    que un administrador lo apruebe. Esto da control sobre quién accede.

    Respuestas:
    - 200: usuario registrado, queda pendiente de aprobación.
    - 409: el correo ya está registrado.
    - 422: el JSON no cumple el formato (email inválido, password corta, etc.).
           Lo maneja Pydantic automáticamente.
    """
    try:
        usuario_creado = registrar_usuario(
            nombre=datos.nombre,
            email=datos.email,
            password=datos.password,
            ingreso_mensual=datos.ingreso_mensual,
            presupuesto_mensual=datos.presupuesto_mensual,
        )

        return {
            "message": "Usuario registrado. Queda pendiente de aprobación por un administrador.",
            "usuario": usuario_creado,
        }

    except ValueError as exc:
        # registrar_usuario lanza ValueError cuando el correo ya existe.
        raise HTTPException(status_code=409, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



class LoginRequest(BaseModel):
    """
    Modelo de entrada para iniciar sesión.

    Solo pide lo mínimo: email y password. No valida longitud de password
    aquí a propósito (eso es cosa del registro); en login solo comparamos.
    """

    email: EmailStr = Field(..., example="mario@ejemplo.com")
    password: str = Field(..., example="contrasena123")


@app.post("/login")
def login(datos: LoginRequest):
    """
    Autentica a un usuario y devuelve un token JWT si todo es correcto.

    Lógica:
    1. Busca el usuario por email. Si no existe -> 401 genérico.
    2. Verifica el password con bcrypt. Si no coincide -> 401 genérico.
       (Mismo mensaje en ambos casos para no revelar si el email existe.)
    3. Revisa el estado. Si no es 'aprobado' -> 403.
    4. Si todo bien -> genera y devuelve un JWT.

    El token devuelto se usa en las demás peticiones como prueba de identidad,
    sin volver a mandar el password.
    """
    try:
        usuario = buscar_usuario_por_email(datos.email)

        # Paso 1 y 2: usuario inexistente o password incorrecto.
        # Respondemos lo mismo en ambos casos a propósito (no revelar cuál falló).
        if usuario is None or not usuario.get("password_hash"):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        if not verificar_password(datos.password, usuario["password_hash"]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        # Paso 3: el password es correcto, pero el acceso depende del estado.
        if usuario["estado"] != "aprobado":
            if usuario["estado"] == "pendiente":
                detalle = "Tu cuenta está pendiente de aprobación por un administrador"
            else:
                detalle = "Tu cuenta está desactivada"
            raise HTTPException(status_code=403, detail=detalle)

        # Paso 4: todo en orden, emitimos el token.
        token = crear_token(usuario_id=usuario["id"], rol=usuario["rol"])

        return {
            "access_token": token,
            "token_type": "bearer",
            "rol": usuario["rol"],
        }

    except HTTPException:
        # Re-lanzamos los errores HTTP que nosotros mismos generamos arriba,
        # para que no los atrape el except genérico de abajo.
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



# ---------------------------------------------------------------------------
# Endpoints de administrador
#
# Todos exigen un token JWT de un usuario con rol 'admin', verificado por la
# dependencia obtener_admin. Permiten ver el padron de usuarios y aprobar o
# desactivar cuentas sin entrar a la base de datos a mano.
# ---------------------------------------------------------------------------


@app.get("/admin/usuarios")
def admin_listar_usuarios(admin: dict = Depends(obtener_admin)):
    """
    Lista todos los usuarios con su estado y rol.

    Pensado para que el admin vea quien esta pendiente de aprobacion.
    Protegido: requiere token de admin.
    """
    try:
        return listar_usuarios_admin()

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/admin/usuarios/{usuario_id}/aprobar")
def admin_aprobar_usuario(usuario_id: int, admin: dict = Depends(obtener_admin)):
    """
    Aprueba a un usuario: cambia su estado a 'aprobado'.

    A partir de aqui ese usuario ya puede iniciar sesion.
    Protegido: requiere token de admin.
    """
    try:
        usuario = cambiar_estado_usuario(usuario_id, "aprobado")

        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return {
            "message": "Usuario aprobado",
            "usuario": usuario,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/admin/usuarios/{usuario_id}/desactivar")
def admin_desactivar_usuario(usuario_id: int, admin: dict = Depends(obtener_admin)):
    """
    Desactiva a un usuario: cambia su estado a 'desactivado'.

    El usuario deja de poder iniciar sesion, pero conserva su historial de
    gastos (no se borra nada). Es reversible: se puede volver a aprobar.

    Salvaguarda: un admin NO puede desactivarse a si mismo, para evitar
    quedarse sin acceso al control de la aplicacion.
    Protegido: requiere token de admin.
    """
    try:
        # admin["usuario_id"] viene del token verificado en obtener_admin.
        if usuario_id == admin["usuario_id"]:
            raise HTTPException(
                status_code=400,
                detail="Un administrador no puede desactivarse a si mismo",
            )

        usuario = cambiar_estado_usuario(usuario_id, "desactivado")

        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return {
            "message": "Usuario desactivado",
            "usuario": usuario,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
