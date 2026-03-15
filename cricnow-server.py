"""
CricNow Mini Server
===================
Serves the app + live data on localhost
Allows HTML to fetch fresh data via /api/live

Run:
  python3 cricnow-server.py
Then open: http://localhost:8080
"""

import http.server
import json
import os
import threading
import time
from pathlib import Path

PORT = 8080
DATA_FILE = "cricnow_live_data.json"

class CricNowHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Live data API endpoint
        if self.path == "/api/live":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                with open(DATA_FILE, "r") as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(json.dumps({"matches":[],"news":[]}).encode())
            return
        
        # Health check
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status":"ok","time":time.time()}).encode())
            return
        
        # Serve static files
        super().do_GET()
    
    def log_message(self, format, *args):
        # Suppress default logs, only show API calls
        if "/api/" in args[0] if args else "":
            print(f"[API] {args[0]}")

def run():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    with http.server.HTTPServer(("", PORT), CricNowHandler) as httpd:
        print(f"╔══════════════════════════════════╗")
        print(f"║  CricNow Server running!         ║")
        print(f"║  Open: http://localhost:{PORT}      ║")
        print(f"║  API:  http://localhost:{PORT}/api/live ║")
        print(f"╚══════════════════════════════════╝")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
