import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()  # carga variables de .env

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = os.getenv("HF_MODEL_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not all([HF_TOKEN, HF_MODEL_URL, SUPABASE_URL, SUPABASE_KEY]):
    raise RuntimeError("Faltan variables de entorno. Revisa .env")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="API de Etiquetado")

# --- Configuración CORS ---
origins = [
    "http://localhost:5173",  # tu frontend local
    "https://TU_FRONTEND_DOMINIO"  # frontend en producción
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelo de datos ---
class URLItem(BaseModel):
    url: str

# --- Ruta de etiquetado ---
@app.post("/etiquetar")
def etiquetar(item: URLItem):
    url = item.url

    # 1️⃣ Descargar imagen
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        img_bytes = r.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error descargando la imagen: {e}")

    # 2️⃣ Enviar a HuggingFace
    try:
        resp = requests.post(HF_MODEL_URL, headers=HEADERS, data=img_bytes, timeout=30)
        resp.raise_for_status()
        etiquetas = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en HuggingFace: {e}")

    # 3️⃣ Guardar en Supabase (no bloquea la respuesta si falla)
    try:
        supabase.table("etiquetas").insert({
            "url": url,
            "resultado": etiquetas
        }).execute()
    except Exception as e:
        print("Aviso: fallo guardando en Supabase:", e)

    return {"url": url, "etiquetas": etiquetas}

# --- Ruta de prueba de CORS ---
@app.options("/etiquetar")
def preflight():
    """
    Responde a preflight requests (OPTIONS) para CORS.
    FastAPI con CORSMiddleware lo hace automáticamente,
    pero es útil tenerla para debug.
    """
    return {}
