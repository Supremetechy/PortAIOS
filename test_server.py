#!/usr/bin/env python3
"""
Simple test server for Avatar Creator Pro
"""
import http.server
import socketserver
import os

PORT = 8000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Fix MIME types for ES modules
        if self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript')
        super().end_headers()

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Test server running at http://localhost:{PORT}/")
    print(f"Open: http://localhost:{PORT}/test_avatar_pro.html")
    print("Note: This is a simple file server - eel features won't work")
    print("For full features, use: python run_onboarding.py")
    httpd.serve_forever()
