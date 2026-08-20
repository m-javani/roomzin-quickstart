#!/usr/bin/env bash
# Roomzin Binary Downloader
# Downloads all required binaries for the quick-start project

set -e

# ============================================
# VERSIONS - Update these with each release
# ============================================
RZID_VERSION="v2.0.0"
RZBRIDGE_VERSION="v2.0.0"
RZROUTER_VERSION="v2.0.0"
RZPROXY_VERSION="v2.0.0"
ROOMZIN_VERSION="v2.0.0"
# ============================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}                 ROOMZIN BINARY DOWNLOADER${NC}"
echo -e "${BLUE}===============================================================================${NC}"

# Check dependencies
for cmd in curl; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is required but not installed.${NC}"
        exit 1
    fi
done

# Create bin directory if it doesn't exist
BIN_DIR="bin"
mkdir -p "$BIN_DIR"

# Download function
download_binary() {
    local repo=$1
    local version=$2
    local binary_name=$3
    local output_name=$4
    
    local url="https://github.com/m-javani/${repo}/releases/download/${version}/${binary_name}"
    local output="${BIN_DIR}/${output_name}"
    
    echo -e "${YELLOW}Downloading ${output_name}...${NC}"
    curl -L "$url" -o "$output"
    chmod +x "$output"
    echo -e "${GREEN}✓ Downloaded ${output_name}${NC}"
}

# Download all binaries
echo -e "${YELLOW}Downloading binaries to ./${BIN_DIR}/...${NC}"
echo ""

# Open source components
download_binary "rzid" "$RZID_VERSION" "rzid" "rzid"
download_binary "rzbridge" "$RZBRIDGE_VERSION" "rzbridge" "rzbridge"
download_binary "rzrouter" "$RZROUTER_VERSION" "rzrouter" "rzrouter"
download_binary "rzproxy" "$RZPROXY_VERSION" "rzproxy" "rzproxy"

# Roomzin (from roomzin-doc repo)
download_binary "roomzin-doc" "$ROOMZIN_VERSION" "roomzin-${ROOMZIN_VERSION}" "roomzin"

echo ""
echo -e "${GREEN}===============================================================================${NC}"
echo -e "${GREEN}✓ All binaries downloaded!${NC}"
echo -e "${GREEN}===============================================================================${NC}"
echo ""
echo -e "Binaries are in: ${BLUE}./${BIN_DIR}/${NC}"
echo -e "  - rzid"
echo -e "  - rzbridge"  
echo -e "  - rzrouter"
echo -e "  - rzproxy"
echo -e "  - roomzin"
echo ""
echo -e "${GREEN}===============================================================================${NC}"