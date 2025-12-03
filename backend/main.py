import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = os.getenv("HF_MODEL_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not all([HF_TOKEN, HF_MODEL_URL, SUPABASE_URL, SUPABASE_KEY]):
    raise RuntimeError("Faltan variables de entorno. Revisa .env")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="API de Etiquetado")

# -----------------------------------------
# 🔥 FIX DEFINITIVO PARA CORS EN RENDER
# -----------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # OK para Render
    allow_credentials=False,  # Obligatorio con "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------
# 👌 Ruta raíz obligatoria para Render
# -----------------------------------------
@app.get("/")
def home():
    return {"status": "ok", "mensaje": "Backend funcionando"}

# --- Modelo de datos ---
class URLItem(BaseModel):
    url: str

# --- Ruta principal ---
@app.post("/etiquetar")
def etiquetar(item: URLItem):
    url = item.url

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        img_bytes = r.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error descargando imagen: {e}")

    try:
        resp = requests.post(HF_MODEL_URL, headers=HEADERS, data=img_bytes, timeout=30)
        resp.raise_for_status()
        etiquetas = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en HuggingFace: {e}")

    try:
        supabase.table("etiquetas").insert({
            "url": url,
            "resultado": etiquetas
        }).execute()
    except Exception as e:
        print("Aviso: fallo guardando en Supabase:", e)

    return {"url": url, "etiquetas": etiquetas}
