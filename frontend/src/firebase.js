// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyCBlFS59N4IC7tIsk4XX4mkqFQ_w0tz9OQ",
  authDomain: "greenroi.firebaseapp.com",
  projectId: "greenroi",
  storageBucket: "greenroi.firebasestorage.app",
  messagingSenderId: "554257170152",
  appId: "1:554257170152:web:0771c78e31ea95fd32535d",
  measurementId: "G-GGWGHEZVKK"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);