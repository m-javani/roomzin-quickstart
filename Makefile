MAKEFLAGS += --no-print-directory

.PHONY: certs
certs:
	./gen_certs.sh roomzin-0 roomzin-1 roomzin-2 rzgate

.PHONY: start stop test logs monitoring monitoring-down help
start:
	@echo "Starting full stack..."
	docker compose --profile full up -d
	@sleep 8
	@$(MAKE) test
	@echo ""
	@echo "✅ Full stack ready!"
	@echo "  Roomzin API ports: 7880, 7980, 8080"
	@echo "  RzGate HTTP:       http://localhost:8777"
	@echo "  RzGate HTTPS:      https://localhost:3443"
	@echo "  Prometheus:        http://localhost:9090"
	@echo "  Grafana:           http://localhost:3000 (admin/admin)"
	@echo "  HTML Dashboard:    open dashboard.html in your browser"

start-minimal:
	@echo "Starting minimal stack..."
	docker compose up -d roomzin-0 roomzin-1 roomzin-2
	@sleep 5
	@$(MAKE) test
	@echo ""
	@echo "✅ Minimal stack ready!"
	@echo "  Roomzin API ports: 7880, 7980, 8080"
	@echo "  HTML Dashboard:    open dashboard.html in your browser"

start-monitoring:
	@echo "Starting monitoring stack..."
	docker compose --profile monitoring up -d prometheus grafana
	@echo "✅ Monitoring ready!"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"
		
stop:
	docker compose --profile full down -v --remove-orphans
	@echo "Cleaning up data directories..."
	@docker run --rm -v $(PWD)/data:/data alpine sh -c 'rm -rf /data/roomzin-*'
	@echo "Removing orphaned containers..."
	@docker container prune -f
	@echo "Pruning unused networks..."
	@docker network prune -f
	@echo "Cleanup complete"

test:
	@echo "Checking cluster health..."
	@for port in 7880 7980 8080; do \
		status=$$(curl -s -H "Authorization: Bearer abc123" http://localhost:$$port/healthz 2>/dev/null || echo "UNHEALTHY"); \
		if [ "$$status" = "UNHEALTHY" ]; then \
			printf "\033[31m✘\033[0m Node on API port %s: %s\n" "$$port" "$$status"; \
		else \
			printf "\033[32m✔\033[0m Node on API port %s: %s\n" "$$port" "$$status"; \
		fi \
	done
	@echo ""
	@echo "Checking RzGate health..."
	@if curl -s -X POST http://localhost:8777/api \
		-H "Authorization: Bearer rzgate123" \
		-H "Content-Type: application/json" \
		-d '{"command":"GETSEGMENTS","body":{}}' 2>/dev/null | grep -q "success"; then \
		printf "\033[32m✔\033[0m RzGate is healthy\n"; \
	else \
		printf "\033[31m✘\033[0m RzGate is unhealthy\n"; \
	fi

logs:
	docker compose logs -f

monitoring:
	@echo "Monitoring stack is already running with the cluster"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"

monitoring-down:
	@echo "Monitoring stack is managed by docker compose"
	@echo "Use 'make stop' to stop everything, or 'docker compose stop prometheus grafana'"

help:
	@echo "Available targets:"
	@echo "  make start          - Start the 3-node Roomzin cluster + monitoring + RzGate"
	@echo "  make start-minimal  - Start only Roomzin nodes (no RzGate, no monitoring)"
	@echo "  make start-monitoring - Start monitoring stack (requires existing cluster)"
	@echo "  make stop           - Stop and clean up everything"
	@echo "  make test           - Check cluster and RzGate health"
	@echo "  make logs           - View all logs"
	@echo "  make monitoring     - Show monitoring URLs"
	@echo "  make help           - Show this help"