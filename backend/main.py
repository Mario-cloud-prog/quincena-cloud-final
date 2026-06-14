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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import insertar_gasto, obtener_dashboard, listar_usuarios, crear_usuario


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
