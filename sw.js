// CricNow Service Worker — Firebase Cloud Messaging
// Ye file notifications ke liye hai

importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js');

// ⚠️ APNA FIREBASE CONFIG YAHAN DAALO
firebase.initializeApp({
  apiKey: "AIzaSyBmq16jmf18cXbrDXaciVRKD0pn4DwQok8",
  authDomain: "cricnow-app.firebaseapp.com",
  projectId: "cricnow-app",
  storageBucket: "cricnow-app.firebasestorage.app",
  messagingSenderId: "56401395901",
  appId: "1:56401395901:web:a8ba466fd17dc6d9bdb7d4"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification || {};
  if (!title) return;
  self.registration.showNotification(title, {
    body: body || '',
    icon: '/icon-192.png',
    badge: '/icon-72.png',
    tag: 'cricnow',
    vibrate: [200, 100, 200],
    data: { url: payload.data?.url || '/' }
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data?.url || '/')
  );
});
