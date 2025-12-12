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

# ============================================
# IMPORTAR PARA MODELO LOCAL
# ============================================
try:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    import torch.nn.functional as F
    MODEL_SUPPORT = True
except ImportError as e:
    print(f"⚠️  Advertencia: No se pudieron importar librerías de ML: {e}")
    MODEL_SUPPORT = False

# ============================================
# CONFIGURACIÓN
# ============================================
print("=" * 70)
print("🚀 INICIANDO BACKEND DE ETIQUETADO DE IMÁGENES")
print("=" * 70)

# Cargar variables de entorno
load_dotenv(override=True)

# Configuración del modelo
MODEL_NAME = os.getenv("LOCAL_MODEL", "google/vit-base-patch16-224")
MODEL_CACHE = {}

# Configuración de Firebase para el backend
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    if os.path.exists("firebase-credentials.json"):
        cred = credentials.Certificate("firebase-credentials.json")
        firebase_app = firebase_admin.initialize_app(cred)
        firebase_db = firestore.client()
        print("✅ Firebase Admin SDK conectado")
    else:
        print("⚠️  Archivo firebase-credentials.json no encontrado")
        firebase_db = None
except ImportError:
    print("⚠️  Firebase Admin SDK no instalado. Ejecuta: pip install firebase-admin")
    firebase_db = None
except Exception as e:
    print(f"❌ Error inicializando Firebase: {e}")
    firebase_db = None

# ============================================
# MODELOS DE DATOS
# ============================================
class URLItem(BaseModel):
    url: str

class Etiqueta(BaseModel):
    label: str
    score: float
    percentage: float

# ============================================
# FUNCIONES DEL MODELO
# ============================================
def cargar_modelo():
    """Carga el modelo de clasificación de imágenes"""
    if not MODEL_SUPPORT:
        raise RuntimeError("Las librerías de ML no están instaladas")
    
    if "model" not in MODEL_CACHE:
        print(f"🤖 Cargando modelo: {MODEL_NAME}")
        
        try:
            # Cargar procesador y modelo
            processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
            model = AutoModelForImageClassification.from_pretrained(MODEL_NAME)
            
            # Poner en modo evaluación
            model.eval()
            
            # Cachear
            MODEL_CACHE["model"] = model
            MODEL_CACHE["processor"] = processor
            
            print(f"✅ Modelo '{MODEL_NAME}' cargado exitosamente")
            print(f"   Dispositivo: {'GPU' if torch.cuda.is_available() else 'CPU'}")
            
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            
            # Intentar con modelo alternativo
            print("🔄 Intentando con modelo alternativo (microsoft/resnet-50)...")
            try:
                MODEL_NAME_ALT = "microsoft/resnet-50"
                processor = AutoImageProcessor.from_pretrained(MODEL_NAME_ALT)
                model = AutoModelForImageClassification.from_pretrained(MODEL_NAME_ALT)
                model.eval()
                
                MODEL_CACHE["model"] = model
                MODEL_CACHE["processor"] = processor
                print(f"✅ Modelo alternativo '{MODEL_NAME_ALT}' cargado exitosamente")
            except Exception as e2:
                print(f"❌ Error con modelo alternativo: {e2}")
                raise RuntimeError(f"No se pudo cargar ningún modelo. Error: {e}")
    
    return MODEL_CACHE["processor"], MODEL_CACHE["model"]

def clasificar_imagen(image_url, top_k=5):
    """Clasifica una imagen usando el modelo"""
    try:
        print(f"📥 Descargando imagen: {image_url}")
        
        # 1. Descargar imagen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 2. Verificar que sea una imagen
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            raise ValueError(f"URL no apunta a una imagen. Content-Type: {content_type}")
        
        # 3. Abrir y convertir imagen
        image = Image.open(BytesIO(response.content)).convert("RGB")
        
        # 4. Cargar modelo
        processor, model = cargar_modelo()
        
        # 5. Procesar imagen
        inputs = processor(images=image, return_tensors="pt")
        
        # 6. Realizar inferencia
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probabilities = F.softmax(logits, dim=-1)
        
        # 7. Obtener las top_k predicciones
        top_probs, top_indices = torch.topk(probabilities, k=top_k)
        
        etiquetas = []
        for i in range(top_k):
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
        
        return etiquetas
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red: {e}")
        raise HTTPException(status_code=400, detail=f"Error descargando imagen: {e}")
    except Exception as e:
        print(f"❌ Error en clasificación: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando imagen: {str(e)}")

def guardar_en_firestore(image_url, etiquetas, processing_time):
    """Guarda los resultados en Firestore"""
    if not firebase_db:
        return None
    
    try:
        doc_ref = firebase_db.collection("etiquetados").document()
        
        data = {
            "image_url": image_url,
            "etiquetas": etiquetas,
            "modelo": MODEL_NAME,
            "tiempo_procesamiento": processing_time,
            "timestamp": datetime.now().isoformat(),
            "top_etiqueta": etiquetas[0]["label"] if etiquetas else None,
            "confianza_top": etiquetas[0]["percentage"] if etiquetas else None
        }
        
        doc_ref.set(data)
        print(f"✅ Guardado en Firestore con ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"⚠️  Error guardando en Firestore: {e}")
        return None

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="API de Etiquetado de Imágenes",
    description="Clasificación de imágenes usando modelos de Hugging Face + Firebase",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    return {
        "status": "ok",
        "message": "✅ Backend funcionando",
        "model": MODEL_NAME,
        "mode": "local_inference",
        "device": "GPU" if torch.cuda.is_available() else "CPU",
        "firebase": "conectado" if firebase_db else "no_configurado",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    model_status = "ready" if MODEL_CACHE else "not_loaded"
    return {
        "status": "healthy",
        "services": {
            "model": model_status,
            "model_name": MODEL_NAME,
            "firebase": "connected" if firebase_db else "not_configured",
            "api": "operational"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/etiquetar")
async def etiquetar(item: URLItem):
    try:
        print(f"📨 Procesando imagen: {item.url[:100]}...")
        start_time = datetime.now()
        
        # Verificar soporte de modelo
        if not MODEL_SUPPORT:
            return {
                "error": "dependencies_missing",
                "message": "Las librerías de ML no están instaladas",
                "solution": "Ejecuta: pip install torch torchvision transformers pillow"
            }
        
        # Validar URL
        if not item.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URL debe comenzar con http:// o https://")
        
        # Clasificar imagen
        etiquetas = clasificar_imagen(item.url, top_k=5)
        
        # Calcular tiempo de procesamiento
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print(f"🏷️  Etiquetas generadas: {len(etiquetas)}")
        print(f"⏱️  Tiempo de procesamiento: {processing_time:.2f}s")
        
        # Mostrar top 3 etiquetas en consola
        for etiqueta in etiquetas[:3]:
            print(f"   {etiqueta['label']}: {etiqueta['percentage']}%")
        
        # Guardar en Firestore
        firestore_id = None
        if firebase_db:
            firestore_id = guardar_en_firestore(item.url, etiquetas, processing_time)
        
        # Preparar respuesta
        response_data = {
            "status": "success",
            "url": item.url,
            "etiquetas": etiquetas,
            "modelo": MODEL_NAME,
            "tiempo_procesamiento": processing_time,
            "timestamp": datetime.now().isoformat(),
            "top_etiqueta": etiquetas[0]["label"] if etiquetas else None,
            "confianza_top": etiquetas[0]["percentage"] if etiquetas else None
        }
        
        if firestore_id:
            response_data["firestore_id"] = firestore_id
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando imagen: {str(e)}"
        )

@app.get("/modelo/info")
async def get_model_info():
    """Obtiene información sobre el modelo cargado"""
    try:
        if "model" in MODEL_CACHE:
            model = MODEL_CACHE["model"]
            return {
                "modelo": MODEL_NAME,
                "tipo": type(model).__name__,
                "num_clases": model.config.num_labels,
                "dispositivo": "GPU" if torch.cuda.is_available() else "CPU",
                "estado": "cargado"
            }
        else:
            return {
                "modelo": MODEL_NAME,
                "estado": "no_cargado",
                "mensaje": "El modelo se cargará bajo demanda"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/historial")
async def get_historial(limite: int = 10):
    """Obtiene el historial de etiquetados"""
    if not firebase_db:
        return {
            "error": "firebase_no_configurado",
            "message": "Firebase no está configurado en el backend"
        }
    
    try:
        docs = firebase_db.collection("etiquetados")\
            .order_by("timestamp", direction=firestore.Query.DESCENDING)\
            .limit(limite)\
            .stream()
        
        historial = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            historial.append(data)
        
        return {
            "status": "success",
            "count": len(historial),
            "historial": historial
        }
    except Exception as e:
        print(f"❌ Error obteniendo historial: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_endpoint():
    """Endpoint de prueba"""
    return {
        "message": "✅ Backend funcionando correctamente",
        "model": MODEL_NAME,
        "firebase": "conectado" if firebase_db else "no_conectado",
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# INICIALIZACIÓN
# ============================================
@app.on_event("startup")
async def startup_event():
    """Carga el modelo al iniciar la aplicación"""
    print("\n" + "=" * 70)
    print("🔄 INICIALIZANDO APLICACIÓN...")
    print(f"📦 Modelo: {MODEL_NAME}")
    
    if MODEL_SUPPORT:
        try:
            cargar_modelo()
            print("✅ Modelo precargado exitosamente")
        except Exception as e:
            print(f"⚠️  Error precargando modelo: {e}")
            print("   El modelo se cargará bajo demanda...")
    else:
        print("⚠️  Modo demo: Librerías de ML no instaladas")
    
    print("=" * 70)

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 10000))
    
    print("\n" + "=" * 70)
    print("🚀 SERVICIO INICIANDO")
    print(f"🌐 URL: http://localhost:{port}")
    print(f"📚 Docs: http://localhost:{port}/docs")
    print(f"🤖 Modelo: {MODEL_NAME}")
    print(f"🔥 Firebase: {'Conectado' if firebase_db else 'No configurado'}")
    print("=" * 70)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        timeout_keep_alive=300
    )