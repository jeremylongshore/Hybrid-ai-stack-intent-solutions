#!/usr/bin/env bash

#############################################################################
# Hybrid AI Stack - One-Command Deployment
#
# Usage:
#   ./deploy-all.sh [deployment-type] [tier]
#
# Examples:
#   ./deploy-all.sh docker           # Local Docker deployment
#   ./deploy-all.sh aws 2            # AWS Tier 2 (Standard)
#   ./deploy-all.sh gcp 3            # GCP Tier 3 (Performance)
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[ ]${NC} $1"
}

log_error() {
    echo -e "${RED}[]${NC} $1"
}

show_progress() {
    echo -e "${YELLOW}[ó]${NC} $1..."
}

# Banner
show_banner() {
    echo -e "${CYAN}"
    echo "TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW"
    echo "Q                  Hybrid AI Stack Deployment                   Q"
    echo "Q            Intelligent AI Request Routing System              Q"
    echo "ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]"
    echo -e "${NC}"
}

# Help message
show_help() {
    cat << EOF
Usage: ./deploy-all.sh [DEPLOYMENT_TYPE] [TIER]

Deployment Types:
  docker          Deploy locally with Docker Compose
  aws             Deploy to AWS with Terraform
  gcp             Deploy to GCP with Terraform

Tiers (for cloud deployments):
  1               Budget (2GB RAM, 1 CPU)     - Cloud only
  2               Standard (4-8GB RAM)        - Local + Cloud (DEFAULT)
  3               Performance (16GB RAM)       - Mostly local
  4               GPU (GPU instance)          - 95% local

Examples:
  ./deploy-all.sh docker                    # Local development
  ./deploy-all.sh aws 2                     # AWS Tier 2
  ./deploy-all.sh gcp 3                     # GCP Tier 3

EOF
}

#############################################################################
# Validation
#############################################################################

DEPLOYMENT_TYPE=${1:-docker}
TIER=${2:-2}

if [[ "$DEPLOYMENT_TYPE" == "-h" ]] || [[ "$DEPLOYMENT_TYPE" == "--help" ]]; then
    show_banner
    show_help
    exit 0
fi

# Validate deployment type
if [[ "$DEPLOYMENT_TYPE" != "docker" ]] && [[ "$DEPLOYMENT_TYPE" != "aws" ]] && [[ "$DEPLOYMENT_TYPE" != "gcp" ]]; then
    log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
    echo
    show_help
    exit 1
fi

# Validate tier
if ! [[ "$TIER" =~ ^[1-4]$ ]]; then
    log_error "Invalid tier: $TIER (must be 1, 2, 3, or 4)"
    exit 1
fi

show_banner

log_info "Deployment Type: $DEPLOYMENT_TYPE"
log_info "Tier: $TIER"
echo

#############################################################################
# Taskwarrior Tracking
#############################################################################

DEPLOY_TASK_ID=""

if command -v task >/dev/null 2>&1; then
    log_info "Creating Taskwarrior tracking task..."
    DEPLOY_TASK_ID=$(task add "Deploy Hybrid AI Stack - $DEPLOYMENT_TYPE Tier $TIER" \
        project:vps_ai.tier${TIER}.deployment +deployment rc.verbose=nothing 2>/dev/null | \
        grep -oP 'Created task \K\d+' || echo "")

    if [ -n "$DEPLOY_TASK_ID" ]; then
        task $DEPLOY_TASK_ID start rc.verbose=nothing 2>/dev/null || true
        log_success "Taskwarrior task #$DEPLOY_TASK_ID created"
    fi
fi

#############################################################################
# Environment Check
#############################################################################

show_progress "Checking environment"

if [ ! -f .env ]; then
    log_error ".env file not found"
    log_error "Please run ./install.sh first or copy .env.example to .env"
    exit 1
fi

# Source .env for cloud deployments
if [[ "$DEPLOYMENT_TYPE" != "docker" ]]; then
    source .env

    # Check for required cloud credentials
    if [[ "$DEPLOYMENT_TYPE" == "aws" ]]; then
        if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
            log_error "AWS credentials not found in .env"
            log_error "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
            exit 1
        fi
    fi

    if [[ "$DEPLOYMENT_TYPE" == "gcp" ]]; then
        if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
            log_warning "GOOGLE_APPLICATION_CREDENTIALS not set"
            log_info "Assuming gcloud CLI is configured"
        fi
    fi
fi

log_success "Environment check passed"

#############################################################################
# Docker Deployment
#############################################################################

deploy_docker() {
    log_info "Starting Docker deployment..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running"
        log_error "Please start Docker and try again"
        exit 1
    fi

    # Pull models based on tier
    log_info "Pulling Ollama models (this may take a few minutes)..."

    # Start Ollama service first
    docker-compose --profile cpu up -d ollama-cpu
    sleep 5

    # Pull models
    if [ "$TIER" -le 2 ]; then
        show_progress "Pulling TinyLlama and Phi-2"
        docker exec ollama ollama pull tinyllama || true
        docker exec ollama ollama pull phi || true
    else
        show_progress "Pulling Mistral-7B"
        docker exec ollama ollama pull mistral || true
    fi

    log_success "Models pulled successfully"

    # Start all services
    show_progress "Starting all services with Docker Compose"
    docker-compose --profile cpu up -d

    log_success "All services started"

    # Wait for services to be healthy
    show_progress "Waiting for services to be ready (30s)"
    sleep 30

    # Health checks
    check_docker_health
}

check_docker_health() {
    log_info "Running health checks..."

    local all_healthy=true

    # Check n8n
    if curl -sf http://localhost:5678 >/dev/null 2>&1; then
        log_success "n8n is healthy (http://localhost:5678)"
    else
        log_warning "n8n is not responding"
        all_healthy=false
    fi

    # Check API Gateway
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
        log_success "API Gateway is healthy (http://localhost:8080)"
    else
        log_warning "API Gateway is not responding"
        all_healthy=false
    fi

    # Check Prometheus
    if curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then
        log_success "Prometheus is healthy (http://localhost:9090)"
    else
        log_warning "Prometheus is not responding"
        all_healthy=false
    fi

    # Check Grafana
    if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
        log_success "Grafana is healthy (http://localhost:3000)"
    else
        log_warning "Grafana is not responding"
        all_healthy=false
    fi

    if [ "$all_healthy" = false ]; then
        log_warning "Some services are not healthy - check logs with: docker-compose logs"
    fi
}

#############################################################################
# Cloud Deployment (Terraform)
#############################################################################

deploy_cloud() {
    local provider=$1

    log_info "Starting $provider deployment with Terraform..."

    cd terraform/$provider || {
        log_error "Terraform configuration not found for $provider"
        exit 1
    }

    # Initialize Terraform
    show_progress "Initializing Terraform"
    terraform init
    log_success "Terraform initialized"

    # Plan
    show_progress "Creating Terraform plan"
    terraform plan -var="tier=$TIER" -out=tfplan
    log_success "Terraform plan created"

    # Apply
    log_warning "About to create cloud resources - this will incur costs"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        cd ../..
        exit 0
    fi

    show_progress "Applying Terraform configuration"
    terraform apply tfplan
    log_success "Cloud resources created"

    # Get outputs
    INSTANCE_IP=$(terraform output -raw instance_ip 2>/dev/null || echo "")

    cd ../..

    if [ -n "$INSTANCE_IP" ]; then
        log_success "Instance deployed at: $INSTANCE_IP"

        # Wait for instance to be ready
        show_progress "Waiting for instance to boot (60s)"
        sleep 60

        # Run Ansible playbook if available
        if [ -f ansible/deploy.yml ]; then
            log_info "Running Ansible playbook..."
            ansible-playbook -i "${INSTANCE_IP}," ansible/deploy.yml
            log_success "Ansible deployment complete"
        fi
    fi
}

#############################################################################
# Main Deployment Logic
#############################################################################

case $DEPLOYMENT_TYPE in
    docker)
        deploy_docker
        ;;
    aws|gcp)
        deploy_cloud $DEPLOYMENT_TYPE
        ;;
esac

#############################################################################
# Display Access Information
#############################################################################

echo
echo -e "${GREEN}PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP${NC}"
echo

if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
    cat << EOF
<‰ Your Hybrid AI Stack is now running!

=Ê Access URLs:
   " API Gateway:  http://localhost:8080
   " n8n:         http://localhost:5678
   " Grafana:     http://localhost:3000 (admin/admin)
   " Prometheus:  http://localhost:9090

>ê Test the API:
   curl -X POST http://localhost:8080/api/v1/chat \\
     -H "Content-Type: application/json" \\
     -d '{"prompt": "What is Python?"}'

=È Check stats:
   curl http://localhost:8080/api/v1/stats

=Ñ Stop services:
   docker-compose down

=Ë View logs:
   docker-compose logs -f [service-name]

EOF
else
    cat << EOF
<‰ Your Hybrid AI Stack is deployed to $DEPLOYMENT_TYPE!

= Instance IP: $INSTANCE_IP

=Ý Next steps:
   1. SSH to instance: ssh ubuntu@$INSTANCE_IP
   2. Check services: docker-compose ps
   3. View logs: docker-compose logs -f

= Security:
   " Configure firewall rules in $DEPLOYMENT_TYPE console
   " Set up SSL/TLS certificates
   " Review security groups

EOF
fi

#############################################################################
# Complete Taskwarrior Task
#############################################################################

if [ -n "$DEPLOY_TASK_ID" ]; then
    task $DEPLOY_TASK_ID done rc.verbose=nothing 2>/dev/null || true
    task $DEPLOY_TASK_ID annotate "Deployed: $DEPLOYMENT_TYPE Tier $TIER" rc.verbose=nothing 2>/dev/null || true
    log_success "Taskwarrior task #$DEPLOY_TASK_ID completed"
fi

echo
log_success "Deployment complete! =€"
