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
    }
  };

  return (
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
    </div>
  );
}

export default App;