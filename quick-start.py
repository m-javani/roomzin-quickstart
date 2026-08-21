#!/usr/bin/env python3
"""
Roomzin Quick-Start Generator

Usage:
  python3 quick-start.py --shards 2 --zones 2
  python3 quick-start.py --level full --ha --rzproxy
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from string import Template


# ---------- Topology Generation ----------

def generate_topology(shards, zones, ha=False):
    """Generate component allocation across zones"""
    
    bridge_count = 2 if ha else 1
    zone_router_count = 2 if ha else 1
    
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
        
        # Bridges per shard (1 or 2 based on HA)
        for b in range(bridge_count):
            bridge_id = f"bridge-{i}-{b}" if ha else f"bridge-{i}"
            topology["bridges"].append({
                "id": bridge_id,
                "shard_id": shard_id,
                "zone_id": zone_id,
                "shard_index": i,
                "bridge_index": b,
            })
        
        topology["shards"].append({
            "id": shard_id,
            "zone_id": zone_id,
            "nodes": node_ids,
            "bridges": [b for b in topology["bridges"] if b["shard_id"] == shard_id],
            "shard_index": i,
        })
    
    # Zone routers per zone (1 or 2 based on HA)
    for z in range(zones):
        zone_id = f"zone{z+1}"
        zone_bridge_ids = [b["id"] for b in topology["bridges"] if b["zone_id"] == zone_id]
        for r in range(zone_router_count):
          router_id = f"router-zone-{z}-{r}" if ha else f"router-zone-{z}"
          topology["zone_routers"].append({
              "id": router_id,
              "zone_id": zone_id,
              "zone_index": z,
              "router_index": r,
              "bridge_ids": zone_bridge_ids,  # Store bridge dependencies
          })
        topology["zones"].append({
            "id": zone_id,
            "routers": [r for r in topology["zone_routers"] if r["zone_id"] == zone_id],
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

def get_ports(component_type, shard_index=0, node_index=0, zone_index=0, edge_index=0, bridge_index=0, router_index=0):
    """Get external ports for each component"""
    
    if component_type == "roomzin_tcp":
        return f"78{shard_index}{node_index}"
    elif component_type == "roomzin_api":
        return f"80{shard_index}{node_index}"
    elif component_type == "bridge":
        # bridge-0:9000, bridge-1:9001
        # HA: bridge-0-0:9000, bridge-0-1:9001, bridge-1-0:9002, bridge-1-1:9003
        return str(9000 + (shard_index * 2) + bridge_index)
    elif component_type == "zone_router":
        # router-zone-0:9100, router-zone-1:9101
        # HA: router-zone-0-0:9100, router-zone-0-1:9101
        return str(9100 + (zone_index * 2) + router_index)
    elif component_type == "edge_router":
        return "9200"
    else:
        return ""

# ---------- IP Allocation ----------

def get_ip(component_type, index):
    """Get IP address for each component"""
    base_ips = {
        "roomzin": 10,
        "rzpoint": 40,
        "rzid": 41,
        "bridge": 45,
        "zone_router": 50,
        "edge_router": 60,
        "rzproxy": 70,
    }
    return f"172.20.0.{base_ips[component_type] + index}"


def build_resolver_mapping(topology):
    """Build ID:IP mapping string for RzPoint - everything in topology"""
    parts = []
    
    for node in topology["nodes"]:
        ip = get_ip("roomzin", node["shard_index"] * 3 + node["node_index"])
        parts.append(f"{node['id']}:{ip}")
    
    for bridge in topology["bridges"]:
        ip = get_ip("bridge", bridge["shard_index"])
        parts.append(f"{bridge['id']}:{ip}")
    
    for router in topology["zone_routers"]:
        ip = get_ip("zone_router", router["zone_index"])
        parts.append(f"{router['id']}:{ip}")
    
    if topology["edge_router"]:
        parts.append(f"{topology['edge_router']['id']}:172.20.0.60")
    
    return ",".join(parts)


# ---------- Level Configuration ----------

def get_level_config(level):
    """Return which components to include based on level"""
    return {
        "bridge": level in ["bridge", "zone", "edge", "full"],
        "zone_router": level in ["zone", "edge", "full"],
        "edge_router": level in ["edge", "full"],
        "rzproxy": level == "full",
    }


# ---------- Docker Compose Rendering ----------

def render_docker_compose(topology, args):
    """Render docker-compose.yml from template"""
    
    level_config = get_level_config(args.level)
    services = []
    
    # ---------- Roomzin nodes (always) ----------
    for node in topology["nodes"]:
        tcp_port = get_ports("roomzin_tcp", node["shard_index"], node["node_index"])
        api_port = get_ports("roomzin_api", node["shard_index"], node["node_index"])
        ip = get_ip("roomzin", node["shard_index"] * 3 + node["node_index"])
        
        shard_nodes = [n["id"] for n in topology["nodes"] if n["shard_id"] == node["shard_id"]]
        voters = ",".join(shard_nodes)
        
        service = Template("""
  ${node_id}:
    image: roomzin:local
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
    
    # ---------- Bridges ----------
    if level_config["bridge"]:
        for bridge in topology["bridges"]:
            port = get_ports("bridge", bridge["shard_index"], bridge_index=bridge.get("bridge_index", 0))
            ip = get_ip("bridge", bridge["shard_index"])
            
            shard_nodes = [n["id"] for n in topology["nodes"] if n["shard_id"] == bridge["shard_id"]]
            depends = "\n".join([f"      - {n}" for n in shard_nodes])
            
            service = Template("""
  ${bridge_id}:
    image: rzbridge:local
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
    
    # ---------- Zone Routers ----------
    if level_config["zone_router"]:
      for router in topology["zone_routers"]:
          port = get_ports("zone_router", zone_index=router["zone_index"], router_index=router.get("router_index", 0))
          ip = get_ip("zone_router", router["zone_index"])
          
          # Depends on bridges in this zone (use stored bridge_ids)
          bridge_ids = router.get("bridge_ids", [])
          depends_items = ["      - rzid", "        - rzpoint"]
          for b in bridge_ids:
              depends_items.append(f"        - {b}")
          depends_str = "\n".join(depends_items)
          
          service = Template("""
  ${router_id}:
      image: rzrouter:local
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
  ${depends}
  """).substitute(
              router_id=router["id"],
              zone_id=router["zone_id"],
              ip=ip,
              port=port,
              depends=depends_str,
          )
          services.append(service)

    # ---------- Edge Router ----------
    if level_config["edge_router"]:
        edge_router = topology["edge_router"]
        port = get_ports("edge_router")
        ip = get_ip("edge_router", 0)
        
        if level_config["zone_router"]:
            depends = "\n".join([f"      - {r['id']}" for r in topology["zone_routers"]])
        else:
            depends = "      - rzid"
        
        service = Template("""
  ${router_id}:
    image: rzrouter:local
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
)
        services.append(service)
    
    # ---------- RzPoint (always) ----------
    mapping_str = build_resolver_mapping(topology)
    
    services.append(Template("""
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
    command: python3 -u /opt/rzpoint/rzpoint-echo.py
    environment:
      - RZPOINT_PORT=9090
      - RZPOINT_MAPPING=${mapping}
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
""").substitute(mapping=mapping_str))
    
    # ---------- RzID (always) ----------
    services.append("""
  rzid:
    image: rzid:local
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
    
    # ---------- RZProxy ----------
    if level_config["rzproxy"] and level_config["edge_router"]:
        services.append("""
  rzproxy:
    image: rzproxy:local
    container_name: rzproxy
    hostname: rzproxy
    networks:
      roomzin-net:
        ipv4_address: 172.20.0.70
    ports:
      - "8777:8777"
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=10M
    command: >
      /opt/rzproxy/rzproxy
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
    elif level_config["rzproxy"] and not level_config["edge_router"]:
        print("⚠️  Warning: RZProxy requires edge-router. Ignoring --rzproxy")
    
    # Combine all services
    all_services = "".join(services)
    
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
    parser.add_argument("--level", type=str, default="cluster", 
                        choices=["cluster", "bridge", "zone", "edge", "full"],
                        help="Top level: cluster|bridge|zone|edge|full (default: cluster)")
    parser.add_argument("--ha", action="store_true", help="Enable HA mode (2 instances per layer)")
    parser.add_argument("--rzproxy", action="store_true", help="Include RZProxy (requires level=full)")
    parser.add_argument("--output", type=str, default="./generated", help="Output directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()
    
    # Validate
    if args.shards < 1:
        print("❌ Error: --shards must be >= 1")
        sys.exit(1)
    if args.zones < 1:
        print("❌ Error: --zones must be >= 1")
        sys.exit(1)
    if args.rzproxy and args.level != "full":
        print("⚠️  Warning: RZProxy requires level=full. Ignoring --rzproxy")
        args.rzproxy = False
    
    # Check output directory
    output_dir = Path(args.output)
    if output_dir.exists() and not args.force:
        print(f"❌ Error: Output directory '{output_dir}' exists. Use --force to overwrite.")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    level_names = {
        "cluster": "Cluster (nodes + RzID + RzPoint)",
        "bridge": "Bridge (cluster + bridges)",
        "zone": "Zone (bridge + zone routers)",
        "edge": "Edge (zone + edge router)",
        "full": "Full (edge + RZProxy)",
    }
    
    print(f"🚀 Generating Roomzin test environment...")
    print(f"   Shards: {args.shards}")
    print(f"   Zones: {args.zones}")
    print(f"   Level: {args.level} ({level_names[args.level]})")
    print(f"   HA: {'Enabled' if args.ha else 'Disabled'}")
    print(f"   RZProxy: {'Enabled' if args.rzproxy else 'Disabled'}")
    print(f"   Output: {output_dir}")
    print()
    
    # Generate topology
    topology = generate_topology(args.shards, args.zones, args.ha)
    
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
    compose = render_docker_compose(topology, args)
    (output_dir / "docker-compose.yml").write_text(compose)
    
    level_config = get_level_config(args.level)
    
    print()
    print("✅ Generation complete!")
    print()
    print(f"   cd {output_dir}")
    print(f"   docker compose up -d")
    print()
    print("   Service endpoints:")
    print("   - RzID:    http://localhost:8081")
    print("   - RzPoint: http://localhost:9090")
    
    if level_config["bridge"]:
        for bridge in topology["bridges"]:
            port = get_ports("bridge", bridge["shard_index"], bridge_index=bridge.get("bridge_index", 0))
            print(f"   - {bridge['id']} (TCP): localhost:{port}")
    
    if level_config["zone_router"]:
        for router in topology["zone_routers"]:
            port = get_ports("zone_router", zone_index=router["zone_index"], router_index=router.get("router_index", 0))
            print(f"   - {router['id']} (TCP): localhost:{port}")
    
    if level_config["edge_router"]:
        print("   - router-edge (TCP): localhost:9200")
    
    if level_config["rzproxy"] and level_config["edge_router"]:
        print("   - RZProxy:  http://localhost:8777")
    
    print()
    print(f"   Roomzin nodes ({args.shards} shards × 3 nodes):")
    for node in topology["nodes"]:
        tcp_port = get_ports("roomzin_tcp", node["shard_index"], node["node_index"])
        api_port = get_ports("roomzin_api", node["shard_index"], node["node_index"])
        print(f"   - {node['id']} (TCP: {tcp_port}, API: {api_port})")
    
    if level_config["rzproxy"] and level_config["edge_router"]:
        print()
        print("   Test with:")
        print('   curl -X POST http://localhost:8777/api -H "Content-Type: application/json" -d \'{"command":"GETSEGMENTS","segment":"","body":{}}\'')
    else:
        print()
        print("   For testing, connect your local service to the running cluster.")
        print("   Example: RzBridge connects to RzID at localhost:8081 and RzPoint at localhost:9090")


if __name__ == "__main__":
    main()