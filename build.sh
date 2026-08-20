#!/usr/bin/env bash
# Roomzin Docker Image Builder
# Creates Dockerfiles in bin/ and builds images from them

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}                 ROOMZIN DOCKER IMAGE BUILDER${NC}"
echo -e "${BLUE}===============================================================================${NC}"

# Check dependencies
for cmd in docker; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is required but not installed.${NC}"
        exit 1
    fi
done

# Check if bin directory exists
BIN_DIR="bin"
if [ ! -d "$BIN_DIR" ]; then
    echo -e "${RED}Error: ./${BIN_DIR} directory not found. Run download.sh first.${NC}"
    exit 1
fi

echo -e "${YELLOW}Creating Dockerfiles in ./${BIN_DIR}/...${NC}"
echo ""

# Create Dockerfile for roomzin
cat > ${BIN_DIR}/Dockerfile.roomzin << 'EOF'
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY roomzin /opt/roomzin/roomzin
RUN chmod +x /opt/roomzin/roomzin
EXPOSE 7777
EXPOSE 8080
CMD ["/opt/roomzin/roomzin"]
EOF

# Create Dockerfile for rzbridge
cat > ${BIN_DIR}/Dockerfile.rzbridge << 'EOF'
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY rzbridge /opt/rzbridge/rzbridge
RUN chmod +x /opt/rzbridge/rzbridge
EXPOSE 9000
EXPOSE 9100
CMD ["/opt/rzbridge/rzbridge"]
EOF

# Create Dockerfile for rzrouter
cat > ${BIN_DIR}/Dockerfile.rzrouter << 'EOF'
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY rzrouter /opt/rzrouter/rzrouter
RUN chmod +x /opt/rzrouter/rzrouter
EXPOSE 9000
EXPOSE 9100
CMD ["/opt/rzrouter/rzrouter"]
EOF

# Create Dockerfile for rzid
cat > ${BIN_DIR}/Dockerfile.rzid << 'EOF'
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY rzid /opt/rzid/rzid
RUN chmod +x /opt/rzid/rzid
EXPOSE 8080
CMD ["/opt/rzid/rzid"]
EOF

# Create Dockerfile for rzproxy
cat > ${BIN_DIR}/Dockerfile.rzproxy << 'EOF'
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY rzproxy /opt/rzproxy/rzproxy
RUN chmod +x /opt/rzproxy/rzproxy
EXPOSE 8777
CMD ["/opt/rzproxy/rzproxy"]
EOF

echo -e "${GREEN}✓ Dockerfiles created in ./${BIN_DIR}/${NC}"
echo ""

echo -e "${YELLOW}Building Docker images...${NC}"
echo ""

# Build images using Dockerfiles in bin/
cd ${BIN_DIR}
docker build -t roomzin:local -f Dockerfile.roomzin .
docker build -t rzbridge:local -f Dockerfile.rzbridge .
docker build -t rzrouter:local -f Dockerfile.rzrouter .
docker build -t rzid:local -f Dockerfile.rzid .
docker build -t rzproxy:local -f Dockerfile.rzproxy .
cd ..

echo ""
echo -e "${GREEN}===============================================================================${NC}"
echo -e "${GREEN}✓ All images built!${NC}"
echo -e "${GREEN}===============================================================================${NC}"
echo ""
echo -e "Images built:"
echo -e "  - ${BLUE}roomzin:local${NC} (ports 7777, 8080)"
echo -e "  - ${BLUE}rzbridge:local${NC} (ports 9000, 9100)"
echo -e "  - ${BLUE}rzrouter:local${NC} (ports 9000, 9100)"
echo -e "  - ${BLUE}rzid:local${NC} (port 8080)"
echo -e "  - ${BLUE}rzproxy:local${NC} (port 8777)"
echo ""
echo -e "Dockerfiles are in: ${BLUE}./${BIN_DIR}/Dockerfile.*${NC}"
echo -e "To verify: ${BLUE}docker images | grep local${NC}"
echo -e "${GREEN}===============================================================================${NC}"