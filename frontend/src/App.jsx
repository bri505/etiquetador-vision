import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  ref, 
  uploadBytes, 
  getDownloadURL, 
  listAll, 
  deleteObject 
} from 'firebase/storage';
import { storage } from './firebase';
import './App.css';

// URL de tu backend en producción
const BACKEND_URL = "https://etiquetador-backend.onrender.com";

function App() {
  // Estados para URL input
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  // Estados para archivos
  const [archivo, setArchivo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [urlImagenSubida, setUrlImagenSubida] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [imagenesStorage, setImagenesStorage] = useState([]);
  
  // Estados para modal
  const [modalAbierto, setModalAbierto] = useState(false);
  const [indiceActual, setIndiceActual] = useState(0);

  // Cargar imágenes de Firebase
  const cargarImagenesStorage = async () => {
    try {
      const carpetaRef = ref(storage, "imagenes/");
      const lista = await listAll(carpetaRef);

      const urls = await Promise.all(
        lista.items.map(async (item) => ({
          url: await getDownloadURL(item),
          path: item.fullPath
        }))
      );

      setImagenesStorage(urls);
    } catch (error) {
      console.error("Error obteniendo imágenes:", error);
    }
  };

  useEffect(() => {
    cargarImagenesStorage();
  }, []);

  // Funcionalidad por URL
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(
        `${BACKEND_URL}/etiquetar`, 
        { url: url },
        { timeout: 60000 }
      );
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  // Funcionalidad por archivo
  const subirYAnalizar = async () => {
    if (!archivo) return alert("Selecciona una imagen primero");
    setCargando(true);
    setError(null);

    try {
      // Subir a Firebase
      const nombre = `imagenes/${Date.now()}-${archivo.name}`;
      const imagenRef = ref(storage, nombre);
      await uploadBytes(imagenRef, archivo);
      const urlFirebase = await getDownloadURL(imagenRef);

      setUrlImagenSubida(urlFirebase);
      
      // Analizar con backend
      const resp = await axios.post(`${BACKEND_URL}/etiquetar`, { 
        url: urlFirebase 
      });

      setResult(resp.data);
      cargarImagenesStorage();
    } catch (err) {
      console.error(err);
      setError("Error: " + (err.response?.data?.detail || err.message));
    } finally {
      setCargando(false);
    }
  };

  // Funcionalidad del modal
  const abrirModal = (index) => {
    setIndiceActual(index);
    setModalAbierto(true);
  };

  const cerrarModal = () => {
    setModalAbierto(false);
  };

  const siguienteImagen = () => {
    setIndiceActual((prev) => (prev + 1) % imagenesStorage.length);
  };

  const anteriorImagen = () => {
    setIndiceActual((prev) =>
      prev === 0 ? imagenesStorage.length - 1 : prev - 1
    );
  };

  const eliminarImagen = async () => {
    const confirmar = confirm("¿Seguro que deseas eliminar esta imagen?");
    if (!confirmar) return;

    try {
      const path = imagenesStorage[indiceActual].path;
      const imgRef = ref(storage, path);
      await deleteObject(imgRef);
      
      cerrarModal();
      cargarImagenesStorage();
    } catch (error) {
      console.error("Error eliminando:", error);
      setError("Error al eliminar la imagen");
    }
  };

  return (
    <div className="contenedor">
      <header className="header">
        <h1 className="titulo">🏷️ Etiquetador de Imágenes</h1>
        <p className="subtitulo">
          Analiza imágenes por URL o sube tus propias imágenes
        </p>
        
        {error && (
          <div className="estado-sistema error">
            ⚠️ Error: {error}
          </div>
        )}
        
        {result && !error && (
          <div className="estado-sistema success">
            ✅ Análisis completado
          </div>
        )}
      </header>

      <div className="panel-principal">
        {/* Panel izquierdo: Subida de imágenes */}
        <div className="card">
          <h2>📤 Subir Imagen</h2>
          
          <div className="upload-area" onClick={() => document.getElementById('file-input').click()}>
            <div className="upload-icon">📁</div>
            <div className="upload-placeholder">
              {archivo ? archivo.name : "Haz clic o arrastra una imagen"}
            </div>
            <div className="upload-hint">
              PNG, JPG, JPEG hasta 5MB
            </div>
          </div>
          
          <input
            id="file-input"
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files[0]) {
                setArchivo(e.target.files[0]);
                setPreview(URL.createObjectURL(e.target.files[0]));
                setResult(null);
              }
            }}
          />

          {preview && (
            <div className="preview">
              <img src={preview} alt="preview" />
            </div>
          )}

          <button 
            className="btn primary" 
            onClick={subirYAnalizar} 
            disabled={cargando || !archivo}
          >
            {cargando ? (
              <>
                <span className="spinner"></span>
                Procesando...
              </>
            ) : (
              '📤 Subir y analizar'
            )}
          </button>
        </div>

        {/* Panel derecho: URL input */}
        <div className="card">
          <h2>🔗 Usar URL</h2>
          
          <form onSubmit={handleSubmit}>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://ejemplo.com/imagen.jpg"
                required
                style={{ 
                  flex: 1, 
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd'
                }}
              />
            </div>
            
            <button 
              type="submit" 
              className="btn primary"
              disabled={loading || !url}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Analizando...
                </>
              ) : (
                '🔍 Analizar URL'
              )}
            </button>
          </form>
          
          <p style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
            Backend: <a href={BACKEND_URL} target="_blank" rel="noreferrer">{BACKEND_URL}</a>
          </p>
        </div>
      </div>

      {/* Resultados */}
      {result && (
        <div className="card resultado-card">
          <h2>📊 Resultados del Análisis</h2>
          
          <div className="imagen-analizada">
            <img 
              src={urlImagenSubida || url} 
              alt="Imagen analizada" 
            />
          </div>
          
          <div className="etiquetas-container">
            <h3>🏷️ Etiquetas detectadas:</h3>
            <div className="etiquetas-grid">
              {result.predictions && result.predictions.map((pred, index) => (
                <div key={index} className="etiqueta-item">
                  <div className="etiqueta-header">
                    <div className="etiqueta-rank">#{index + 1}</div>
                    <div className="etiqueta-nombre">{pred.tagName}</div>
                  </div>
                  <div className="barra-progreso">
                    <div 
                      className="progreso-fill" 
                      style={{ width: `${pred.probability * 100}%` }}
                    ></div>
                  </div>
                  <div className="etiqueta-stats">
                    <span>Confianza:</span>
                    <span className="porcentaje">
                      {(pred.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="metadatos">
            {result.metadata && (
              <>
                <div className="metadato">
                  <strong>Ancho:</strong>
                  <span>{result.metadata.width}px</span>
                </div>
                <div className="metadato">
                  <strong>Alto:</strong>
                  <span>{result.metadata.height}px</span>
                </div>
                <div className="metadato">
                  <strong>Formato:</strong>
                  <span>{result.metadata.format}</span>
                </div>
                {result.url && (
                  <div className="metadato">
                    <strong>URL:</strong>
                    <a href={result.url} target="_blank" rel="noreferrer" className="url-enlace">
                      {result.url}
                    </a>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Galería de imágenes */}
      <div className="card galeria-card">
        <div className="galeria-header">
          <h2>📁 Imágenes guardadas</h2>
          <button className="btn secondary small" onClick={cargarImagenesStorage}>
            🔄 Actualizar
          </button>
        </div>
        
        <div className="galeria-grid">
          {imagenesStorage.length === 0 ? (
            <div className="empty-state">
              No hay imágenes guardadas aún
            </div>
          ) : (
            imagenesStorage.map((item, idx) => (
              <div
                className="galeria-item"
                key={idx}
                onClick={() => abrirModal(idx)}
              >
                <img src={item.url} alt={`Imagen ${idx + 1}`} />
                <div className="galeria-info">
                  <div className="galeria-nombre">
                    Imagen {idx + 1}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modal */}
      {modalAbierto && imagenesStorage.length > 0 && (
        <div className="modal-overlay" onClick={cerrarModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-cerrar" onClick={cerrarModal}>
              ✕
            </button>

            <img
              src={imagenesStorage[indiceActual].url}
              className="modal-img"
              alt="Vista previa"
            />

            {result && (
              <div className="etiqueta-modal">
                <h4>🏷️ Etiquetas generadas:</h4>
                <pre>{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}

            <div className="nav-botones">
              <button className="nav-btn" onClick={anteriorImagen}>
                ⟨
              </button>
              <span style={{ margin: '0 10px' }}>
                {indiceActual + 1} / {imagenesStorage.length}
              </span>
              <button className="nav-btn" onClick={siguienteImagen}>
                ⟩
              </button>
            </div>

            <button className="btn-eliminar" onClick={eliminarImagen}>
              🗑️ Eliminar imagen
            </button>
          </div>
        </div>
      )}

      <footer className="footer">
        <p>Etiquetador de Imágenes v1.0</p>
        <p className="footer-tech">
          Tecnologías: React + Firebase + Custom Vision API
        </p>
      </footer>
    </div>
  );
}

export default App;