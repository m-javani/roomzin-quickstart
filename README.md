# Roomzin Quickstart

> **⚠️ IMPORTANT: Development & Testing Only**
>
> This setup is **for local development and testing only**. For production, deploy Roomzin on **bare metal or VMs** for maximum performance, lower latency, and better resource control.

A complete Roomzin test environment with configurable components for local development and testing.

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.6+ (for data generation)
- Make (optional, for convenience)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/m-javani/roomzin-quickstart
cd roomzin-quickstart

# Download binaries and build Docker images
make download
make build

# Start the full stack (2 shards, 2 zones, all components)
make start

# Check cluster health
make health

# View logs
make logs

# Stop and clean up
make stop
```

## 📊 Component Levels

Control which components are started using the `LEVEL` parameter:

| Level | Components Included |
|-------|---------------------|
| `cluster` | Roomzin nodes + RzID + RzPoint |
| `bridge` | Cluster + Bridges |
| `zone` | Bridge + Zone Routers |
| `edge` | Zone + Edge Router |
| `full` | Edge + RZProxy |

### Examples

```bash
# Just the cluster (default)
make start

# Add bridges for bridge testing
make start LEVEL=bridge

# Add zone routers
make start LEVEL=zone

# Add edge router
make start LEVEL=edge

# Full stack with RZProxy
make start LEVEL=full RZPROXY=true

# Full stack with HA (2 bridges, 2 zone routers)
make start LEVEL=full HA=true RZPROXY=true
```

## ⚙️ Configuration Options

### Scaling

```bash
# Custom number of shards and zones
make start SHARDS=3 ZONES=3 LEVEL=full

# Minimal cluster (1 shard, 1 zone)
make start SHARDS=1 ZONES=1
```

### High Availability (HA) Mode

When `HA=true`:
- 2 bridges per shard (instead of 1)
- 2 zone routers per zone (instead of 1)
- Edge router remains single instance

```bash
# Bridge HA testing
make start LEVEL=bridge HA=true SHARDS=1 ZONES=1

# Full stack HA
make start LEVEL=full HA=true
```

## 🎯 Testing Individual Components

For component development, start only the required dependencies:

### Test RzBridge
```bash
make start SHARDS=1 ZONES=1 LEVEL=bridge
```
Then run your local RzBridge connecting to `localhost:8081` (RzID) and `localhost:9090` (RzPoint).

### Test RzRouter (Zone Router)
```bash
make start SHARDS=1 ZONES=1 LEVEL=zone
```

### Test RzRouter (Edge Router)
```bash
make start SHARDS=1 ZONES=1 LEVEL=edge
```

### Test RZProxy
```bash
make start SHARDS=1 ZONES=1 LEVEL=edge RZPROXY=false
```
Then run your local RZProxy.

### Test HA Configurations
```bash
# 2 bridges per shard
make start SHARDS=1 ZONES=1 LEVEL=bridge HA=true

# 2 zone routers per zone
make start SHARDS=1 ZONES=1 LEVEL=zone HA=true
```

## 🏗️ What Happens When You Run `make start`

1. **Generate test data** - Creates CSV files with sample properties and packages
2. **Build snapshots** - Uses Roomzin to build snapshots from CSV data
3. **Start containers** - Brings up all configured services

Everything is automated - no manual steps required.

## 🔌 Access Points

| Component | Address | Port |
|-----------|---------|------|
| RZProxy HTTP | `http://localhost` | 8777 |
| RzID HTTP | `http://localhost` | 8081 |
| RzPoint HTTP | `http://localhost` | 9090 |
| Edge Router (TCP) | `localhost` | 9200 |

### Roomzin Nodes (2 shards × 3 nodes)

| Node | TCP Port | API Port |
|------|----------|----------|
| roomzin-0-0 | 7800 | 8000 |
| roomzin-0-1 | 7801 | 8001 |
| roomzin-0-2 | 7802 | 8002 |
| roomzin-1-0 | 7810 | 8010 |
| roomzin-1-1 | 7811 | 8011 |
| roomzin-1-2 | 7812 | 8012 |

### HA Mode Ports (2 shards, 2 zones, HA=true)

| Bridge | Port | Zone Router | Port |
|--------|------|-------------|------|
| bridge-0-0 | 9000 | router-zone-0-0 | 9100 |
| bridge-0-1 | 9001 | router-zone-0-1 | 9101 |
| bridge-1-0 | 9002 | router-zone-1-0 | 9102 |
| bridge-1-1 | 9003 | router-zone-1-1 | 9103 |

## 🛠️ Make Commands

| Command | Description |
|---------|-------------|
| `make download` | Download all binaries |
| `make build` | Build local Docker images |
| `make start` | Generate data, build snapshots, and start environment |
| `make stop` | Stop everything and clean up generated files |
| `make health` | Check cluster health |
| `make logs` | View all container logs |
| `make logs-<service>` | View specific service logs |
| `make clean` | Remove generated directory and test data |
| `make help` | Show available commands |

## 📁 Directory Structure

```
roomzin-quickstart/
├── quick-start.py           # Generator script
├── gen_data.py              # Test data generator
├── rzpoint-echo.py          # RzPoint resolver
├── download.sh              # Binary downloader
├── build.sh                 # Docker image builder
├── Makefile                 # Automation targets
├── bin/                     # Downloaded binaries and Dockerfiles
│   ├── roomzin
│   ├── rzbridge
│   ├── rzrouter
│   ├── rzid
│   ├── rzproxy
│   ├── Dockerfile.roomzin
│   ├── Dockerfile.rzbridge
│   ├── Dockerfile.rzrouter
│   ├── Dockerfile.rzid
│   └── Dockerfile.rzproxy
└── generated/               # Created by make start
    ├── docker-compose.yml
    ├── certs/
    ├── configs/
    ├── data/
    └── rzpoint-echo.py
```

## 🐳 Docker Images

This quickstart builds local Docker images from downloaded binaries:

- `roomzin:local` - Roomzin node (ports 7777, 8080)
- `rzid:local` - Control plane (port 8080)
- `rzbridge:local` - Bridge proxy (ports 9000, 9100)
- `rzrouter:local` - Router (ports 9000, 9100)
- `rzproxy:local` - HTTP/JSON proxy (port 8777)

## 🔍 Troubleshooting

### Cluster fails to start

```bash
make logs
# Or specific service
make logs-roomzin-0-0
```

### Clean everything

```bash
# Stop everything and remove all generated files
make stop

# Same as stop
make clean
```

## 📝 Notes

- **Certs** are pre-generated and shared across all nodes (hostname verification disabled for testing)
- **Data** is generated fresh on each `make start`
- **Snapshots** are built automatically from test data
- **All components** are stateless except Roomzin nodes (data persists until `make stop`)
- **RzPoint** resolves IDs to IPs for local development (returns IPs instead of hostnames)

## 🔗 Related Repositories

- [Roomzin](https://github.com/m-javani/roomzin) - Main repository
- [RzProxy](https://github.com/m-javani/rzproxy) - HTTP/JSON proxy
- [RzID](https://github.com/m-javani/rzid) - Control plane
- [RzBridge](https://github.com/m-javani/rzbridge) - Bridge proxy
- [RzRouter](https://github.com/m-javani/rzrouter) - Router
- [Documentation](https://m-javani.github.io/roomzin-doc/) - Official docs