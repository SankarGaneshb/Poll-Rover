import http.server
import json
import socketserver
import os
from pathlib import Path
import yaml
from datetime import datetime

import threading
import time

PORT = 4040
LOG_DIR = Path("ops_logs")
APPROVAL_FILE = Path("data/approvals.yml")
TASK_STATUS = {} # Global task tracker {incident_type: 'processing'|'completed'|'failed'}

class HILHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open("templates/dashboard_ui.html", "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode())
        
        elif self.path == '/api/incidents':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            incidents = self._get_pending_incidents()
            self.wfile.write(json.dumps({"incidents": incidents}).encode())
        
        elif self.path == '/api/tasks':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"tasks": TASK_STATUS}).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/approve':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            
            incident_type = post_data.get("type")
            self._save_approval(incident_type)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())

    def _get_pending_incidents(self):
        """Scan ops_logs for reports containing incidents, filtering out approved ones."""
        all_incidents = []
        approved_types = self._get_approved_types()
        
        if not LOG_DIR.exists():
            return []

        files = sorted(LOG_DIR.glob("sre_report_*.yml"), reverse=True)[:3]
        
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as y:
                    data = yaml.safe_load(y)
                    if data and "incidents" in data:
                        for inc in data["incidents"]:
                            # Filter if already approved or currently being processed
                            if inc["type"] in approved_types or inc["type"] in TASK_STATUS:
                                continue
                                
                            if not any(a["type"] == inc["type"] for a in all_incidents):
                                all_incidents.append(inc)
            except Exception as e:
                print(f"Error reading {f}: {e}")
        
        return all_incidents

    def _get_approved_types(self):
        """Get list of incident types that have been approved in approvals.yml."""
        if not APPROVAL_FILE.exists():
            return []
        try:
            with open(APPROVAL_FILE, "r") as f:
                data = yaml.safe_load(f)
                if data and "approvals" in data:
                    return [a["incident_type"] for a in data["approvals"]]
        except:
            return []
        return []

    def _save_approval(self, incident_type):
        """Append the approval to the data/approvals.yml file."""
        APPROVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        TASK_STATUS[incident_type] = "processing" # Start UI progress
        
        approvals = {"approvals": []}
        if APPROVAL_FILE.exists():
            with open(APPROVAL_FILE, "r") as f:
                data = yaml.safe_load(f)
                if data: approvals = data
        
        approvals["approvals"].append({
            "incident_type": incident_type,
            "timestamp": datetime.now().isoformat(),
            "status": "approved"
        })
        
        with open(APPROVAL_FILE, "w") as f:
            yaml.dump(approvals, f)
        print(f"HIL: Approved {incident_type}. Remediation triggered.")


def background_remediation_processor():
    """Simulates the SRE Agent checking for approvals and running them."""
    while True:
        # For each incident in 'processing' state
        for inc_type in list(TASK_STATUS.keys()):
            if TASK_STATUS[inc_type] == "processing":
                print(f"SRE Agent: Executing remediation for {inc_type}...")
                time.sleep(5) # Simulate work (e.g. running fix_issues)
                TASK_STATUS[inc_type] = "completed"
                print(f"SRE Agent: FIXED {inc_type} successfully.")
        
        time.sleep(2)


print(f"HIL Dashboard Server starting on http://localhost:{PORT}")
# Start Background Processor
threading.Thread(target=background_remediation_processor, daemon=True).start()

with socketserver.TCPServer(("", PORT), HILHandler) as httpd:
    httpd.serve_forever()
