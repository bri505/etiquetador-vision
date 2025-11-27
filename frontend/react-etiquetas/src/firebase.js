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
