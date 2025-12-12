<<<<<<< HEAD
import { initializeApp } from "firebase/app";
import { getStorage } from "firebase/storage";
import { getFirestore } from "firebase/firestore";

// Configuración de Firebase (usa variables de entorno)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Inicializar Firebase
const app = initializeApp(firebaseConfig);
const storage = getStorage(app);
const db = getFirestore(app);

export { storage, db };
=======
// src/firebase.js
import { initializeApp } from "firebase/app";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyCCBta_5B1wDa3MkNKQOzIF1bhIqh8ED5g",
  authDomain: "etiquetas-3347a.firebaseapp.com",
  projectId: "etiquetas-3347a",
  storageBucket: "etiquetas-3347a.firebasestorage.app",   // ← CORREGIDO
  messagingSenderId: "287987459942",
  appId: "1:287987459942:web:9b0eb3dbd5d21a33c84aa7"
};

const app = initializeApp(firebaseConfig);
export const storage = getStorage(app);
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
