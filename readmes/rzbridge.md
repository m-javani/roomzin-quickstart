## For RzBridge Testing

Run:
```bash
make start SHARDS=1 ZONES=1 BRIDGE=0 ZONE_ROUTER=0 EDGE_ROUTER=0 RZGATE=0
```

## RzBridge Needs

| Service | Address | Port | Purpose |
|---------|---------|------|---------|
| RzID | `localhost` | 8081 | Register bridge, discover topology |
| RzPoint | `localhost` | 9090 | Resolve node hostnames |
| Roomzin Nodes | `roomzin-0-0:7777` | 7777 | Connect to node TCP port (internal) |
| Roomzin Nodes API | `roomzin-0-0:8080` | 8080 | Health checks (optional) |

**RzBridge command:**
```bash
--rzid-addr localhost:8081
--rzpoint-addr localhost:9090
--zone-id zone1
--shard-id shard1
--bridge-id bridge-test
--listen-host 0.0.0.0
--listen-port 9000
```

**Node hostnames** from RzPoint:
- `roomzin-0-0`
- `roomzin-0-1`  
- `roomzin-0-2`

Your local machine can resolve these because they're in the Docker network. Your tests will connect to them via their exposed ports or directly if you run tests inside the Docker network.