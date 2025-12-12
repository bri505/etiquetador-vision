import { initializeApp } from "firebase/app";
import { getStorage } from "firebase/storage";
import { getFirestore } from "firebase/firestore";

// Configuración de Firebase (usa tus propias credenciales)
const firebaseConfig = {
  apiKey: "AIzaSyCCBta_5B1wDa3MkNKQOzIF1bhIqh8ED5g",
  authDomain: "etiquetas-3347a.firebaseapp.com",
  projectId: "etiquetas-3347a",
  storageBucket: "etiquetas-3347a.firebasestorage.app",
  messagingSenderId: "287987459942",
  appId: "1:287987459942:web:9b0eb3dbd5d21a33c84aa7"
};

// Inicializar Firebase
const app = initializeApp(firebaseConfig);
const storage = getStorage(app);
const db = getFirestore(app);

export { storage, db };