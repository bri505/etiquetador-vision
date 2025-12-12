import os
<<<<<<< HEAD
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
from datetime import datetime
import requests
from io import BytesIO
import traceback

# ============================================
# CONFIGURACIÓN HF_TOKEN
# ============================================
# Cargar variables de entorno
load_dotenv()

# Obtener HF_TOKEN - IMPORTANTE para modelos privados o rate limits
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mostrar info del token (sin mostrar el valor completo por seguridad)
if HF_TOKEN:
    logger.info(f"✅ HF_TOKEN configurado ({len(HF_TOKEN)} caracteres)")
    # Configurar header para requests a Hugging Face
    HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
else:
    logger.warning("⚠️  HF_TOKEN no configurado. Algunos modelos pueden tener rate limits.")
    logger.info("💡 Obtén un token gratis en: https://huggingface.co/settings/tokens")
    HF_HEADERS = {}

# ============================================
# CONFIGURACIÓN DEL MODELO
# ============================================
MODEL_NAME = os.getenv("LOCAL_MODEL", "google/vit-base-patch16-224")

# ============================================
# IMPORTAR MODELO DE HUGGING FACE
# ============================================
try:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    import torch.nn.functional as F
    
    MODEL_SUPPORT = True
    MODEL_CACHE = {}
    
    def cargar_modelo():
        """Carga el modelo usando HF_TOKEN si está disponible"""
        if not MODEL_SUPPORT:
            raise RuntimeError("Librerías de ML no instaladas")
        
        if "model" not in MODEL_CACHE:
            logger.info(f"🤖 Cargando modelo: {MODEL_NAME}")
            
            try:
                # Configurar token para la descarga
                kwargs = {}
                if HF_TOKEN:
                    kwargs["token"] = HF_TOKEN
                    kwargs["use_auth_token"] = HF_TOKEN
                
                # Cargar procesador y modelo
                processor = AutoImageProcessor.from_pretrained(MODEL_NAME, **kwargs)
                model = AutoModelForImageClassification.from_pretrained(MODEL_NAME, **kwargs)
                
                model.eval()
                
                MODEL_CACHE["model"] = model
                MODEL_CACHE["processor"] = processor
                
                logger.info(f"✅ Modelo '{MODEL_NAME}' cargado exitosamente")
                logger.info(f"   Dispositivo: {'GPU' if torch.cuda.is_available() else 'CPU'}")
                
            except Exception as e:
                logger.error(f"❌ Error cargando modelo: {e}")
                
                # Fallback a un modelo más pequeño y público
                logger.info("🔄 Intentando con modelo alternativo público...")
                try:
                    MODEL_FALLBACK = "google/vit-base-patch16-224"
                    processor = AutoImageProcessor.from_pretrained(MODEL_FALLBACK)
                    model = AutoModelForImageClassification.from_pretrained(MODEL_FALLBACK)
                    model.eval()
                    
                    MODEL_CACHE["model"] = model
                    MODEL_CACHE["processor"] = processor
                    logger.info(f"✅ Modelo alternativo '{MODEL_FALLBACK}' cargado")
                except Exception as e2:
                    logger.error(f"❌ Error con modelo alternativo: {e2}")
                    raise RuntimeError(f"No se pudo cargar ningún modelo")
        
        return MODEL_CACHE["processor"], MODEL_CACHE["model"]
    
except ImportError as e:
    logger.warning(f"⚠️  No se pudieron importar librerías de ML: {e}")
    logger.warning("   Ejecutando en modo mock")
    MODEL_SUPPORT = False

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="API de Etiquetado de Imágenes",
    description="Clasificación de imágenes usando Hugging Face",
    version="1.0.0"
)

=======
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
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLItem(BaseModel):
    url: str

<<<<<<< HEAD
# ============================================
# ENDPOINTS
# ============================================
@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "✅ Backend funcionando",
        "model": MODEL_NAME,
        "mode": "real_inference" if MODEL_SUPPORT else "mock_mode",
        "hf_token": "configured" if HF_TOKEN else "not_configured",
        "timestamp": datetime.now().isoformat()
    }
=======
@app.get("/")
def home():
    return {"status": "ok", "mensaje": "Backend funcionando"}
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8

@app.get("/health")
def health():
    return {
        "status": "healthy",
<<<<<<< HEAD
        "timestamp": datetime.now().isoformat(),
        "services": {
            "model": "ready" if MODEL_CACHE else "not_loaded",
            "hf_token": "configured" if HF_TOKEN else "not_configured",
            "api": "operational"
        }
    }

@app.post("/etiquetar")
async def etiquetar(item: URLItem):
    """Endpoint principal para etiquetar imágenes"""
    start_time = datetime.now()
    
    try:
        logger.info(f"📨 Procesando imagen: {item.url[:100]}...")
        
        # 1. Validar URL
        if not item.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URL debe comenzar con http:// o https://")
        
        # 2. Descargar imagen
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(item.url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 3. Verificar que sea imagen
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            raise HTTPException(status_code=400, detail=f"URL no apunta a una imagen. Content-Type: {content_type}")
        
        # 4. Abrir imagen
        image = Image.open(BytesIO(response.content)).convert("RGB")
        
        # 5. Procesar con modelo
        if MODEL_SUPPORT:
            try:
                # Cargar modelo
                processor, model = cargar_modelo()
                
                # Procesar imagen
                inputs = processor(images=image, return_tensors="pt")
                
                # Inferencia
                with torch.no_grad():
                    outputs = model(**inputs)
                    logits = outputs.logits
                    probabilities = F.softmax(logits, dim=-1)
                
                # Obtener top 5 predicciones
                top_probs, top_indices = torch.topk(probabilities, k=5)
                
                etiquetas = []
                for i in range(5):
                    idx = top_indices[0][i].item()
                    score = top_probs[0][i].item()
                    
                    # Obtener etiqueta legible
                    if hasattr(model.config, 'id2label') and idx in model.config.id2label:
                        label = model.config.id2label[idx]
                    else:
                        label = f"clase_{idx}"
                    
                    etiquetas.append({
                        "label": label,
                        "score": round(score, 4),
                        "percentage": round(score * 100, 2)
                    })
                
                mode = "real_inference"
                
            except Exception as e:
                logger.error(f"❌ Error en inferencia: {e}")
                # Fallback a modo mock
                etiquetas = get_mock_predictions()
                mode = "mock_fallback"
                
        else:
            # Modo mock si no hay soporte de ML
            etiquetas = get_mock_predictions()
            mode = "mock_mode"
        
        # 6. Calcular tiempo
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 7. Preparar respuesta
        response_data = {
            "status": "success",
            "url": item.url,
            "etiquetas": etiquetas,
            "modelo": MODEL_NAME,
            "tiempo_procesamiento": processing_time,
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "hf_token_used": bool(HF_TOKEN)
        }
        
        # 8. Log resultados
        logger.info(f"🏷️  Etiquetas generadas: {len(etiquetas)}")
        logger.info(f"⏱️  Tiempo: {processing_time:.2f}s")
        logger.info(f"🔧 Modo: {mode}")
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error descargando imagen: {e}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando imagen: {str(e)}")

def get_mock_predictions():
    """Predicciones mock para cuando el modelo no está disponible"""
    return [
        {"label": "computer_keyboard", "score": 0.95, "percentage": 95.0},
        {"label": "mouse", "score": 0.03, "percentage": 3.0},
        {"label": "monitor", "score": 0.02, "percentage": 2.0},
        {"label": "laptop", "score": 0.01, "percentage": 1.0},
        {"label": "desktop_computer", "score": 0.01, "percentage": 1.0}
    ]

@app.get("/model/info")
def get_model_info():
    """Información del modelo"""
    if MODEL_SUPPORT and "model" in MODEL_CACHE:
        model = MODEL_CACHE["model"]
        return {
            "modelo": MODEL_NAME,
            "tipo": type(model).__name__,
            "num_clases": model.config.num_labels,
            "estado": "cargado",
            "hf_token": "si" if HF_TOKEN else "no"
        }
    else:
        return {
            "modelo": MODEL_NAME,
            "estado": "no_cargado" if MODEL_SUPPORT else "no_soportado",
            "modo": "mock",
            "hf_token": "si" if HF_TOKEN else "no",
            "mensaje": "Usa /etiquetar para probar la API"
        }

# ============================================
# INICIALIZACIÓN
# ============================================
@app.on_event("startup")
async def startup_event():
    """Carga el modelo al iniciar"""
    logger.info("=" * 70)
    logger.info("🚀 INICIANDO ETIQUETADOR DE IMÁGENES")
    logger.info(f"🤖 Modelo: {MODEL_NAME}")
    logger.info(f"🔑 HF_TOKEN: {'✅ Configurado' if HF_TOKEN else '⚠️  No configurado'}")
    logger.info(f"⚡ ML Support: {'✅ Disponible' if MODEL_SUPPORT else '⚠️  No disponible'}")
    logger.info("=" * 70)
    
    if MODEL_SUPPORT:
        try:
            # Carga diferida - se cargará con la primera solicitud
            logger.info("📦 El modelo se cargará bajo demanda")
        except Exception as e:
            logger.error(f"❌ Error inicializando modelo: {e}")
    else:
        logger.info("🎭 Ejecutando en modo mock")

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 10000))
    
    logger.info(f"🌍 Servidor iniciando en puerto {port}")
    logger.info(f"📚 API Docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
=======
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
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
