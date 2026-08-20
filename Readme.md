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

A complete Roomzin test environment with configurable components for local development and testing.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.6+ (for data generation)
- Make (optional, for convenience)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/m-javani/roomzin-quickstart
cd roomzin-quickstart

# download all needed binaries
make download

# build local docker images
make build

# Start the full stack (2 shards, 2 zones, all components)
make start

# Check cluster health
make health

# View logs
make logs

# Stop and clean up everything
make stop
```

## Component Selection

Control which components are started using `level`:

| Level | Components |
|-------|------------|
| `cluster` | Roomzin nodes + RzID + RzPoint |
| `bridge` | cluster + Bridges |
| `zone` | bridge + Zone Routers |
| `edge` | zone + Edge Router |
| `full` | edge + RZProxy |

```bash
# if not done yet
# download all needed binaries / build local docker images
make download
make build

# Just cluster (default)
make start

# Cluster + Bridges (for bridge testing)
make start level=bridge

# Cluster + Bridges + Zone Routers (for zone router testing)
make start level=zone

# Cluster + Bridges + Zone Routers + Edge Router (for edge router testing)
make start level=edge

# Full stack without RZProxy
make start level=full

# Full stack with RZProxy
make start level=full rzproxy=true

# Full stack with HA (2 bridges per shard, 2 zone routers per zone)
make start level=full ha=true

# Full stack with HA + RZProxy
make start level=full ha=true rzproxy=true
```

## Scaling

```bash
# Custom number of shards and zones
make start SHARDS=3 ZONES=3 level=full

# Minimal cluster (1 shard, 1 zone)
make start SHARDS=1 ZONES=1
```

## HA Mode

When `ha=true`:
- 2 bridges per shard (instead of 1)
- 2 zone routers per zone (instead of 1)
- Edge router remains single instance

```bash
# Bridge HA testing
make start level=bridge ha=true SHARDS=1 ZONES=1

# Full stack HA
make start level=full ha=true
```

## What Happens When You Run `make start`

1. **Generate test data** - Creates CSV files with sample properties and packages
2. **Build snapshots** - Uses Roomzin to build snapshots from the CSV data
3. **Start containers** - Brings up all configured services

Everything is automated. No manual steps required.

## Make Commands

| Command | Description |
|---------|-------------|
| `make download` | Download all binaries: roomzin, rzbridge, rzrouter, rzproxy, rzid |
| `make build` | Builds local docker images from binaries|
| `make start` | Generate data, build snapshots, and start the environment |
| `make stop` | Stop everything and clean up all generated files |
| `make health` | Check cluster health |
| `make logs` | View all container logs |
| `make logs-<service>` | View specific service logs |
| `make test-query` | Run test queries via RZProxy |
| `make clean` | Remove generated directory and test data |
| `make help` | Show available commands |

## Access Points

| Component | Address | Port |
|-----------|---------|------|
| RZProxy HTTP | `http://localhost` | 8777 |
| RzID HTTP | `http://localhost` | 8081 |
| RzPoint HTTP | `http://localhost` | 9090 |
| Edge Router (TCP) | `localhost` | 9200 |

**Roomzin Nodes (2 shards × 3 nodes):**

| Node | TCP Port | API Port |
|------|----------|----------|
| roomzin-0-0 | 7800 | 8000 |
| roomzin-0-1 | 7801 | 8001 |
| roomzin-0-2 | 7802 | 8002 |
| roomzin-1-0 | 7810 | 8010 |
| roomzin-1-1 | 7811 | 8011 |
| roomzin-1-2 | 7812 | 8012 |

**HA Mode Ports (2 shards, 2 zones, ha=true):**

| Bridge | Port |
|--------|------|
| bridge-0-0 | 9000 |
| bridge-0-1 | 9001 |
| bridge-1-0 | 9002 |
| bridge-1-1 | 9003 |

| Zone Router | Port |
|-------------|------|
| router-zone-0-0 | 9100 |
| router-zone-0-1 | 9101 |
| router-zone-1-0 | 9102 |
| router-zone-1-1 | 9103 |

## Testing

### Health Check

```bash
make health
```

### Test Queries

```bash
make test-query
```

Or send manual requests:

```bash
# Search properties
curl -X POST http://localhost:8777/api \
  -H "Content-Type: application/json" \
  -d '{
    "command": "SEARCHPROP",
    "segment": "segment_1",
    "body": {
      "segment": "segment_1",
      "limit": 1
    }
  }'

# Search availability
curl -X POST http://localhost:8777/api \
  -H "Content-Type: application/json" \
  -d '{
    "command": "SEARCHAVAIL",
    "segment": "segment_1",
    "body": {
      "segment": "segment_1",
      "room_type": "room1",
      "type": "hotel",
      "date": ["2026-08-14"],
      "limit": 1
    }
  }'
```

## Testing Individual Components

For development of specific components, start only the required dependencies:

### Testing RzBridge

```bash
make start SHARDS=1 ZONES=1 level=bridge
```

This starts:
- 3 Roomzin nodes (1 shard)
- RzID
- RzPoint
- Bridges

Then run your local RzBridge binary connecting to:
- RzID: `localhost:8081`
- RzPoint: `localhost:9090`

### Testing RzRouter (Zone Router)

```bash
make start SHARDS=1 ZONES=1 level=zone
```

This starts: cluster + Bridges + Zone Routers. Run your local Zone Router.

### Testing RzRouter (Edge Router)

```bash
make start SHARDS=1 ZONES=1 level=edge
```

This starts: cluster + Bridges + Zone Routers + Edge Router. Run your local Edge Router.

### Testing RZProxy

```bash
make start SHARDS=1 ZONES=1 level=edge rzproxy=false
```

This starts: full stack without RZProxy. Run your local RZProxy.

### Testing HA

```bash
# Test with 2 bridges per shard
make start SHARDS=1 ZONES=1 level=bridge ha=true

# Test with 2 zone routers per zone
make start SHARDS=1 ZONES=1 level=zone ha=true
```

## Usage Examples

```bash
# Just cluster
make start SHARDS=1 ZONES=1 LEVEL=cluster

# Cluster + Bridges
make start SHARDS=1 ZONES=1 LEVEL=bridge

# Cluster + Bridges + Zone Routers
make start SHARDS=1 ZONES=1 LEVEL=zone

# Cluster + Bridges + Zone Routers + Edge Router
make start SHARDS=1 ZONES=1 LEVEL=edge

# Full stack (includes RZProxy)
make start SHARDS=1 ZONES=1 LEVEL=full RZPROXY=true

# Full stack with HA
make start SHARDS=1 ZONES=1 LEVEL=full HA=true RZPROXY=true
```

## Docker Images

This quickstart builds local Docker images from downloaded binaries:

- `roomzin:local` - Roomzin node (ports 7777, 8080)
- `rzid:local` - Control plane (port 8080)
- `rzbridge:local` - Bridge proxy (ports 9000, 9100)
- `rzrouter:local` - Router (ports 9000, 9100)
- `rzproxy:local` - HTTP/JSON proxy (port 8777)

Images are built using Dockerfiles in the `bin/` directory:
- `bin/Dockerfile.roomzin`
- `bin/Dockerfile.rzid`
- `bin/Dockerfile.rzbridge`
- `bin/Dockerfile.rzrouter`
- `bin/Dockerfile.rzproxy`


## Directory Structure

```
roomzin-quickstart/
├── quick-start.py           # Generator script
├── gen_data.py              # Test data generator
├── test_query.py            # Query test script
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
```

## Troubleshooting

### Cluster fails to start

```bash
make logs
# Or specific service
make logs-roomzin-0-0
```

## Clean Up

```bash
# Stop everything and remove all generated files
make stop

# Same as stop
make clean
```

## Notes

1. **Certs** are pre-generated and shared across all nodes (hostname verification disabled for testing)
2. **Data** is generated fresh on each `make start`
3. **Snapshots** are built automatically from test data
4. **All components** are stateless except Roomzin nodes (data persists until `make stop`)
5. **RzPoint** resolves IDs to IPs for local development (returns IPs instead of hostnames)

## Related Repositories

- [Roomzin](https://github.com/m-javani/roomzin) - Main repository
- [RzProxy](https://github.com/m-javani/rzproxy) - HTTP/JSON proxy
- [RzID](https://github.com/m-javani/rzid) - Control plane
- [RzBridge](https://github.com/m-javani/rzbridge) - Bridge proxy
- [RzRouter](https://github.com/m-javani/rzrouter) - Router
- [Documentation](https://m-javani.github.io/roomzin-doc/) - Official docs