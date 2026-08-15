.PHONY: csv snapshot data start stop test-query logs health clean help

# Default values
SHARDS ?= 2
ZONES ?= 2

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
	@echo "  make csv             - Generate test CSV data"
	@echo "  make snapshot        - Build snapshots from CSV data"
	@echo "  make data            - Generate CSVs and build snapshots"
	@echo "  make start           - Start the environment"
	@echo "  make stop            - Stop and clean up"
	@echo "  make test-query      - Run a test query via RZGate"
	@echo "  make logs            - View all logs"
	@echo "  make logs-<service>  - View specific service logs"
	@echo "  make clean           - Remove generated directory"
	@echo "  make help            - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make data && make start"
	@echo "  make start SHARDS=3 ZONES=3"
	@echo "  make logs-roomzin-0-0"

csv:
	@echo "$(BLUE)📄 Generating CSV test data...$(NC)"
	@python3 gen_data.py --shards $(SHARDS) --force
	@echo "$(GREEN)✅ CSV data generated$(NC)"

snapshot:
	@echo "$(BLUE)📦 Building snapshots from test data...$(NC)"
	@echo ""
	@# Generate docker-compose first (so data dirs exist)
	@python3 quick-start.py --shards $(SHARDS) --zones $(ZONES) --force
	@echo ""
	@# For each shard directory in test-data/
	@for shard_dir in test-data/shard*/; do \
		shard_id=$$(basename $$shard_dir); \
		shard_num=$${shard_id##shard}; \
		echo "  Building snapshot for $$shard_id..."; \
		\
		# Copy codecs.yml to the shard directory (build-snapshot needs it) \
		cp configs/codecs.yml $$shard_dir/; \
		\
		mkdir -p generated/temp-snapshots/$$shard_id; \
		\
		docker run --rm \
			-v $$(pwd)/test-data:/opt/test-data:ro \
			-v $$(pwd)/generated/temp-snapshots:/opt/snapshots \
			mehdyjavany/roomzin:latest \
			/opt/roomzin/roomzin build-snapshot \
				--shard-id $$shard_id \
				--input-path /opt/test-data/$$shard_id \
				--output-path /opt/snapshots/$$shard_id; \
		\
		node_idx=0; \
		while [ $$node_idx -lt 3 ]; do \
			node_dir="generated/data/roomzin-$$((shard_num-1))-$$node_idx"; \
			mkdir -p $$node_dir; \
			cp generated/temp-snapshots/$$shard_id/snapshot.tar.zst $$node_dir/; \
			node_idx=$$((node_idx + 1)); \
		done; \
		echo "  ✓ $$shard_id snapshot copied to all 3 nodes"; \
	done
	@echo ""
	@rm -rf generated/temp-snapshots
	@echo "$(GREEN)✅ Snapshots built and ready$(NC)"
	
data: csv snapshot
	@echo "$(GREEN)✅ Data preparation complete$(NC)"

start:
	@echo "$(BLUE)🚀 Starting Roomzin environment...$(NC)"
	@echo "   Shards: $(SHARDS)"
	@echo "   Zones: $(ZONES)"
	@echo ""
	@# Generate docker-compose if it doesn't exist
	@if [ ! -f generated/docker-compose.yml ]; then \
		python3 quick-start.py --shards $(SHARDS) --zones $(ZONES) --force; \
	fi
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
	@echo "    RZGate:  http://localhost:8777"
	@echo "    RzID:    http://localhost:8081"
	@echo "    RzPoint: http://localhost:9090"
	@echo "    Edge Router (TCP): localhost:9200"
	@echo ""
	@echo "  $(BLUE)Test with: make test-query$(NC)"

test-query:
	@echo "$(BLUE)🔍 Running test queries via RZGate...$(NC)"
	@echo ""
	@python3 test_query.py
	@echo ""

stop:
	@echo "$(YELLOW)🛑 Stopping containers...$(NC)"
	cd generated && docker compose down -v --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✅ Stopped$(NC)"

health:
	@echo "$(BLUE)🔍 Detailed health check...$(NC)"
	@echo ""
	@echo "  $(BLUE)Roomzin nodes:$(NC)"
	@for port in 8000 8001 8002 8010 8011 8012; do \
		status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$$port/healthz 2>/dev/null || echo "000"); \
		if [ "$$status" = "200" ]; then \
			echo "    $(GREEN)✅ Node on port $$port: healthy$(NC)"; \
		elif [ "$$status" = "000" ]; then \
			echo "    $(YELLOW)⚠️  Node on port $$port: not responding$(NC)"; \
		else \
			echo "    $(RED)❌ Node on port $$port: unhealthy ($$status)$(NC)"; \
		fi \
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
	@if curl -s -o /dev/null -w "%{http_code}" http://localhost:8777/health 2>/dev/null | grep -q "200"; then \
		echo "    $(GREEN)✅ RZGate: running$(NC)"; \
	else \
		echo "    $(RED)❌ RZGate: not responding (check logs)$(NC)"; \
	fi
	@echo ""
	@echo "  $(BLUE)Registered components (from RzID):$(NC)"
	@curl -s http://localhost:8081/metrics 2>/dev/null | grep -E "rzid_registered_(nodes|bridges|routers)" | sed 's/^/    /' || echo "    $(YELLOW)No metrics available$(NC)"

logs:
	@cd generated && docker compose logs -f

logs-%:
	@cd generated && docker compose logs -f $(subst logs-,,$@)

clean:
	@echo "$(YELLOW)🧹 Cleaning up...$(NC)"
	@cd generated && docker compose down -v --remove-orphans 2>/dev/null || true
	@sudo rm -rf generated
	@sudo rm -rf test-data
	@echo "$(GREEN)✅ Cleaned$(NC)"