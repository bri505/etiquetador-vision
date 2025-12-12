import { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  ref,
  uploadBytes,
  getDownloadURL,
  listAll,
  deleteObject
} from "firebase/storage";
import { storage, db } from "./firebase";
import { collection, addDoc, getDocs, query, orderBy, limit, deleteDoc, doc } from "firebase/firestore";
import "./App.css";

function App() {
  const [archivo, setArchivo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [urlImagenSubida, setUrlImagenSubida] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [imagenesStorage, setImagenesStorage] = useState([]);
  const [historialEtiquetas, setHistorialEtiquetas] = useState([]);
  const [historialCargando, setHistorialCargando] = useState(false);

  const [modalAbierto, setModalAbierto] = useState(false);
  const [indiceActual, setIndiceActual] = useState(0);
  const [estadoBackend, setEstadoBackend] = useState(null);

  const fileInputRef = useRef(null);

  // Verificar estado del backend
  useEffect(() => {
    verificarBackend();
  }, []);

  // Cargar imágenes y historial
  useEffect(() => {
    cargarImagenesStorage();
    cargarHistorial();
  }, []);

  const verificarBackend = async () => {
    try {
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:10000";
      const response = await axios.get(`${BACKEND_URL}/health`, { timeout: 5000 });
      setEstadoBackend(response.data);
      console.log("✅ Backend conectado:", response.data);
    } catch (error) {
      console.error("❌ Backend no disponible:", error.message);
      setEstadoBackend({
        status: "error",
        message: "Backend no disponible. Verifica que esté ejecutándose."
      });
    }
  };

  const cargarImagenesStorage = async () => {
    try {
      const carpetaRef = ref(storage, "imagenes/");
      const lista = await listAll(carpetaRef);

      const urls = await Promise.all(
        lista.items.map(async (item) => ({
          url: await getDownloadURL(item),
          path: item.fullPath,
          nombre: item.name
        }))
      );

      setImagenesStorage(urls);
    } catch (error) {
      console.error("Error obteniendo imágenes:", error);
    }
  };

  const cargarHistorial = async () => {
    setHistorialCargando(true);
    try {
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:10000";
      const response = await axios.get(`${BACKEND_URL}/historial?limite=20`);
      
      if (response.data.status === "success") {
        setHistorialEtiquetas(response.data.historial);
      }
    } catch (error) {
      console.error("Error cargando historial:", error);
    } finally {
      setHistorialCargando(false);
    }
  };

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
    const confirmar = confirm("¿Seguro que deseas eliminar esta imagen y su historial?");
    
    if (!confirmar) return;

    try {
      const path = imagenesStorage[indiceActual].path;
      const imgRef = ref(storage, path);

      await deleteObject(imgRef);
      alert("✅ Imagen eliminada con éxito.");
      
      cerrarModal();
      cargarImagenesStorage();
    } catch (error) {
      console.error("Error eliminando:", error);
      alert("❌ Error al eliminar la imagen");
    }
  };

  const limpiarTodo = () => {
    setArchivo(null);
    setPreview(null);
    setResultado(null);
    setUrlImagenSubida(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const subirYAnalizar = async () => {
    if (!archivo) {
      alert("📸 Selecciona una imagen primero");
      return;
    }
    
    setCargando(true);
    setResultado(null);

    try {
      // 1. Subir a Firebase Storage
      const nombre = `imagenes/${Date.now()}-${archivo.name}`;
      const imagenRef = ref(storage, nombre);
      await uploadBytes(imagenRef, archivo);
      const url = await getDownloadURL(imagenRef);

      setUrlImagenSubida(url);
      console.log("✅ Imagen subida a Firebase:", url);

      // 2. Enviar al backend para etiquetado
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:10000";
      
      console.log("📤 Enviando a backend:", BACKEND_URL);
      
      const response = await axios.post(
        `${BACKEND_URL}/etiquetar`, 
        { url: url }, 
        { 
          timeout: 60000,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log("✅ Respuesta del backend:", response.data);
      
      // Manejar posibles errores del backend
      if (response.data.error) {
        if (response.data.error === "dependencies_missing") {
          alert(`⚠️  Error: ${response.data.message}\n\nSolución: ${response.data.solution}`);
        } else {
          alert(`Error: ${response.data.message}`);
        }
        return;
      }

      if (response.data.status === "success") {
        setResultado(response.data);
        alert("🎉 ¡Etiqueta generada exitosamente!");
        
        // 3. Guardar en Firestore (si el backend no lo hizo)
        try {
          await addDoc(collection(db, "etiquetados_frontend"), {
            ...response.data,
            fecha_frontend: new Date().toISOString()
          });
        } catch (firestoreError) {
          console.log("⚠️  No se pudo guardar en Firestore frontend:", firestoreError);
        }
        
        // Actualizar listas
        cargarImagenesStorage();
        cargarHistorial();
      } else {
        alert("❌ Error en la respuesta del backend");
      }
      
    } catch (error) {
      console.error("❌ Error completo:", error);
      
      let mensajeError = "Error desconocido";
      
      if (error.code === "storage/unauthorized") {
        mensajeError = "No tienes permisos para subir imágenes. Verifica las reglas de Firebase Storage.";
      } else if (error.code === "storage/network-request-failed") {
        mensajeError = "Error de red. Verifica tu conexión a internet.";
      } else if (error.response) {
        // Error del backend
        const { data, status } = error.response;
        if (status === 400) {
          mensajeError = `Error en la solicitud: ${data.detail || data.message}`;
        } else if (status === 500) {
          mensajeError = `Error del servidor: ${data.detail || data.message}`;
        } else if (data.detail) {
          mensajeError = data.detail;
        } else if (data.message) {
          mensajeError = data.message;
        }
      } else if (error.request) {
        // No hubo respuesta
        mensajeError = "No se pudo conectar con el backend. Asegúrate de que esté ejecutándose.";
      } else {
        mensajeError = error.message;
      }
      
      alert("❌ Error: " + mensajeError);
    } finally {
      setCargando(false);
    }
  };

  const eliminarDelHistorial = async (id, index) => {
    if (!confirm("¿Eliminar este registro del historial?")) return;
    
    try {
      // Intentar eliminar del backend
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:10000";
      
      try {
        await axios.delete(`${BACKEND_URL}/historial/${id}`);
      } catch (e) {
        console.log("El backend no tiene endpoint DELETE, continuando...");
      }
      
      // Actualizar estado local
      setHistorialEtiquetas(prev => prev.filter((_, i) => i !== index));
      alert("✅ Registro eliminado del historial");
    } catch (error) {
      console.error("Error eliminando:", error);
      alert("❌ Error al eliminar del historial");
    }
  };

  return (
    <div className="contenedor">
      <h1 className="titulo">🏷️ Etiquetador Inteligente de Imágenes</h1>
      <p className="subtitulo">Powered by Hugging Face + Firebase + FastAPI</p>

      {/* Estado del sistema */}
      {estadoBackend && (
        <div className={`estado-sistema ${estadoBackend.status === "error" ? "error" : "success"}`}>
          <strong>Estado del sistema:</strong> 
          {estadoBackend.status === "error" ? " ⚠️ Backend no disponible" : " ✅ Sistema operativo"}
          {estadoBackend.services?.model_name && ` | Modelo: ${estadoBackend.services.model_name}`}
        </div>
      )}

      {/* Panel principal */}
      <div className="panel-principal">
        <div className="card">
          <h2>📤 Subir Imagen</h2>
          
          <div className="upload-area" onClick={() => fileInputRef.current?.click()}>
            {preview ? (
              <img src={preview} alt="Vista previa" className="preview-image" />
            ) : (
              <div className="upload-placeholder">
                <span className="upload-icon">📁</span>
                <p>Haz clic o arrastra una imagen aquí</p>
                <p className="upload-hint">Formatos: JPG, PNG, WebP (Max 5MB)</p>
              </div>
            )}
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files[0];
              if (file) {
                if (file.size > 5 * 1024 * 1024) {
                  alert("⚠️ La imagen es muy grande. Máximo 5MB.");
                  return;
                }
                setArchivo(file);
                setPreview(URL.createObjectURL(file));
              }
            }}
            style={{ display: 'none' }}
          />

          <div className="botones-accion">
            <button 
              className={`btn ${!archivo ? 'disabled' : 'primary'}`} 
              onClick={subirYAnalizar} 
              disabled={cargando || !archivo}
            >
              {cargando ? (
                <>
                  <span className="spinner"></span>
                  Procesando...
                </>
              ) : (
                "🚀 Subir y Analizar"
              )}
            </button>
            
            <button 
              className="btn secondary" 
              onClick={limpiarTodo}
              disabled={cargando}
            >
              🗑️ Limpiar
            </button>
          </div>
        </div>

        {/* Resultados */}
        {resultado && (
          <div className="card resultado-card">
            <h2>📊 Resultados del Análisis</h2>
            
            {urlImagenSubida && (
              <div className="imagen-analizada">
                <img src={urlImagenSubida} alt="Imagen analizada" />
              </div>
            )}
            
            <div className="etiquetas-container">
              <h3>🏷️ Etiquetas Detectadas</h3>
              <div className="etiquetas-grid">
                {resultado.etiquetas?.map((etiqueta, idx) => (
                  <div key={idx} className="etiqueta-item">
                    <div className="etiqueta-header">
                      <span className="etiqueta-rank">#{idx + 1}</span>
                      <span className="etiqueta-nombre">{etiqueta.label}</span>
                    </div>
                    
                    <div className="barra-progreso">
                      <div 
                        className="progreso-fill"
                        style={{ width: `${etiqueta.percentage}%` }}
                      ></div>
                    </div>
                    
                    <div className="etiqueta-stats">
                      <span className="porcentaje">{etiqueta.percentage}%</span>
                      <span className="confianza">Confianza: {etiqueta.score.toFixed(4)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="metadatos">
              <div className="metadato">
                <strong>🤖 Modelo:</strong> {resultado.modelo}
              </div>
              <div className="metadato">
                <strong>⏱️ Tiempo:</strong> {resultado.tiempo_procesamiento?.toFixed(2)}s
              </div>
              <div className="metadato">
                <strong>🔗 URL:</strong> 
                <a href={resultado.url} target="_blank" rel="noopener noreferrer" className="url-enlace">
                  Ver imagen original
                </a>
              </div>
              {resultado.firestore_id && (
                <div className="metadato">
                  <strong>📝 ID:</strong> {resultado.firestore_id}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Galería de imágenes */}
      <div className="card galeria-card">
        <div className="galeria-header">
          <h2>📁 Galería de Imágenes ({imagenesStorage.length})</h2>
          <button className="btn small" onClick={cargarImagenesStorage}>
            🔄 Actualizar
          </button>
        </div>
        
        {imagenesStorage.length === 0 ? (
          <p className="empty-state">No hay imágenes almacenadas.</p>
        ) : (
          <div className="galeria-grid">
            {imagenesStorage.map((item, idx) => (
              <div 
                className="galeria-item" 
                key={idx}
                onClick={() => abrirModal(idx)}
              >
                <img src={item.url} alt={`Imagen ${idx + 1}`} />
                <div className="galeria-info">
                  <span className="galeria-nombre">{item.nombre.substring(0, 20)}...</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historial de etiquetados */}
      <div className="card historial-card">
        <div className="historial-header">
          <h2>📜 Historial de Análisis ({historialEtiquetas.length})</h2>
          <button className="btn small" onClick={cargarHistorial} disabled={historialCargando}>
            {historialCargando ? "Cargando..." : "🔄 Actualizar"}
          </button>
        </div>
        
        {historialCargando ? (
          <div className="loading-historial">
            <div className="spinner small"></div>
            <p>Cargando historial...</p>
          </div>
        ) : historialEtiquetas.length === 0 ? (
          <p className="empty-state">No hay análisis en el historial.</p>
        ) : (
          <div className="historial-list">
            {historialEtiquetas.map((item, idx) => (
              <div key={idx} className="historial-item">
                <div className="historial-imagen">
                  <img src={item.image_url} alt="Historial" />
                </div>
                <div className="historial-contenido">
                  <h4>{item.top_etiqueta || "Sin etiqueta"}</h4>
                  <p><strong>Confianza:</strong> {item.confianza_top || 0}%</p>
                  <p><strong>Modelo:</strong> {item.modelo}</p>
                  <p><strong>Tiempo:</strong> {item.tiempo_procesamiento?.toFixed(2)}s</p>
                  <p className="historial-fecha">
                    {new Date(item.timestamp).toLocaleString()}
                  </p>
                </div>
                <div className="historial-acciones">
                  <button 
                    className="btn danger small"
                    onClick={() => eliminarDelHistorial(item.id, idx)}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal de galería */}
      {modalAbierto && imagenesStorage[indiceActual] && (
        <div className="modal-overlay" onClick={cerrarModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={cerrarModal}>✕</button>
            
            <div className="modal-imagen">
              <img 
                src={imagenesStorage[indiceActual].url} 
                alt="Modal" 
              />
            </div>
            
            <div className="modal-info">
              <h3>Información de la imagen</h3>
              <p><strong>Nombre:</strong> {imagenesStorage[indiceActual].nombre}</p>
              <p><strong>Ruta:</strong> {imagenesStorage[indiceActual].path}</p>
            </div>
            
            <div className="modal-navegacion">
              <button className="nav-btn" onClick={anteriorImagen}>⟨ Anterior</button>
              <span>{indiceActual + 1} / {imagenesStorage.length}</span>
              <button className="nav-btn" onClick={siguienteImagen}>Siguiente ⟩</button>
            </div>
            
            <div className="modal-acciones">
              <a 
                href={imagenesStorage[indiceActual].url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="btn small"
              >
                🔗 Abrir en nueva pestaña
              </a>
              <button className="btn danger small" onClick={eliminarImagen}>
                🗑️ Eliminar imagen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>
          <strong>Etiquetador Inteligente</strong> • 
          Backend: {import.meta.env.VITE_BACKEND_URL || "localhost:10000"} • 
          Modelo: {estadoBackend?.services?.model_name || "Cargando..."}
        </p>
        <p className="footer-tech">
          Tecnologías: React • FastAPI • Hugging Face • Firebase • Render
        </p>
      </footer>
    </div>
  );
}

export default App;