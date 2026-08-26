#!/usr/bin/env bash
# Roomzin Binary Downloader

set -e

# Configuration - set to "latest" or specific version
RZID_VERSION="latest"
RZBRIDGE_VERSION="latest"
RZROUTER_VERSION="latest"
RZPROXY_VERSION="latest"
ROOMZIN_VERSION="latest"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Downloading Roomzin binaries...${NC}"

BIN_DIR="bin"
mkdir -p "$BIN_DIR"

download() {
    local repo=$1
    local version=$2
    local binary=$3
    local output=$4
    
    local url
    if [ "$version" = "latest" ]; then
        url="https://github.com/m-javani/${repo}/releases/latest/download/${binary}"
    else
        url="https://github.com/m-javani/${repo}/releases/download/${version}/${binary}"
    fi
    
    echo -e "${YELLOW}Downloading ${output}...${NC}"
    curl -L -# "$url" -o "${BIN_DIR}/${output}"
    chmod +x "${BIN_DIR}/${output}"
    echo -e "${GREEN}✓ Downloaded ${output}${NC}"
}

# Download all binaries
download "rzid" "$RZID_VERSION" "rzid" "rzid"
download "rzbridge" "$RZBRIDGE_VERSION" "rzbridge" "rzbridge"
download "rzrouter" "$RZROUTER_VERSION" "rzrouter" "rzrouter"
download "rzproxy" "$RZPROXY_VERSION" "rzproxy" "rzproxy"
download "roomzin-doc" "$ROOMZIN_VERSION" "roomzin" "roomzin"

echo -e "${GREEN}✓ All binaries downloaded to ./${BIN_DIR}/${NC}"