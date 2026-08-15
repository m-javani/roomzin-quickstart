#!/usr/bin/env python3
"""
Roomzin Quick-Start Generator

Usage:
  python3 quick-start.py --shards 2 --zones 2
  python3 quick-start.py --shards 3 --zones 3
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from string import Template

# ---------- Topology Generation ----------

def generate_topology(shards, zones):
    """Generate component allocation across zones"""
    
    if zones > shards:
        print(f"⚠️  Warning: zones ({zones}) > shards ({shards}). Some zones will have no shards.")
    
    topology = {
        "zones": [],
        "shards": [],
        "nodes": [],
        "bridges": [],
        "zone_routers": [],
        "edge_router": None,
    }
    
    # Distribute shards across zones (round-robin)
    for i in range(shards):
        zone_index = i % zones
        shard_id = f"shard{i+1}"
        zone_id = f"zone{zone_index+1}"
        
        # 3 nodes per shard
        node_ids = []
        for j in range(3):
            node_id = f"roomzin-{i}-{j}"
            node_ids.append(node_id)
            topology["nodes"].append({
                "id": node_id,
                "shard_id": shard_id,
                "zone_id": zone_id,
                "node_index": j,
                "shard_index": i,
                "role": "leader" if j == 0 else "follower"
            })
        
        # 1 bridge per shard
        bridge_id = f"bridge-{i}"
        topology["bridges"].append({
            "id": bridge_id,
            "shard_id": shard_id,
            "zone_id": zone_id,
            "shard_index": i,
        })
        
        topology["shards"].append({
            "id": shard_id,
            "zone_id": zone_id,
            "nodes": node_ids,
            "bridge": bridge_id,
            "shard_index": i,
        })
    
    # 1 zone router per zone
    for z in range(zones):
        zone_id = f"zone{z+1}"
        router_id = f"router-zone-{z}"
        topology["zone_routers"].append({
            "id": router_id,
            "zone_id": zone_id,
            "zone_index": z,
        })
        topology["zones"].append({
            "id": zone_id,
            "router": router_id,
            "shards": [s["id"] for s in topology["shards"] if s["zone_id"] == zone_id],
            "zone_index": z,
        })
    
    # Single edge router (always 1)
    topology["edge_router"] = {
        "id": "router-edge",
        "edge_index": 0,
    }
    
    return topology


# ---------- Port Allocation ----------

def get_ports(component_type, shard_index=0, node_index=0, zone_index=0, edge_index=0):
    """Get external ports for each component"""
    
    if component_type == "roomzin_tcp":
        return f"78{shard_index}{node_index}"  # 7800, 7801, 7802, 7810, ...
    elif component_type == "roomzin_api":
        return f"80{shard_index}{node_index}"  # 8000, 8001, 8002, 8010, ...
    elif component_type == "bridge":
        return f"90{shard_index:02d}"  # 9000, 9001, 9002, ...
    elif component_type == "zone_router":
        return f"91{zone_index:02d}"  # 9100, 9101, 9102, ...
    elif component_type == "edge_router":
        return "9200"  # Always 9200 for single edge router
    else:
        return ""


# ---------- IP Allocation ----------

def get_ip(component_type, index):
    """Get IP address for each component"""
    base_ips = {
        "roomzin": 10,      # 10 + (shard_index * 3 + node_index)
        "rzpoint": 40,
        "rzid": 41,
        "bridge": 45,       # 45 + shard_index
        "zone_router": 50,  # 50 + zone_index
        "edge_router": 60,  # Always 60 for single edge router
        "rzgate": 70,
    }
    return f"172.20.0.{base_ips[component_type] + index}"


# ---------- Docker Compose Rendering ----------

def render_docker_compose(topology):
    """Render docker-compose.yml from template"""
    
    # Build service definitions
    services = []
    
    # Roomzin nodes
    for node in topology["nodes"]:
        tcp_port = get_ports("roomzin_tcp", node["shard_index"], node["node_index"])
        api_port = get_ports("roomzin_api", node["shard_index"], node["node_index"])
        ip = get_ip("roomzin", node["shard_index"] * 3 + node["node_index"])
        
        # Initial voters: all 3 node IDs for this shard
        shard_nodes = [n["id"] for n in topology["nodes"] if n["shard_id"] == node["shard_id"]]
        voters = ",".join(shard_nodes)
        
        service = Template("""
  ${node_id}:
    image: mehdyjavany/roomzin:latest
    container_name: ${node_id}
    hostname: ${node_id}
    networks:
      roomzin-net:
        ipv4_address: ${ip}
    ports:
      - "${tcp_port}:7777"
      - "${api_port}:8080"
    volumes:
      - ./data/${node_id}:/opt/roomzin/data
      - ./certs:/opt/roomzin/certs:ro
      - ./configs:/opt/roomzin/configs:ro
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100M
    cap_add:
      - NET_ADMIN
    command: >
      /opt/roomzin/roomzin run-clustered
        --config /opt/roomzin/configs/roomzin.yml
        --node-id ${node_id}
        --shard-id ${shard_id}
        --zone-id ${zone_id}
        --initial-voters ${voters}
        --cert-path /opt/roomzin/certs/cert.pem
        --key-path /opt/roomzin/certs/key.pem
        --ca-cert-path /opt/roomzin/certs/ca.pem
        --rzid-addr rzid:8080
        --rzpoint-addr rzpoint:9090
        --tcp-listen-addr 0.0.0.0
        --api-listen-addr 0.0.0.0
        --quic-listen-addr 0.0.0.0
        --data-dir /opt/roomzin/data
    depends_on:
      - rzid
      - rzpoint
""").substitute(
            node_id=node["id"],
            shard_id=node["shard_id"],
            zone_id=node["zone_id"],
            ip=ip,
            tcp_port=tcp_port,
            api_port=api_port,
            voters=voters,
        )
        services.append(service)
    
    # Bridges
    for bridge in topology["bridges"]:
        port = get_ports("bridge", bridge["shard_index"])
        ip = get_ip("bridge", bridge["shard_index"])
        
        # Depends on the 3 nodes in this shard
        shard_nodes = [n["id"] for n in topology["nodes"] if n["shard_id"] == bridge["shard_id"]]
        depends = "\n".join([f"      - {n}" for n in shard_nodes])
        
        service = Template("""
  ${bridge_id}:
    image: mehdyjavany/rzbridge:latest
    container_name: ${bridge_id}
    hostname: ${bridge_id}
    networks:
      roomzin-net:
        ipv4_address: ${ip}
    ports:
      - "${port}:9000"
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
    command: >
      /opt/rzbridge/rzbridge
        --zone-id ${zone_id}
        --shard-id ${shard_id}
        --bridge-id ${bridge_id}
        --rzid-addr rzid:8080
        --rzpoint-addr rzpoint:9090
        --listen-host 0.0.0.0
        --listen-port 9000
        --roomzin-api-port 8080
        --roomzin-tcp-port 7777
    depends_on:
      - rzid
      - rzpoint
${depends}
""").substitute(
            bridge_id=bridge["id"],
            shard_id=bridge["shard_id"],
            zone_id=bridge["zone_id"],
            ip=ip,
            port=port,
            depends=depends,
        )
        services.append(service)
    
    # Zone Routers
    for router in topology["zone_routers"]:
        port = get_ports("zone_router", zone_index=router["zone_index"])
        ip = get_ip("zone_router", router["zone_index"])
        
        # Depends on bridges in this zone
        zone_bridges = [b["id"] for b in topology["bridges"] if b["zone_id"] == router["zone_id"]]
        depends = "\n".join([f"      - {b}" for b in zone_bridges]) if zone_bridges else "      - rzid"
        
        service = Template("""
  ${router_id}:
    image: mehdyjavany/rzrouter:latest
    container_name: ${router_id}
    hostname: ${router_id}
    networks:
      roomzin-net:
        ipv4_address: ${ip}
    ports:
      - "${port}:9000"
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
    command: >
      /opt/rzrouter/rzrouter
        --mode zone
        --zone-id ${zone_id}
        --router-id ${router_id}
        --rzid-addr rzid:8080
        --rzpoint-addr rzpoint:9090
        --listen-host 0.0.0.0
        --tcp-port 9000
        --hop-tcp-port 9000
    depends_on:
      - rzid
      - rzpoint
${depends}
""").substitute(
            router_id=router["id"],
            zone_id=router["zone_id"],
            ip=ip,
            port=port,
            depends=depends,
        )
        services.append(service)
    
    # Edge Router (single instance)
    edge_router = topology["edge_router"]
    port = get_ports("edge_router")
    ip = get_ip("edge_router", 0)
    
    # Depends on all zone routers
    depends = "\n".join([f"      - {r['id']}" for r in topology["zone_routers"]])
    
    services.append(Template("""
  ${router_id}:
    image: mehdyjavany/rzrouter:latest
    container_name: ${router_id}
    hostname: ${router_id}
    networks:
      roomzin-net:
        ipv4_address: ${ip}
    ports:
      - "${port}:9000"
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
    command: >
      /opt/rzrouter/rzrouter
        --mode edge
        --rzid-addr rzid:8080
        --rzpoint-addr rzpoint:9090
        --listen-host 0.0.0.0
        --tcp-port 9000
        --hop-tcp-port 9000
    depends_on:
      - rzid
      - rzpoint
${depends}
""").substitute(
    router_id=edge_router["id"],
    ip=ip,
    port=port,
    depends=depends,
))
    
    # RzPoint (Python echo server)
    services.append("""
  rzpoint:
    image: python:3.11-slim
    container_name: rzpoint
    hostname: rzpoint
    networks:
      roomzin-net:
        ipv4_address: 172.20.0.40
    ports:
      - "9090:9090"
    working_dir: /opt/rzpoint
    volumes:
      - ./rzpoint-echo.py:/opt/rzpoint/rzpoint-echo.py:ro
    command: python3 /opt/rzpoint/rzpoint-echo.py
    environment:
      - RZPOINT_PORT=9090
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
""")
    
    # RzID
    services.append("""
  rzid:
    image: mehdyjavany/rzid:latest
    container_name: rzid
    hostname: rzid
    networks:
      roomzin-net:
        ipv4_address: 172.20.0.41
    ports:
      - "8081:8080"
    volumes:
      - ./configs/codecs.yml:/opt/rzid/codecs.yml:ro
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
    command: >
      /opt/rzid/rzid
        --addr 0.0.0.0
        --port 8080
        --codecs-path /opt/rzid/codecs.yml
    depends_on:
      - rzpoint
""")
    
    # RZGate
    services.append("""
  rzgate:
    image: mehdyjavany/rzgate:latest
    container_name: rzgate
    hostname: rzgate
    networks:
      roomzin-net:
        ipv4_address: 172.20.0.70
    ports:
      - "8777:8777"
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
    command: >
      /opt/rzgate/rzgate
        --mode router
        --roomzin-addr router-edge
        --roomzin-port 9000
        --listening-addr 0.0.0.0
        --http-port 8777
        --timeout-sec 2
        --keep-alive-sec 30
        --conn-per-node 10
        --max-active-conns 10000
    depends_on:
      - router-edge
""")

    # Combine all services
    all_services = "".join(services)
    
    # Build complete compose file
    compose = Template("""services:${services}

networks:
  roomzin-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
""").substitute(services=all_services)
    
    return compose


# ---------- Main Script ----------

def main():
    parser = argparse.ArgumentParser(description="Roomzin Quick-Start Generator")
    parser.add_argument("--shards", type=int, default=2, help="Number of shards (default: 2)")
    parser.add_argument("--zones", type=int, default=2, help="Number of zones (default: 2)")
    parser.add_argument("--output", type=str, default="./generated", help="Output directory (default: ./generated)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output directory")
    args = parser.parse_args()
    
    # Validate
    if args.shards < 1:
        print("❌ Error: --shards must be >= 1")
        sys.exit(1)
    if args.zones < 1:
        print("❌ Error: --zones must be >= 1")
        sys.exit(1)
    
    # Check output directory
    output_dir = Path(args.output)
    if output_dir.exists() and not args.force:
        print(f"❌ Error: Output directory '{output_dir}' exists. Use --force to overwrite.")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Generating Roomzin test environment...")
    print(f"   Shards: {args.shards}")
    print(f"   Zones: {args.zones}")
    print(f"   Output: {output_dir}")
    print()
    
    # Generate topology
    topology = generate_topology(args.shards, args.zones)
    
    # Copy static files
    print("📁 Copying static files...")
    shutil.copytree("./certs", output_dir / "certs", dirs_exist_ok=True)
    shutil.copytree("./configs", output_dir / "configs", dirs_exist_ok=True)
    shutil.copy("./rzpoint-echo.py", output_dir / "rzpoint-echo.py")
    
    # Create data directories for each node
    print("📁 Creating data directories...")
    for node in topology["nodes"]:
        (output_dir / "data" / node["id"]).mkdir(parents=True, exist_ok=True)
    
    # Generate docker-compose.yml
    print("📝 Generating docker-compose.yml...")
    compose = render_docker_compose(topology)
    (output_dir / "docker-compose.yml").write_text(compose)
    
    print()
    print("✅ Generation complete!")
    print()
    print(f"   cd {output_dir}")
    print(f"   docker compose up -d")
    print()
    print("   Service endpoints:")
    print("   - RZGate:  http://localhost:8777")
    print("   - RzID:    http://localhost:8081")
    print("   - RzPoint: http://localhost:9090")
    print("   - Edge Router (TCP): localhost:9200")
    print()
    print(f"   Roomzin nodes ({args.shards} shards × 3 nodes):")
    for node in topology["nodes"]:
        tcp_port = get_ports("roomzin_tcp", node["shard_index"], node["node_index"])
        api_port = get_ports("roomzin_api", node["shard_index"], node["node_index"])
        print(f"   - {node['id']} (TCP: {tcp_port}, API: {api_port})")
    print()


if __name__ == "__main__":
    main()