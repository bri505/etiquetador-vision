import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

# Obtener variables de entorno
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = os.getenv("HF_MODEL_URL", "https://api-inference.huggingface.co/models/google/vit-base-patch16-224")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN no configurado")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLItem(BaseModel):
    url: str

@app.get("/")
def home():
    return {"status": "ok", "mensaje": "Backend funcionando"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "hf_token": bool(HF_TOKEN),
        "backend": "operational"
    }

@app.post("/etiquetar")
def etiquetar(item: URLItem):
    try:
        print(f"Procesando imagen: {item.url}")
        
        # 1. Descargar imagen
        response = requests.get(item.url, timeout=15)
        response.raise_for_status()
        image_data = response.content
        
        print(f"Imagen descargada: {len(image_data)} bytes")
        
        # 2. Enviar a HuggingFace
        print(f"Enviando a: {HF_MODEL_URL}")
        hf_response = requests.post(
            HF_MODEL_URL,
            headers=HEADERS,
            data=image_data,
            timeout=30
        )
        
        print(f"Respuesta HF: {hf_response.status_code}")
        
        # Si el modelo está cargando
        if hf_response.status_code == 503:
            return {
                "error": "Modelo cargando",
                "estimated_time": hf_response.json().get("estimated_time", 30),
                "url": item.url
            }
        
        hf_response.raise_for_status()
        labels = hf_response.json()
        
        print(f"Etiquetas obtenidas: {len(labels)}")
        
        # 3. Intentar guardar en Supabase si hay credenciales
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import httpx
                from postgrest import PostgrestClient
                
                client = PostgrestClient(SUPABASE_URL)
                client.auth(SUPABASE_KEY)
                
                data = {
                    "url": item.url,
                    "resultado": labels
                }
                
                response = client.from_("etiquetas").insert(data).execute()
                print("Guardado en Supabase exitoso")
            except Exception as e:
                print(f"Error guardando en Supabase: {e}")
        
        return {
            "url": item.url,
            "etiquetas": labels,
            "procesado": True,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error de requests: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)