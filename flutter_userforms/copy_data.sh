#!/bin/bash

# Script to copy data files from project root to Flutter assets

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Copying data files to Flutter assets...${NC}"

# Project root is one level up
PROJECT_ROOT="../data"
ASSETS_DIR="assets/data"

# Create assets directory if it doesn't exist
mkdir -p "$ASSETS_DIR"

# Copy ncsu_orgs.txt if it exists
if [ -f "$PROJECT_ROOT/ncsu_orgs.txt" ]; then
    cp "$PROJECT_ROOT/ncsu_orgs.txt" "$ASSETS_DIR/"
    echo -e "${GREEN}✓ Copied ncsu_orgs.txt${NC}"
else
    echo "⚠️  ncsu_orgs.txt not found in $PROJECT_ROOT"
fi

# You can add more files here as needed
# if [ -f "$PROJECT_ROOT/courses.txt" ]; then
#     cp "$PROJECT_ROOT/courses.txt" "$ASSETS_DIR/"
#     echo -e "${GREEN}✓ Copied courses.txt${NC}"
# fi

echo -e "${BLUE}✅ Done! Run 'flutter run' to use the updated data.${NC}"
