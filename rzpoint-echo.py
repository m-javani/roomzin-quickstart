#!/usr/bin/env python3
"""
RzPoint - Simple Resolver for Roomzin Quick-Start

Returns IP from mapping for any ID.
If ID not found, returns the ID itself (fallback).
"""

import argparse
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler


class ResolverHandler(BaseHTTPRequestHandler):
    resolver_map = {}

    def do_GET(self):
        parts = self.path.strip('/').split('/')

        if 'nodes' in parts:
            idx = parts.index('nodes')
            node_id = parts[idx + 1] if idx + 1 < len(parts) else ''
        else:
            node_id = parts[-1] if parts[-1] else ''

        ip = self.server.resolver_map.get(node_id, node_id)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(ip.encode('utf-8'))

    def do_POST(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def parse_mapping(mapping_str):
    """Parse 'id1:ip1,id2:ip2' into dict"""
    result = {}
    if mapping_str:
        for pair in mapping_str.split(','):
            if ':' in pair:
                key, val = pair.split(':', 1)
                result[key.strip()] = val.strip()
    return result


def main():
    parser = argparse.ArgumentParser(description='RzPoint resolver')
    parser.add_argument('--mapping', type=str, default=None, help='Comma-separated id:ip mappings')
    parser.add_argument('--port', type=int, default=int(os.environ.get('RZPOINT_PORT', '9090')))
    args = parser.parse_args()

    # Read from env if not provided via CLI
    mapping_str = args.mapping
    if mapping_str is None:
        mapping_str = os.environ.get('RZPOINT_MAPPING', '')

    resolver_map = parse_mapping(mapping_str)

    print(f"🔄 RzPoint resolver running on 0.0.0.0:{args.port}")
    print(f"   Loaded {len(resolver_map)} mappings")

    # Print first few mappings for visibility
    if resolver_map:
        items = list(resolver_map.items())[:5]
        for key, val in items:
            print(f"     {key} → {val}")
        if len(resolver_map) > 5:
            print(f"     ... and {len(resolver_map) - 5} more")

    server = HTTPServer(('0.0.0.0', args.port), ResolverHandler)
    server.resolver_map = resolver_map

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()