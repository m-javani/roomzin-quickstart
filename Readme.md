# Roomzin Quickstart

> **⚠️ IMPORTANT: Development & Testing Only**
> 
> This Docker Compose setup is intended **solely for local development, testing, and quick evaluation** of the Roomzin ecosystem.
> 
> For **production deployments**, Roomzin should be deployed on **bare metal or VMs** for:
> - Maximum performance (no container overhead)
> - Better network throughput
> - Lower latency (no Docker networking layer)
> - More predictable resource allocation
> - Easier debugging and profiling
> 
> **Do not use this setup in production.**

A 3-node Roomzin cluster with optional monitoring (Prometheus + Grafana) and RzGate HTTP/JSON proxy for local testing and development.

## Prerequisites

- Docker and Docker Compose installed
- Make (optional, for convenience)

## Quick Start

```bash
# Pull images from Docker Hub and start the cluster
make start

# Check cluster health
make test

# View logs
make logs

# Stop the cluster
make stop
```

## Docker Images

This quickstart pulls pre-built images from Docker Hub:

- [`mehdyjavany/roomzin:latest`](https://hub.docker.com/r/mehdyjavany/roomzin) - Roomzin node
- [`mehdyjavany/rzgate:latest`](https://hub.docker.com/r/mehdyjavany/rzgate) - RzGate HTTP/JSON proxy

Images are automatically pulled when you run `make start` or `docker compose up`. To update to the latest version:

```bash
docker pull mehdyjavany/roomzin:latest
docker pull mehdyjavany/rzgate:latest
make stop && make start
```

## Directory Structure

```
roomzin-cluster/
├── rzgate/
│   ├── rzgate.yml             # RzGate config
│   └── auth.yml               # RzGate auth tokens
├── dashboard.html             # Standalone HTML dashboard
├── docker-compose.yml         # 3 nodes + RzGate + Prometheus + Grafana
├── Makefile                   # Automation targets
├── configs/
│   ├── roomzin.yml           # Main config
│   ├── auth.yml              # Authentication tokens
│   ├── codecs.yml            # Rate features
│   └── discovery.yml         # Static discovery config
├── certs/
│   ├── roomzin-0/            # Node 0 TLS certs
│   ├── roomzin-1/            # Node 1 TLS certs
│   ├── roomzin-2/            # Node 2 TLS certs
│   └── rzgate/               # RzGate TLS certs (optional)
├── data/
│   ├── roomzin-0/            # Node 0 data (snapshots, WAL)
│   ├── roomzin-1/            # Node 1 data
│   └── roomzin-2/            # Node 2 data
├── dashboards/
│   ├── dashboard.json        # Grafana dashboard
│   └── dashboard.yml         # Grafana dashboard provisioning
├── datasources/
│   └── datasource.yml        # Grafana datasource config
├── prometheus.yml            # Prometheus scrape config
└── token.txt                 # Prometheus bearer token
```

## Make Commands

| Command | Description |
|---------|-------------|
| `make start` | Pull images, start full stack (cluster + RzGate + monitoring) |
| `make start-minimal` | Start Roomzin nodes only (no RzGate, no monitoring) |
| `make start-monitoring` | Start Prometheus + Grafana only |
| `make stop` | Stop everything and clean up data |
| `make test` | Check cluster and RzGate health |
| `make logs` | View all container logs |
| `make help` | Show available commands |

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Roomzin Node 0 | TCP: `localhost:7877`, API: `localhost:7880` | Token: `abc123` |
| Roomzin Node 1 | TCP: `localhost:7977`, API: `localhost:7980` | Token: `abc123` |
| Roomzin Node 2 | TCP: `localhost:8077`, API: `localhost:8080` | Token: `abc123` |
| RzGate HTTP | `http://localhost:8777/api` | Token: `rzgate123` |
| RzGate HTTPS | `https://localhost:3443/api` | Token: `rzgate123` |
| Prometheus | `http://localhost:9090` | - |
| Grafana | `http://localhost:3000` | `admin/admin` |

## Monitoring Options

### Option 1: HTML Dashboard (Lightweight)

For a quick visual overview without Grafana:

```bash
make start-minimal   # Start only Roomzin nodes
# Then open dashboard.html in your browser
```

The HTML dashboard provides:
- Node status (Leader/Follower/Offline)
- TCP connections and commands
- Cluster traffic overview
- WAL and snapshot metrics
- Auto-refreshes every 30 seconds

### Option 2: Grafana (Full Monitoring)

For detailed monitoring with persistent dashboards:

```bash
make start   # Full stack with Grafana
```

Grafana provides:
- Pre-configured Prometheus datasource
- Auto-imported Roomzin dashboard
- Customizable panels and alerts
- Historical data visualization

**Note:** If you start with `make start-minimal`, you can add monitoring later:
```bash
make start-monitoring   # Start only Prometheus + Grafana
```

## Testing Cluster Health

```bash
# Check all nodes and RzGate
make test

# Manual health check for Roomzin
curl -H "Authorization: Bearer abc123" http://localhost:7880/healthz
curl -H "Authorization: Bearer abc123" http://localhost:7880/peers

# Manual health check for RzGate
curl -X POST http://localhost:8777/api \
  -H "Authorization: Bearer rzgate123" \
  -H "Content-Type: application/json" \
  -d '{"command":"GETSEGMENTS","body":{}}'
```

## Network Simulation (Optional)

Add network delay to a node to test cluster behavior:

```bash
# Add 3ms delay to roomzin-2
docker exec roomzin-2 tc qdisc add dev eth0 root netem delay 3ms

# Verify it's working
docker exec roomzin-2 tc qdisc show dev eth0

# Remove delay
docker exec roomzin-2 tc qdisc del dev eth0 root
```

## Troubleshooting

### Cluster fails to start

Check logs:
```bash
docker compose logs roomzin-0
docker compose logs prometheus
docker compose logs rzgate
```

### Node not joining cluster

Verify certificates and discovery:
```bash
docker exec roomzin-0 cat /opt/roomzin/configs/discovery.yml
docker exec roomzin-0 ls -la /opt/roomzin/certs/
```

### RzGate can't connect to Roomzin

Verify RzGate config:
```bash
docker exec rzgate cat /opt/rzgate/configs/rzgate.yml
# Check roomzin_seed_hosts: "roomzin-0,roomzin-1,roomzin-2"
```

### Authentication errors

Check token in `configs/auth.yml` matches what you're using:
```bash
cat configs/auth.yml
# Should contain: abc123 (for Roomzin)
# Should contain: rzgate123 (for RzGate)
```

### Port conflicts

If ports 7877, 7977, 8077, 7880, 7980, 8080, 8777, 3443 are in use, update the port mappings in `docker-compose.yml`.

## Updating Images

To update to the latest Roomzin or RzGate images:

```bash
# Pull latest images
docker pull mehdyjavany/roomzin:latest
docker pull mehdyjavany/rzgate:latest

# Restart the cluster
make stop && make start
```

## Clean Up

```bash
# Stop everything and remove containers, networks, volumes
make stop

# Remove dangling images
docker image prune -f
```

## Notes

1. **Certs** are per-node and must be placed in `certs/roomzin-{0,1,2}/`
2. **Data** persists in `./data/` and is cleaned up on `make stop`
3. **Monitoring** containers run in the same Docker network and can resolve node hostnames
4. **Prometheus v2.52.0** and **Grafana v13.1.0** are used
5. **Images** are pulled from Docker Hub - no local build required
6. **Pre-built images** use Alpine Linux for minimal size (~17MB per node)

## Related Repositories

- [RzGate](https://github.com/m-javani/rzgate) - HTTP/JSON proxy
- [Roomzin Bench](https://github.com/m-javani/roomzin-bench) - Benchmarking tool
- [Documentation](https://m-javani.github.io/roomzin-doc/) - Official docs
