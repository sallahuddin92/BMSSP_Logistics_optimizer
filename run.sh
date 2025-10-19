#!/bin/bash

# BMSSP Routing System - Production Deployment Script
# This script provides easy commands to manage the entire system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "  BMSSP Routing System - $1"
    echo "=========================================="
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is available"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_success "Docker daemon is running"
}

show_help() {
    echo "BMSSP Routing System Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start          Start all services (default)"
    echo "  stop           Stop all services"
    echo "  restart        Restart all services"
    echo "  build          Build all Docker images"
    echo "  logs           Show logs from all services"
    echo "  logs-backend   Show backend logs"
    echo "  logs-frontend  Show frontend logs"
    echo "  status         Show service status"
    echo "  test           Run unit tests"
    echo "  benchmark      Run benchmarks"
    echo "  clean          Clean up containers and volumes"
    echo "  dev            Start in development mode"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start       # Start the system"
    echo "  $0 benchmark   # Run performance benchmarks"
    echo "  $0 logs        # View all logs"
    echo ""
}

start_services() {
    print_header "Starting Services"
    
    # Use docker compose (newer) or docker-compose (legacy)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    echo "Building and starting services..."
    $COMPOSE_CMD up --build -d
    
    echo ""
    echo "Waiting for services to be ready..."
    sleep 10
    
    # Health checks
    echo "Checking backend health..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Backend is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend health check failed"
            $COMPOSE_CMD logs backend
            exit 1
        fi
        sleep 2
    done
    
    echo "Checking frontend..."
    if curl -f http://localhost:8080/ &> /dev/null; then
        print_success "Frontend is accessible"
    else
        print_warning "Frontend might not be ready yet"
    fi
    
    echo ""
    print_success "All services started successfully!"
    echo ""
    echo "🌐 Frontend: http://localhost:8080"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo ""
    echo "Use '$0 logs' to view logs"
    echo "Use '$0 stop' to stop services"
}

stop_services() {
    print_header "Stopping Services"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    $COMPOSE_CMD down
    print_success "All services stopped"
}

restart_services() {
    print_header "Restarting Services"
    stop_services
    start_services
}

build_images() {
    print_header "Building Images"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    $COMPOSE_CMD build --no-cache
    print_success "All images built successfully"
}

show_logs() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    case "$1" in
        backend)
            print_header "Backend Logs"
            $COMPOSE_CMD logs -f backend
            ;;
        frontend)
            print_header "Frontend Logs"
            $COMPOSE_CMD logs -f frontend
            ;;
        *)
            print_header "All Service Logs"
            $COMPOSE_CMD logs -f
            ;;
    esac
}

show_status() {
    print_header "Service Status"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    $COMPOSE_CMD ps
    
    echo ""
    echo "Health Checks:"
    
    # Backend health
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_success "Backend API: Healthy"
    else
        print_error "Backend API: Unhealthy"
    fi
    
    # Frontend health
    if curl -f http://localhost:8080/ &> /dev/null; then
        print_success "Frontend: Accessible"
    else
        print_error "Frontend: Not accessible"
    fi
}

run_tests() {
    print_header "Running Tests"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # Build backend for testing
    echo "Building backend for testing..."
    docker build -t bmssp-backend-test ./backend
    
    # Run tests in container
    echo "Running unit tests..."
    docker run --rm \
        -v "$(pwd)/backend:/app" \
        -w /app \
        bmssp-backend-test \
        python -m pytest tests/ -v
    
    print_success "Tests completed"
}

run_benchmarks() {
    print_header "Running Benchmarks"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    echo "Starting services for benchmarking..."
    $COMPOSE_CMD up -d --wait
    
    echo "Running benchmark suite..."
    $COMPOSE_CMD --profile benchmarks up --build benchmarks
    
    echo "Collecting results..."
    mkdir -p ./benchmark-results
    docker cp "$(docker-compose ps -q benchmarks)":/app/results/ ./benchmark-results/ 2>/dev/null || true
    
    print_success "Benchmarks completed"
    echo "Results available in ./benchmark-results/"
}

clean_system() {
    print_header "Cleaning System"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    echo "Stopping and removing containers..."
    $COMPOSE_CMD down -v --remove-orphans
    
    echo "Removing images..."
    docker image prune -f
    
    echo "Removing volumes..."
    docker volume prune -f
    
    print_success "System cleaned"
}

dev_mode() {
    print_header "Development Mode"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # Start with hot reload and debug logging
    COMPOSE_FILE=docker-compose.yml $COMPOSE_CMD up --build
}

# Main script logic
main() {
    # Check if no arguments provided
    if [ $# -eq 0 ]; then
        check_dependencies
        start_services
        exit 0
    fi
    
    case "$1" in
        start)
            check_dependencies
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            check_dependencies
            restart_services
            ;;
        build)
            check_dependencies
            build_images
            ;;
        logs)
            show_logs "$2"
            ;;
        logs-backend)
            show_logs "backend"
            ;;
        logs-frontend)
            show_logs "frontend"
            ;;
        status)
            show_status
            ;;
        test)
            check_dependencies
            run_tests
            ;;
        benchmark)
            check_dependencies
            run_benchmarks
            ;;
        clean)
            clean_system
            ;;
        dev)
            check_dependencies
            dev_mode
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"