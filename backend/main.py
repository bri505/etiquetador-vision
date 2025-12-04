import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client
import traceback
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = os.getenv("HF_MODEL_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

logger.info(f"HF_TOKEN presente: {bool(HF_TOKEN)}")
logger.info(f"HF_MODEL_URL: {HF_MODEL_URL}")
logger.info(f"SUPABASE_URL: {SUPABASE_URL}")
logger.info(f"SUPABASE_KEY presente: {bool(SUPABASE_KEY)}")

# Solo levantamos excepción si falta HF_TOKEN, las otras pueden ser opcionales
if not HF_TOKEN:
    logger.error("❌ HF_TOKEN no configurado")
    raise RuntimeError("HF_TOKEN es requerido. Configúralo en Render.")

# Configurar headers para HuggingFace si hay token
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

# Configurar Supabase solo si hay credenciales
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase configurado correctamente")
    except Exception as e:
        logger.warning(f"⚠️  No se pudo configurar Supabase: {e}")
        supabase = None
else:
    logger.warning("⚠️  Credenciales de Supabase no configuradas")

app = FastAPI(title="API de Etiquetado")

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "mensaje": "Backend funcionando"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "hf_token_configured": bool(HF_TOKEN),
        "supabase_configured": bool(supabase),
        "backend": "operational"
    }

# --- Modelo de datos ---
class URLItem(BaseModel):
    url: str

# --- Ruta principal ---
@app.post("/etiquetar")
def etiquetar(item: URLItem):
    url = item.url
    logger.info(f"Procesando imagen: {url[:50]}...")
    
    # Verificar que HF_TOKEN está configurado
    if not HF_TOKEN:
        raise HTTPException(
            status_code=500, 
            detail="Servicio no configurado. HF_TOKEN faltante."
        )
    
    try:
        # 1. Descargar imagen
        logger.info("Descargando imagen...")
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        img_bytes = r.content
        logger.info(f"Imagen descargada: {len(img_bytes)} bytes")
    except Exception as e:
        logger.error(f"Error descargando imagen: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error descargando imagen: {e}")

    try:
        # 2. Procesar con HuggingFace
        logger.info(f"Enviando a HuggingFace: {HF_MODEL_URL}")
        
        # Verificar que el modelo esté especificado
        if not HF_MODEL_URL:
            HF_MODEL_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
            
        resp = requests.post(
            HF_MODEL_URL, 
            headers=HEADERS, 
            data=img_bytes, 
            timeout=30
        )
        
        logger.info(f"Respuesta HF status: {resp.status_code}")
        
        # Si el modelo está cargando
        if resp.status_code == 503:
            estimated_time = resp.json().get("estimated_time", 30)
            logger.warning(f"Modelo cargando, tiempo estimado: {estimated_time}s")
            raise HTTPException(
                status_code=503,
                detail=f"Modelo está cargando. Intenta de nuevo en {estimated_time} segundos."
            )
        
        resp.raise_for_status()
        etiquetas = resp.json()
        logger.info(f"Etiquetas recibidas: {len(etiquetas)} items")
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP de HuggingFace: {str(e)}")
        logger.error(f"Respuesta: {resp.text if 'resp' in locals() else 'No response'}")
        
        if resp.status_code == 401:
            raise HTTPException(status_code=500, detail="Token de HuggingFace inválido")
        elif resp.status_code == 404:
            raise HTTPException(status_code=500, detail="Modelo no encontrado en HuggingFace")
        else:
            raise HTTPException(status_code=500, detail=f"Error en HuggingFace: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en HuggingFace: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error procesando imagen: {e}")

    # 3. Guardar en Supabase (si está configurado)
    if supabase:
        try:
            logger.info("Guardando en Supabase...")
            supabase.table("etiquetas").insert({
                "url": url,
                "resultado": etiquetas
            }).execute()
            logger.info("Guardado en Supabase exitoso")
        except Exception as e:
            logger.error(f"Error guardando en Supabase: {str(e)}")
            # Continuamos aunque falle Supabase
    else:
        logger.warning("⚠️  Supabase no configurado, omitiendo guardado")

    return {
        "url": url,
        "etiquetas": etiquetas,
        "procesado": True,
        "mensaje": "Imagen etiquetada exitosamente",
        "supabase_guardado": bool(supabase)
    }

# Endpoint para pruebas
@app.post("/test")
def test_endpoint(item: URLItem):
    return {
        "message": "Test endpoint funciona",
        "received_url": item.url,
        "backend_status": "operational",
        "hf_configured": bool(HF_TOKEN),
        "supabase_configured": bool(supabase)
    }

# Endpoint de diagnóstico
@app.get("/debug")
def debug_info():
    return {
        "backend": "running",
        "hf_token_configured": bool(HF_TOKEN),
        "hf_token_prefix": HF_TOKEN[:10] + "..." if HF_TOKEN else "none",
        "hf_model_url": HF_MODEL_URL,
        "supabase_configured": bool(supabase),
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "none",
        "cors_enabled": True
    }

# Handler para OPTIONS
@app.options("/etiquetar")
async def options_etiquetar():
    return {}