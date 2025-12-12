import { initializeApp } from "firebase/app";
import { getStorage } from "firebase/storage";
import { getFirestore } from "firebase/firestore";

// Configuración combinada - usando ambas configuraciones
const firebaseConfig = {
  // Configuración de tu versión local (con variables de entorno)
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyCCBta_5B1wDa3MkNKQOzIF1bhIqh8ED5g",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "etiquetas-3347a.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "etiquetas-3347a",
  
  // Usamos el storageBucket de la versión remota (corregido)
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "etiquetas-3347a.firebasestorage.app",
  
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "287987459942",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:287987459942:web:9b0eb3dbd5d21a33c84aa7",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || ""
};

// Inicializar Firebase
const app = initializeApp(firebaseConfig);
const storage = getStorage(app);
const db = getFirestore(app);

export { storage, db, app };