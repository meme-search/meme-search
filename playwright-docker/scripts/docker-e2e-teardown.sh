#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Docker E2E Test Environment Teardown ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# COMPOSE_PROJECT_NAME comes from here; without it compose looks for the wrong project and stops nothing.
ENV_FILE="$SCRIPT_DIR/../.env.docker-e2e"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if Docker daemon is responsive
if ! docker ps >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠ Docker daemon not responsive - skipping log save${NC}"
  echo -e "${YELLOW}Note: This may happen if Docker crashed during tests${NC}"
else
  # Save logs
  echo -e "${YELLOW}Saving service logs...${NC}"
  docker compose -f docker-compose.e2e.yml logs > "$LOG_DIR/docker-e2e-${TIMESTAMP}.log" 2>&1 || true
  echo -e "${GREEN}✓ Logs saved to $LOG_DIR/docker-e2e-${TIMESTAMP}.log${NC}"
fi

# Stop and remove containers
echo -e "${YELLOW}Stopping Docker services...${NC}"
docker compose -f docker-compose.e2e.yml down

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to stop services${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Services stopped${NC}"

# Ask about volume removal (auto-answer in CI/automated runs)
if [ "$CI" = "true" ] || [ "$AUTO_CLEANUP" = "true" ]; then
  echo -e "${YELLOW}Auto-removing volumes (automated mode)...${NC}"
  docker compose -f docker-compose.e2e.yml down -v
  echo -e "${GREEN}✓ Volumes removed${NC}"
else
  read -p "Remove volumes? (y/N): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Removing volumes...${NC}"
    docker compose -f docker-compose.e2e.yml down -v
    echo -e "${GREEN}✓ Volumes removed${NC}"
  else
    echo -e "${YELLOW}Volumes preserved${NC}"
  fi
fi

echo ""
echo -e "${GREEN}✓ Teardown complete${NC}"
echo ""
echo -e "Logs available at: ${BLUE}$LOG_DIR/docker-e2e-${TIMESTAMP}.log${NC}"
echo ""
