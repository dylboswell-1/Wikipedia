#!/bin/bash

# Development helper script
# Quick commands for common tasks

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

help() {
  echo -e "${BLUE}Ollama Backend - Development Helper${NC}"
  echo ""
  echo "Usage: ./dev.sh [command]"
  echo ""
  echo "Commands:"
  echo "  start       - Start docker-compose (development)"
  echo "  stop        - Stop docker-compose"
  echo "  logs        - Show live logs"
  echo "  logs-backend - Show backend logs only"
  echo "  logs-ollama  - Show Ollama logs only"
  echo "  restart     - Restart services"
  echo "  build       - Build Docker image"
  echo "  test        - Run tests against local service"
  echo "  clean       - Remove containers and volumes"
  echo "  shell-backend - Open shell in backend container"
  echo "  shell-ollama  - Open shell in Ollama container"
  echo ""
}

case "${1:-help}" in
  start)
    echo -e "${GREEN}▶ Starting services...${NC}"
    docker-compose up -d
    echo "Waiting for services..."
    sleep 5
    docker-compose ps
    ;;
  stop)
    echo -e "${GREEN}⏹ Stopping services...${NC}"
    docker-compose stop
    ;;
  logs)
    docker-compose logs -f
    ;;
  logs-backend)
    docker-compose logs -f backend
    ;;
  logs-ollama)
    docker-compose logs -f ollama
    ;;
  restart)
    echo -e "${GREEN}🔄 Restarting services...${NC}"
    docker-compose restart
    ;;
  build)
    echo -e "${GREEN}🔨 Building Docker image...${NC}"
    docker build -t ollama-backend:latest .
    ;;
  test)
    echo -e "${GREEN}🧪 Running tests...${NC}"
    ./test.sh
    ;;
  clean)
    echo -e "${GREEN}🗑 Cleaning up...${NC}"
    docker-compose down -v
    ;;
  shell-backend)
    echo -e "${GREEN}💻 Opening shell in backend container...${NC}"
    docker-compose exec backend bash
    ;;
  shell-ollama)
    echo -e "${GREEN}💻 Opening shell in Ollama container...${NC}"
    docker-compose exec ollama bash
    ;;
  *)
    help
    ;;
esac
