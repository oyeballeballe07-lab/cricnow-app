// functions/index.js — CricNow Cloud Functions
// Deploy: firebase deploy --only functions

const functions = require("firebase-functions");
const admin = require("firebase-admin");
const axios = require("axios");

admin.initializeApp();
const db = admin.database();
const firestore = admin.firestore();

const CRICAPI_KEY = functions.config().cricapi?.key || "";
const NEWSAPI_KEY = functions.config().newsapi?.key || "";

// ── Score Fetcher (every 1 min) ──
exports.fetchScores = functions.region("asia-south1")
  .pubsub.schedule("every 1 minutes").onRun(async () => {
    if (!CRICAPI_KEY) { console.log("No CricAPI key"); return null; }
    try {
      const res = await axios.get(
        `https://cricapi.com/api/currentMatches?apikey=${CRICAPI_KEY}`,
        { timeout: 8000 }
      );
      const matches = (res.data.matches || []).map(m => ({
        id: String(m.unique_id || Date.now()),
        t1: m["team-1"] || "TBA", t2: m["team-2"] || "TBA",
        f1: getFlag(m["team-1"] || ""), f2: getFlag(m["team-2"] || ""),
        series: `${m.type || "T20"} · ${m.series || ""}`,
        venue: m.venue || "",
        status: m.matchStarted ? "live" : "upcoming",
        s1: m.score?.[m["team-1"]] || "",
        s2: m.score?.[m["team-2"]] || "",
        note: m.status || "",
        cat: classifyMatch(m.series || "", m.type || ""),
        time: m.date || "",
        updated: new Date().toISOString(),
      }));
      await db.ref("live_scores").set({ matches, updated: new Date().toISOString() });
      console.log(`Saved ${matches.length} matches`);
    } catch(e) { console.error("Score error:", e.message); }
    return null;
  });

// ── News Fetcher (every 15 min) ──
exports.fetchNews = functions.region("asia-south1")
  .pubsub.schedule("every 15 minutes").onRun(async () => {
    try {
      let articles = [];
      if (NEWSAPI_KEY) {
        const res = await axios.get(
          `https://newsapi.org/v2/everything?q=cricket+IPL&language=en&sortBy=publishedAt&pageSize=10&apiKey=${NEWSAPI_KEY}`,
          { timeout: 8000 }
        );
        articles = (res.data.articles || [])
          .filter(a => a.title && !a.title.includes("[Removed]"))
          .map((a, i) => ({
            id: `na_${i}`, title: a.title,
            url: a.url || "", source: a.source?.name || "",
            time: a.publishedAt?.substr(0,10) || "",
            icon: "🏏", tag: tagNews(a.title),
          }));
      }
      if (!articles.length) {
        const res = await axios.get(
          "https://www.cricbuzz.com/rss-feeds/latest-cricket-news",
          { headers: { "User-Agent": "CricNow/1.0" }, timeout: 8000 }
        );
        const items = res.data.match(/<item>([\s\S]*?)<\/item>/g) || [];
        articles = items.slice(0,10).map((item, i) => {
          const title = (item.match(/<title><!\[CDATA\[(.*?)\]\]>/) ||
                         item.match(/<title>(.*?)<\/title>/) || [])[1] || "";
          const link = (item.match(/<link>(.*?)<\/link>/) || [])[1] || "";
          return { id:`cb_${i}`, title:title.trim(), url:link.trim(),
                   source:"Cricbuzz", time:new Date().toISOString().substr(0,10),
                   icon:"🏏", tag:tagNews(title) };
        }).filter(a => a.title);
      }
      if (articles.length) {
        await db.ref("news").set({ articles, updated: new Date().toISOString() });
        console.log(`Saved ${articles.length} articles`);
      }
    } catch(e) { console.error("News error:", e.message); }
    return null;
  });

// ── Send Notification (callable) ──
exports.sendNotif = functions.region("asia-south1")
  .https.onCall(async (data, context) => {
    if (!context.auth) throw new functions.https.HttpsError("unauthenticated","Login required");
    const { title, body, topic } = data;
    await admin.messaging().send({ notification: {title, body}, topic: topic || "all" });
    return { success: true };
  });

// ── Update Match Score (callable) ──
exports.updateMatch = functions.region("asia-south1")
  .https.onCall(async (data, context) => {
    if (!context.auth) throw new functions.https.HttpsError("unauthenticated","Login required");
    const { matchId, updates } = data;
    await firestore.collection("matches").doc(matchId)
      .set({ ...updates, updated: new Date().toISOString() }, { merge: true });
    return { success: true };
  });

// ── HELPERS ──
const FLAGS = {
  india:"🇮🇳", australia:"🇦🇺", england:"🏴󠁧󠁢󠁥󠁮󠁧󠁿", pakistan:"🇵🇰",
  "south africa":"🇿🇦", "new zealand":"🇳🇿", "west indies":"🇯🇲",
  "sri lanka":"🇱🇰", bangladesh:"🇧🇩", afghanistan:"🇦🇫",
};
function getFlag(team) {
  const t = team.toLowerCase();
  for (const [k,v] of Object.entries(FLAGS)) if (t.includes(k)) return v;
  return "🏏";
}
function classifyMatch(series, type) {
  const s = series.toUpperCase();
  if (s.includes("IPL") || s.includes("WPL")) return "ipl";
  if (s.includes("WOMEN")) return "women";
  if (["RANJI","SHEFFIELD","CSA"].some(w => s.includes(w))) return "domestic";
  return "intl";
}
function tagNews(title) {
  const t = (title||"").toLowerCase();
  if (["live","score","update"].some(w=>t.includes(w))) return "LIVE";
  if (["won","beat","result"].some(w=>t.includes(w))) return "MATCH REPORT";
  if (["preview","vs"].some(w=>t.includes(w))) return "PREVIEW";
  return "TRENDING";
}
