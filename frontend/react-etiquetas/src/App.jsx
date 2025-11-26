import { useState } from "react";
import axios from "axios";
import { ref, uploadBytes, getDownloadURL } from "firebase/storage";
import { storage } from "./firebase";

function App() {
  const [archivo, setArchivo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);

  const subirYAnalizar = async () => {
    if (!archivo) return alert("Selecciona una imagen primero");
    setCargando(true);

    try {
      // 1) Subir a Firebase Storage
      const nombre = `imagenes/${Date.now()}-${archivo.name}`;
      const imagenRef = ref(storage, nombre);
      await uploadBytes(imagenRef, archivo);
      const url = await getDownloadURL(imagenRef);

      // 2) Enviar URL al backend
      // PON LA URL DE TU BACKEND DEPLOY EN RENDER:
      const BACKEND_URL = "https://TU_BACKEND.onrender.com/etiquetar";

      const resp = await axios.post(BACKEND_URL, { url });
      setResultado(resp.data);
    } catch (err) {
      console.error(err);
      alert("Error: " + (err.response?.data?.detail || err.message));
    } finally {
      setCargando(false);
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      <h1>Generador de Etiquetas (Cloud)</h1>

      <input
        type="file"
        accept="image/*"
        onChange={(e) => {
          setArchivo(e.target.files[0]);
          setPreview(URL.createObjectURL(e.target.files[0]));
        }}
      />

      {preview && (
        <div style={{ marginTop: 12 }}>
          <img src={preview} alt="preview" style={{ width: 240 }} />
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <button onClick={subirYAnalizar} disabled={cargando}>
          {cargando ? "Procesando..." : "Subir y generar etiquetas"}
        </button>
      </div>

      {resultado && (
        <div style={{ marginTop: 20 }}>
          <h3>Resultado</h3>
          <pre style={{ background: "#f3f3f3", padding: 12 }}>
            {JSON.stringify(resultado, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default App;
