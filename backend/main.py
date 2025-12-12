import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

# ============================
# VARIABLES DE ENTORNO
# ============================
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = os.getenv("HF_MODEL_URL", "https://api-inference.huggingface.co/models/google/vit-base-patch16-224")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN no configurado en Render")

HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

# ============================
# FASTAPI
# ============================
app = FastAPI(
    title="API de Etiquetado de Imágenes",
    description="Clasificación de imágenes usando Hugging Face Inference API",
    version="1.0.0"
)

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

# ============================
# ENDPOINTS
# ============================

@app.get("/")
def home():
    return {
        "status": "ok",
        "mensaje": "Backend funcionando",
        "modelo": HF_MODEL_URL,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "hf_token": bool(HF_TOKEN),
        "backend": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/etiquetar")
def etiquetar(item: URLItem):
    try:
        # 1. Descargar imagen
        img_request = requests.get(item.url, timeout=15)
        img_request.raise_for_status()
        image_data = img_request.content

        # 2. Enviar a HuggingFace
        hf_response = requests.post(
            HF_MODEL_URL,
            headers=HF_HEADERS,
            data=image_data,
            timeout=30
        )

        if hf_response.status_code == 503:
            return {
                "error": "Modelo cargando (Warmup)",
                "estimated_time": hf_response.json().get("estimated_time", 30),
                "url": item.url
            }

        hf_response.raise_for_status()
        labels = hf_response.json()

        # 3. Guardar en Supabase si existe la tabla
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from postgrest import PostgrestClient
                
                client = PostgrestClient(SUPABASE_URL)
                client.auth(SUPABASE_KEY)

                data = {
                    "url": item.url,
                    "resultado": labels,
                    "timestamp": datetime.now().isoformat()
                }

                client.from_("etiquetas").insert(data).execute()
            except Exception as e:
                print(f"No se pudo guardar en Supabase: {e}")

        # 4. Respuesta final
        return {
            "status": "ok",
            "url": item.url,
            "etiquetas": labels,
            "timestamp": datetime.now().isoformat()
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error descargando la imagen: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================
# EJECUCIÓN LOCAL
# ============================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
