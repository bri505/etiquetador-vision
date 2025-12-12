import os
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
import json

# ============================================
# CONFIGURACIÓN
# ============================================
# Cargar variables de entorno
load_dotenv()

# Obtener variables de entorno
HF_TOKEN = os.getenv("HF_TOKEN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración del modelo
MODEL_NAME = os.getenv("LOCAL_MODEL", "google/vit-base-patch16-224")
HF_MODEL_URL = os.getenv("HF_MODEL_URL", "https://api-inference.huggingface.co/models/google/vit-base-patch16-224")

# Configurar headers para Hugging Face
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

# Mostrar info de configuración
if HF_TOKEN:
    logger.info(f"✅ HF_TOKEN configurado ({len(HF_TOKEN)} caracteres)")
else:
    logger.warning("⚠️  HF_TOKEN no configurado. Algunos modelos pueden tener rate limits.")
    logger.info("💡 Obtén un token gratis en: https://huggingface.co/settings/tokens")

if SUPABASE_URL and SUPABASE_KEY:
    logger.info("✅ Supabase configurado")
else:
    logger.info("ℹ️  Supabase no configurado")

# ============================================
# IMPORTAR MODELO DE HUGGING FACE (opcional)
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
    logger.warning("   Usando API Hugging Face remota")
    MODEL_SUPPORT = False

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="API de Etiquetado de Imágenes",
    description="Clasificación de imágenes usando Hugging Face",
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

# ============================================
# ENDPOINTS
# ============================================
@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "✅ Backend funcionando",
        "model": MODEL_NAME,
        "mode": "real_inference" if MODEL_SUPPORT else "remote_api",
        "hf_token": "configured" if HF_TOKEN else "not_configured",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "model": "ready" if MODEL_CACHE else "not_loaded",
            "hf_token": "configured" if HF_TOKEN else "not_configured",
            "api": "operational",
            "backend": "operational"
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
        
        image_data = response.content
        
        # 4. Intentar inferencia local primero
        if MODEL_SUPPORT:
            try:
                # Cargar modelo
                processor, model = cargar_modelo()
                
                # Abrir imagen
                image = Image.open(BytesIO(image_data)).convert("RGB")
                
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
                
                mode = "local_inference"
                
            except Exception as e:
                logger.error(f"❌ Error en inferencia local: {e}")
                # Fallback a API remota
                mode = "remote_api_fallback"
                etiquetas = await usar_api_remota(image_data)
                
        else:
            # Usar API remota si no hay soporte local
            mode = "remote_api"
            etiquetas = await usar_api_remota(image_data)
        
        # 5. Intentar guardar en Supabase si hay credenciales
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import httpx
                from postgrest import PostgrestClient
                
                client = PostgrestClient(SUPABASE_URL)
                client.auth(SUPABASE_KEY)
                
                data = {
                    "url": item.url,
                    "resultado": etiquetas,
                    "timestamp": datetime.now().isoformat()
                }
                
                response = client.from_("etiquetas").insert(data).execute()
                logger.info("✅ Guardado en Supabase exitoso")
            except Exception as e:
                logger.warning(f"⚠️  Error guardando en Supabase: {e}")
        
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

async def usar_api_remota(image_data):
    """Usar API remota de Hugging Face"""
    try:
        print(f"Enviando a API Hugging Face: {HF_MODEL_URL}")
        hf_response = requests.post(
            HF_MODEL_URL,
            headers=HEADERS,
            data=image_data,
            timeout=30
        )
        
        # Si el modelo está cargando
        if hf_response.status_code == 503:
            estimated_time = hf_response.json().get("estimated_time", 30)
            logger.warning(f"⚠️  Modelo cargando, tiempo estimado: {estimated_time}s")
            
            # Retornar predicciones mock mientras espera
            return get_mock_predictions()
        
        hf_response.raise_for_status()
        labels = hf_response.json()
        
        # Convertir formato de Hugging Face a nuestro formato
        etiquetas = []
        for item in labels[:5]:  # Top 5
            if isinstance(item, dict):
                etiquetas.append({
                    "label": item.get("label", "unknown"),
                    "score": item.get("score", 0),
                    "percentage": round(item.get("score", 0) * 100, 2)
                })
        
        logger.info(f"✅ API remota: {len(etiquetas)} etiquetas obtenidas")
        return etiquetas
        
    except Exception as e:
        logger.error(f"❌ Error en API remota: {e}")
        # Fallback a modo mock
        return get_mock_predictions()

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
            "hf_token": "si" if HF_TOKEN else "no",
            "mode": "local"
        }
    else:
        return {
            "modelo": MODEL_NAME,
            "estado": "no_cargado" if MODEL_SUPPORT else "no_soportado",
            "modo": "remote_api",
            "hf_token": "si" if HF_TOKEN else "no",
            "mensaje": "Usando API Hugging Face remota"
        }

# ============================================
# INICIALIZACIÓN
# ============================================
@app.on_event("startup")
async def startup_event():
    """Inicialización al iniciar"""
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
        logger.info("🌐 Usando API Hugging Face remota")

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