import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()  # carga .env

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = os.getenv("HF_MODEL_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not all([HF_TOKEN, HF_MODEL_URL, SUPABASE_URL, SUPABASE_KEY]):
    raise RuntimeError("Faltan variables de entorno. Revisa .env")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="API de Etiquetado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod limita al frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLItem(BaseModel):
    url: str

@app.post("/etiquetar")
def etiquetar(item: URLItem):
    url = item.url
    # descargar imagen (bytes)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        img_bytes = r.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error descargando la imagen: {e}")

    # enviar a HuggingFace
    try:
        resp = requests.post(HF_MODEL_URL, headers=HEADERS, data=img_bytes, timeout=30)
        resp.raise_for_status()
        etiquetas = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en HuggingFace: {e}")

    # guardar en Supabase
    try:
        insert = supabase.table("etiquetas").insert({
            "url": url,
            "resultado": etiquetas
        }).execute()
    except Exception as e:
        # no interrumpir si falla guardar; igualmente devolvemos etiquetas
        print("Aviso: fallo guardando en Supabase:", e)

    return {"url": url, "etiquetas": etiquetas}
