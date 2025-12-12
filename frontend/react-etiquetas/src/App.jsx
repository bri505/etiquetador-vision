<<<<<<< HEAD
import { useState } from 'react';
import axios from 'axios';
import './App.css';

// URL de tu backend en producción
const BACKEND_URL = "https://etiquetador-backend.onrender.com";

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

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
=======
import { useState, useEffect } from "react";
import axios from "axios";
import {
  ref,
  uploadBytes,
  getDownloadURL,
  listAll,
  deleteObject
} from "firebase/storage";
import { storage } from "./firebase";
import "./App.css";

function App() {
  const [archivo, setArchivo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [urlImagenSubida, setUrlImagenSubida] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [imagenesStorage, setImagenesStorage] = useState([]);

  const [modalAbierto, setModalAbierto] = useState(false);
  const [indiceActual, setIndiceActual] = useState(0);

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

      alert("Imagen eliminada con éxito.");

      cerrarModal();
      cargarImagenesStorage();
    } catch (error) {
      console.error("Error eliminando:", error);
    }
  };

  const subirYAnalizar = async () => {
    if (!archivo) return alert("Selecciona una imagen primero");
    setCargando(true);

    try {
      const nombre = `imagenes/${Date.now()}-${archivo.name}`;
      const imagenRef = ref(storage, nombre);
      await uploadBytes(imagenRef, archivo);
      const url = await getDownloadURL(imagenRef);

      setUrlImagenSubida(url);
      alert("Imagen subida correctamente ✔️");

      const BACKEND_URL = "https://TU_BACKEND.onrender.com/etiquetar";
      const resp = await axios.post(BACKEND_URL, { url });

      setResultado(resp.data);

      alert("Etiqueta generada ✔️");

      cargarImagenesStorage();
    } catch (err) {
      console.error(err);
      alert("Error: " + (err.response?.data?.detail || err.message));
    } finally {
      setCargando(false);
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
    }
  };

  return (
<<<<<<< HEAD
    <div className="app">
      <h1>🏷️ Etiquetador de Imágenes</h1>
      <p>Backend: <a href={BACKEND_URL} target="_blank">{BACKEND_URL}</a></p>
      
      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://ejemplo.com/imagen.jpg"
          required
          style={{ width: '300px', padding: '10px' }}
        />
        <button type="submit" disabled={loading} style={{ padding: '10px 20px' }}>
          {loading ? 'Procesando...' : 'Etiquetar'}
        </button>
      </form>
      
      {error && <div style={{ color: 'red', margin: '10px 0' }}>Error: {error}</div>}
      
      {result && (
        <div style={{ marginTop: '20px', textAlign: 'left' }}>
          <h2>Resultados:</h2>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: '15px', 
            borderRadius: '5px',
            overflow: 'auto'
          }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
=======
    <div className="contenedor">
      <h1 className="titulo">Generador de Etiquetas (Cloud)</h1>

      <div className="card">
        <input
          type="file"
          accept="image/*"
          onChange={(e) => {
            setArchivo(e.target.files[0]);
            setPreview(URL.createObjectURL(e.target.files[0]));
          }}
        />

        {preview && (
          <div className="preview">
            <img src={preview} alt="preview" />
          </div>
        )}

        <button className="btn" onClick={subirYAnalizar} disabled={cargando}>
          {cargando ? "Procesando..." : "Subir y generar etiquetas"}
        </button>
      </div>

      {urlImagenSubida && (
        <div className="card">
          <h3>Imagen subida a Firebase:</h3>
          <img src={urlImagenSubida} alt="subida" className="imagen-subida" />
        </div>
      )}

      {resultado && (
        <div className="card">
          <h3>Resultado:</h3>
          <pre className="resultado-box">
            {JSON.stringify(resultado, null, 2)}
          </pre>
        </div>
      )}

      <div className="galeria-contenedor">
        <h2>📁 Imágenes guardadas en el Storage</h2>

        <button className="btn" onClick={cargarImagenesStorage}>
          Recargar imágenes
        </button>

        <div className="galeria">
          {imagenesStorage.length === 0 ? (
            <p>No hay imágenes guardadas.</p>
          ) : (
            imagenesStorage.map((item, idx) => (
              <div
                className="galeria-item"
                key={idx}
                onClick={() => abrirModal(idx)}
              >
                <img src={item.url} alt="storage-img" />
              </div>
            ))
          )}
        </div>
      </div>

      {/* ---------------- MODAL ---------------- */}
      {modalAbierto && (
        <div className="modal-overlay" onClick={cerrarModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-cerrar" onClick={cerrarModal}>
              ✕
            </button>

            <img
              src={imagenesStorage[indiceActual].url}
              className="modal-img"
            />

            {/* AQUI SE AGREGA LA ETIQUETA DEBAJO DE LA IMAGEN */}
            {resultado && (
              <div className="etiqueta-modal">
                <h4>Etiqueta generada:</h4>
                <pre>{JSON.stringify(resultado, null, 2)}</pre>
              </div>
            )}

            <div className="nav-botones">
              <button className="nav-btn" onClick={anteriorImagen}>⟨</button>
              <button className="nav-btn" onClick={siguienteImagen}>⟩</button>
            </div>

            <button className="btn-eliminar" onClick={eliminarImagen}>
              🗑️ Eliminar imagen
            </button>
          </div>
        </div>
      )}
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
    </div>
  );
}

<<<<<<< HEAD
export default App;
=======
export default App;
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
