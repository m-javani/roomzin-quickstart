#!/usr/bin/env python3
"""
RzPoint - Simple Echo Resolver for Roomzin Quick-Start

Returns the ID from the URL path as the hostname.
For Docker Compose, container names = hostnames = IDs.

Examples:
  GET /routers/router-zone-0     → "router-zone-0"
  GET /bridges/bridge-0          → "bridge-0"
  GET /shards/shard1/nodes/roomzin-0-0 → "roomzin-0-0"
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import sys
import re
import json

class EchoHandler(BaseHTTPRequestHandler):
    """Handle GET requests by echoing the ID from the path"""
    
    def do_GET(self):
        """Extract ID from path and return it"""
        
        # Parse the path
        # /routers/router-zone-0 → router-zone-0
        # /bridges/bridge-0 → bridge-0
        # /shards/shard1/nodes/roomzin-0-0 → roomzin-0-0
        
        parts = self.path.strip('/').split('/')
        
        if not parts or parts[0] == '':
            # Empty path - return empty string
            node_id = ''
        elif 'nodes' in parts:
            # Path: /shards/{shard}/nodes/{node_id}
            idx = parts.index('nodes')
            node_id = parts[idx + 1] if idx + 1 < len(parts) else ''
        else:
            # Path: /routers/{id} or /bridges/{id}
            node_id = parts[-1] if parts[-1] else ''
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        
        # Echo the ID back
        self.wfile.write(node_id.encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests - for health checks"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Silence HTTP request logs to keep output clean"""
        # Uncomment for debugging:
        # print(f"[RzPoint] {format % args}")
        pass

def main():
    """Start the RzPoint echo server"""
    port = int(os.environ.get('RZPOINT_PORT', '9090'))
    host = os.environ.get('RZPOINT_HOST', '0.0.0.0')
    
    print(f"🔄 RzPoint echo resolver running on {host}:{port}")
    print(f"   Example: GET /routers/router-zone-0 → router-zone-0")
    print(f"   Health:  GET /health → {{'status': 'ok'}}")
    
    server = HTTPServer((host, port), EchoHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down RzPoint...")
        server.shutdown()

if __name__ == "__main__":
    main()