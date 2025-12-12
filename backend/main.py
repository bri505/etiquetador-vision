import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="API de Etiquetado de Imágenes",
    description="Clasificación de imágenes usando Azure Computer Vision",
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

# Configuración de Azure
AZURE_KEY = os.getenv("AZURE_VISION_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT")

class ImageRequest(BaseModel):
    url: str

class TagPrediction(BaseModel):
    tagName: str
    probability: float

class ImageResponse(BaseModel):
    predictions: List[TagPrediction]
    metadata: dict
    url: str

@app.get("/")
def read_root():
    return {
        "message": "API de etiquetado de imágenes", 
        "version": "1.0",
        "status": "operational",
        "service": "Azure Computer Vision"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "azure_configured": bool(AZURE_KEY and AZURE_ENDPOINT),
        "timestamp": "2024-01-01T00:00:00Z"  # Placeholder, actualizar si se quiere
    }

@app.post("/etiquetar", response_model=ImageResponse)
async def etiquetar_imagen(request: ImageRequest):
    try:
        # Validar que tenemos credenciales
        if not AZURE_KEY or not AZURE_ENDPOINT:
            raise HTTPException(
                status_code=500, 
                detail="Azure credentials not configured. Set AZURE_VISION_KEY and AZURE_VISION_ENDPOINT environment variables."
            )
        
        # Crear cliente de Azure
        credentials = CognitiveServicesCredentials(AZURE_KEY)
        client = ComputerVisionClient(AZURE_ENDPOINT, credentials)
        
        # Analizar imagen
        tags_result = client.tag_image(request.url)
        
        # Procesar resultados
        predictions = [
            TagPrediction(
                tagName=tag.name, 
                probability=tag.confidence
            )
            for tag in tags_result.tags[:10]  # Top 10 etiquetas
        ]
        
        # Obtener metadata de la imagen
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.head(request.url, timeout=10)
                metadata = {
                    "content_type": response.headers.get("content-type", "unknown"),
                    "content_length": response.headers.get("content-length", "unknown"),
                }
            except:
                metadata = {
                    "content_type": "unknown", 
                    "content_length": "unknown"
                }
        
        return ImageResponse(
            predictions=predictions,
            metadata=metadata,
            url=request.url
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
