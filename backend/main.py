from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from db import insertar_gasto, obtener_dashboard

app = FastAPI(
    title="Quincena API",
    description="API para registrar gastos y consultar si el usuario llega a fin de mes.",
    version="1.0.0",
)


class GastoCreate(BaseModel):
    usuario_id: int = Field(..., example=1)
    monto: float = Field(..., gt=0, example=120.50)
    categoria: str = Field(..., min_length=1, max_length=50, example="comida")
    fecha: date = Field(..., example="2026-06-11")


@app.get("/health")
def health():
    """
    Health check usado por Cloud Run para validar que la API está viva.
    """
    return {"status": "ok"}


@app.post("/gastos")
def crear_gasto(gasto: GastoCreate):
    """
    Registra un gasto nuevo.

    Más adelante este endpoint también publicará un evento en Pub/Sub
    para que el worker del Integrante 3 procese pronósticos y anomalías.
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
    """
    try:
        return obtener_dashboard(usuario_id)

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
