#!/bin/bash
# ✨ Sparkling Water - One-Command Breakthrough Installation

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}✨ Initializing Sparkling Water: The Breakthrough AI Coding Agent...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found."
    exit 1
fi

# Install Sparkling Water
echo -e "${BLUE}📦 Installing and optimizing system...${NC}"
pip install -e .

echo -e "\n${GREEN}✅ Installation Complete!${NC}"
echo -e "🚀 Run '${BLUE}sw${NC}' to start the breakthrough terminal UI."
echo -e "💡 Context: Use '${BLUE}@filename${NC}' in chat to link files instantly."
echo ""
