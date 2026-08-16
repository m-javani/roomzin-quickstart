.PHONY: start stop test-query logs health clean help

# Default values
SHARDS ?= 2
ZONES ?= 2
BRIDGE ?= 1
ZONE_ROUTER ?= 1
EDGE_ROUTER ?= 1
RZGATE ?= 1

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)Roomzin Quick-Start$(NC)"
	@echo ""
	@echo "Usage:"
	@echo "  make start           - Generate data, build snapshots, and start the environment"
	@echo "  make start SHARDS=3  - Start with 3 shards"
	@echo "  make start ZONES=3   - Start with 3 zones"
	@echo "  make start BRIDGE=0  - Start without RzBridge"
	@echo "  make stop            - Stop and clean up everything"
	@echo "  make test-query      - Run test queries via RZGate"
	@echo "  make health          - Check cluster health"
	@echo "  make logs            - View all logs"
	@echo "  make logs-<service>  - View specific service logs"
	@echo "  make clean           - Remove generated directory and test data"
	@echo "  make help            - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make start"
	@echo "  make start SHARDS=1 ZONES=1 BRIDGE=0 ZONE_ROUTER=0 EDGE_ROUTER=0 RZGATE=0"
	@echo "  make start BRIDGE=1 ZONE_ROUTER=0 EDGE_ROUTER=0 RZGATE=0"
	@echo "  make logs-roomzin-0-0"

start:
	@echo "$(BLUE)🚀 Starting Roomzin environment...$(NC)"
	@echo "   Shards: $(SHARDS)"
	@echo "   Zones: $(ZONES)"
	@echo "   Bridge: $(BRIDGE)"
	@echo "   Zone Router: $(ZONE_ROUTER)"
	@echo "   Edge Router: $(EDGE_ROUTER)"
	@echo "   RZGate: $(RZGATE)"
	@echo ""
	@echo "$(BLUE)📄 Generating test data...$(NC)"
	@python3 gen_data.py --shards $(SHARDS) --force
	@echo "$(GREEN)✅ CSV data generated$(NC)"
	@echo ""
	@echo "$(BLUE)📦 Building snapshots...$(NC)"
	@# Generate docker-compose first (so data dirs exist)
	@python3 quick-start.py --shards $(SHARDS) --zones $(ZONES) \
		--bridge $(BRIDGE) --zone-router $(ZONE_ROUTER) \
		--edge-router $(EDGE_ROUTER) --rzgate $(RZGATE) --force
	@# For each shard directory in test-data/
	@for shard_dir in test-data/shard*/; do \
		shard_id=$$(basename $$shard_dir); \
		shard_num=$${shard_id##shard}; \
		echo "  Building snapshot for $$shard_id..."; \
		cp configs/codecs.yml $$shard_dir/; \
		mkdir -p generated/temp-snapshots/$$shard_id; \
		docker run --rm \
			-v $$(pwd)/test-data:/opt/test-data:ro \
			-v $$(pwd)/generated/temp-snapshots:/opt/snapshots \
			mehdyjavany/roomzin:latest \
			/opt/roomzin/roomzin build-snapshot \
				--shard-id $$shard_id \
				--input-path /opt/test-data/$$shard_id \
				--output-path /opt/snapshots/$$shard_id; \
		node_idx=0; \
		while [ $$node_idx -lt 3 ]; do \
			node_dir="generated/data/roomzin-$$((shard_num-1))-$$node_idx"; \
			mkdir -p $$node_dir; \
			cp generated/temp-snapshots/$$shard_id/snapshot.tar.zst $$node_dir/; \
			node_idx=$$((node_idx + 1)); \
		done; \
		echo "  ✓ $$shard_id snapshot copied to all 3 nodes"; \
	done
	@rm -rf generated/temp-snapshots
	@echo "$(GREEN)✅ Snapshots built$(NC)"
	@echo ""
	@echo "$(BLUE)🏗️  Starting containers...$(NC)"
	cd generated && docker compose up -d
	@echo ""
	@echo "$(YELLOW)⏳ Waiting for cluster to stabilize...$(NC)"
	@sleep 15
	@echo ""
	@$(MAKE) health
	@echo ""
	@echo "$(GREEN)✅ Environment ready!$(NC)"
	@echo ""
	@echo "  $(BLUE)Service endpoints:$(NC)"
	@echo "    RzID:    http://localhost:8081"
	@echo "    RzPoint: http://localhost:9090"
	@if [ $(BRIDGE) -eq 1 ]; then \
		echo "    Bridge:  localhost:9000 (shard1), localhost:9001 (shard2)"; \
	fi
	@if [ $(ZONE_ROUTER) -eq 1 ]; then \
		echo "    Zone Router: localhost:9100 (zone1), localhost:9101 (zone2)"; \
	fi
	@if [ $(EDGE_ROUTER) -eq 1 ]; then \
		echo "    Edge Router (TCP): localhost:9200"; \
	fi
	@if [ $(RZGATE) -eq 1 ] && [ $(EDGE_ROUTER) -eq 1 ]; then \
		echo "    RZGate:  http://localhost:8777"; \
	fi
	@echo ""
	@echo "  $(BLUE)Test with: make test-query$(NC)"

stop:
	@echo "$(YELLOW)🛑 Stopping and cleaning up...$(NC)"
	@cd generated && docker compose kill && docker compose down -v --remove-orphans 2>/dev/null || true
	@sudo rm -rf generated
	@sudo rm -rf test-data
	@echo "$(GREEN)✅ Stopped and cleaned$(NC)"

test-query:
	@echo "$(BLUE)🔍 Running test queries via RZGate...$(NC)"
	@echo ""
	@python3 test_query.py
	@echo ""

health:
	@echo "$(BLUE)🔍 Detailed health check...$(NC)"
	@echo ""
	@echo "  $(BLUE)Roomzin nodes:$(NC)"
	@# Dynamically check only nodes that exist
	@for shard in $$(seq 1 $(SHARDS)); do \
		for node in 0 1 2; do \
			port=$$((8000 + (shard-1)*10 + node)); \
			status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$$port/healthz 2>/dev/null || echo "000"); \
			if [ "$$status" = "200" ]; then \
				echo "    $(GREEN)✅ Node on port $$port: healthy$(NC)"; \
			elif [ "$$status" = "000" ]; then \
				echo "    $(YELLOW)⚠️  Node on port $$port: not responding$(NC)"; \
			else \
				echo "    $(RED)❌ Node on port $$port: unhealthy ($$status)$(NC)"; \
			fi \
		done; \
	done
	@echo ""
	@echo "  $(BLUE)Services health:$(NC)"
	@if curl -s http://localhost:8081/health 2>/dev/null | grep -q "OK"; then \
		echo "    $(GREEN)✅ RzID: healthy (OK)$(NC)"; \
	else \
		echo "    $(RED)❌ RzID: unhealthy$(NC)"; \
	fi
	@if curl -s http://localhost:9090/routers/test 2>/dev/null | grep -q "test"; then \
		echo "    $(GREEN)✅ RzPoint: running (echo working)$(NC)"; \
	else \
		echo "    $(RED)❌ RzPoint: not responding$(NC)"; \
	fi
	@if [ $(RZGATE) -eq 1 ] && [ $(EDGE_ROUTER) -eq 1 ]; then \
		if curl -s -o /dev/null -w "%{http_code}" http://localhost:8777/health 2>/dev/null | grep -q "200"; then \
			echo "    $(GREEN)✅ RZGate: running$(NC)"; \
		else \
			echo "    $(RED)❌ RZGate: not responding (check logs)$(NC)"; \
		fi \
	fi
	@echo ""
	
logs:
	@cd generated && docker compose logs -f

logs-%:
	@cd generated && docker compose logs -f $(subst logs-,,$@)

clean:
	@echo "$(YELLOW)🧹 Cleaning up...$(NC)"
	@cd generated && docker compose kill && docker compose down -v --remove-orphans 2>/dev/null || true
	@sudo rm -rf generated
	@sudo rm -rf test-data
	@echo "$(GREEN)✅ Cleaned$(NC)"