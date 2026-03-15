# CricNow 🏏
### Live IPL & Cricket Score App

A real-time cricket scoring app with live scores, animations, and multi-language commentary.

## 🌐 Live App
> https://YOUR_PROJECT_ID.web.app

## 📁 File Structure
```
cricnow-app/
├── index.html                    ← Main app (auto-redirects)
├── cricnow-ipl-v9.html           ← Main cricket app
├── cricnow-admin.html            ← Admin panel
├── sw.js                         ← Push notification service worker
├── firebase.json                 ← Firebase hosting config
├── .firebaserc                   ← Firebase project ID
├── database.rules.json           ← Realtime DB security rules
├── requirements.txt              ← Python dependencies
├── cricnow-scraper.py            ← Python scraper (optional local use)
├── cricnow-server.py             ← Local dev server (optional)
├── functions/
│   ├── index.js                  ← Cloud Functions (auto scraper)
│   └── package.json              ← Functions dependencies
└── .github/
    └── workflows/
        └── deploy.yml            ← Auto-deploy to Firebase
```

## 🚀 Setup
See DEEP_SETUP_GUIDE.md for complete instructions.

## 🔑 Required GitHub Secrets
| Secret | Value |
|--------|-------|
| `FIREBASE_TOKEN` | `firebase login:ci` output |
| `FIREBASE_PROJECT_ID` | Your Firebase project ID |
| `CRICAPI_KEY` | From cricapi.com |
| `NEWSAPI_KEY` | From newsapi.org |
| `GEMINI_API_KEY` | From aistudio.google.com |

## 📱 Features
- ✅ Live scores (updates every 1 minute via Cloud Functions)
- ✅ IPL + International + Domestic + Women matches
- ✅ Hindi / Hinglish / English commentary
- ✅ Animations (4, 6, wicket, milestones)
- ✅ Push notifications via FCM
- ✅ Admin panel (match management, API config, ads)
- ✅ 3 themes (Light / Dark / Multicolour)
- ✅ Auto-deploy via GitHub Actions
