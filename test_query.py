#!/usr/bin/env python3
"""
Test queries for Roomzin quick-start

Usage:
  python3 test_query.py
  python3 test_query.py --host localhost --port 8777
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta

def send_query(host, port, command, segment, body):
    """Send a query to RZGate and return the response"""
    
    url = f"http://{host}:{port}/api"
    
    payload = {
        "command": command,
        "segment": segment,
        "body": body
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Test queries for Roomzin")
    parser.add_argument("--host", default="localhost", help="RZGate host (default: localhost)")
    parser.add_argument("--port", type=int, default=8777, help="RZGate port (default: 8777)")
    args = parser.parse_args()
    
    # Get today's date and tomorrow
    today = datetime.now().date()
    date1 = today.strftime("%Y-%m-%d")
    date2 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"🧪 Testing RZGate at {args.host}:{args.port}")
    print()
    
    # Test 1: SEARCHPROP on segment_1
    print("📋 Test 1: SEARCHPROP on segment_1")
    print("   Request:")
    print(f'    {{"command":"SEARCHPROP","segment":"segment_1","body":{{"limit":1}}}}')
    
    result = send_query(args.host, args.port, "SEARCHPROP", "segment_1", {"limit": 1})
    
    if result.get("status") == "success":
        properties = result.get("properties", [])
        print(f"   ✅ Success: found {len(properties)} properties")
        if properties:
            print(f"   First property: {properties[0]}")
    else:
        print(f"   ❌ Error: {result.get('message', 'unknown error')}")
    print()
    
    # Test 2: SEARCHAVAIL on segment_1
    print("📋 Test 2: SEARCHAVAIL on segment_1")
    print(f"   Request:")
    print(f'    {{"command":"SEARCHAVAIL","segment":"segment_1","body":{{"room_type":"room1","type":"hotel","date":["{date1}","{date2}"],"limit":1}}}}')
    
    result = send_query(
        args.host, args.port,
        "SEARCHAVAIL",
        "segment_1",
        {
            "room_type": "room1",
            "type": "hotel",
            "date": [date1, date2],
            "limit": 1
        }
    )
    
    if result.get("status") == "success":
        properties = result.get("properties", [])
        print(f"   ✅ Success: found {len(properties)} properties with availability")
        if properties:
            prop = properties[0]
            print(f"   Property: {prop.get('property_id')}")
            days = prop.get("days", [])
            for day in days:
                print(f"     {day.get('date')}: avail={day.get('availability')}, price={day.get('final_price')}")
    else:
        print(f"   ❌ Error: {result.get('message', 'unknown error')}")
    print()
    
    # Test 3: SEARCHAVAIL on segment_5 (should route to shard2)
    print("📋 Test 3: SEARCHAVAIL on segment_5 (routes to shard2)")
    print(f"   Request:")
    print(f'    {{"command":"SEARCHAVAIL","segment":"segment_5","body":{{"room_type":"room1","type":"hotel","date":["{date1}","{date2}"],"limit":1}}}}')
    
    result = send_query(
        args.host, args.port,
        "SEARCHAVAIL",
        "segment_5",
        {
            "room_type": "room1",
            "type": "hotel",
            "date": [date1, date2],
            "limit": 1
        }
    )
    
    if result.get("status") == "success":
        properties = result.get("properties", [])
        print(f"   ✅ Success: found {len(properties)} properties with availability")
        if properties:
            prop = properties[0]
            print(f"   Property: {prop.get('property_id')}")
            days = prop.get("days", [])
            for day in days:
                print(f"     {day.get('date')}: avail={day.get('availability')}, price={day.get('final_price')}")
    else:
        print(f"   ❌ Error: {result.get('message', 'unknown error')}")
    print()
    
    # Summary
    print("✅ Test queries completed")

if __name__ == "__main__":
    main()