#!/usr/bin/env bash

#############################################################################
# Hybrid AI Stack - Installation Script
#
# This script sets up all dependencies for the Hybrid AI Stack system
# with proper error handling, idempotency, and colored progress indicators
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Progress indicator
show_progress() {
    local message=$1
    echo -e "${YELLOW}[ó]${NC} $message..."
}

#############################################################################
# Safety Checks
#############################################################################

# Check if running as root (NOT ALLOWED)
if [ "$EUID" -eq 0 ]; then
    log_error "This script should NOT be run as root"
    log_error "Please run as a regular user: ./install.sh"
    exit 1
fi

# Check sudo availability upfront
if ! sudo -n true 2>/dev/null; then
    log_info "This script requires sudo access for package installation"
    sudo -v || {
        log_error "Sudo access required but not available"
        exit 1
    }
fi

log_success "Sudo access verified"

# Keep sudo alive during installation
keep_sudo_alive() {
    while true; do
        sudo -n true
        sleep 60
        kill -0 "$$" || exit
    done 2>/dev/null &
}

keep_sudo_alive

#############################################################################
# System Detection
#############################################################################

log_info "Detecting system..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    log_error "Cannot detect operating system"
    exit 1
fi

log_success "Detected: $PRETTY_NAME"

if [[ "$OS" != "ubuntu" ]] && [[ "$OS" != "debian" ]]; then
    log_warning "This script is optimized for Ubuntu/Debian"
    log_warning "It may work on other systems but is not tested"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

#############################################################################
# Package Installation Functions
#############################################################################

check_command() {
    command -v "$1" >/dev/null 2>&1
}

install_package() {
    local package=$1
    local check_cmd=${2:-$1}

    if check_command "$check_cmd"; then
        log_success "$package already installed"
        return 0
    fi

    show_progress "Installing $package"
    sudo apt-get install -y "$package" >/dev/null 2>&1

    if check_command "$check_cmd"; then
        log_success "$package installed successfully"
        return 0
    else
        log_error "Failed to install $package"
        return 1
    fi
}

#############################################################################
# Main Installation Process
#############################################################################

log_info "Starting Hybrid AI Stack installation..."
echo

# Update package list
show_progress "Updating package list"
sudo apt-get update -qq
log_success "Package list updated"

# Install basic dependencies
log_info "Installing system dependencies..."

install_package "curl" "curl"
install_package "git" "git"
install_package "python3" "python3"
install_package "python3-pip" "pip3"
install_package "python3-venv" "python3"
install_package "docker.io" "docker"
install_package "docker-compose" "docker-compose"
install_package "task" "task"  # Taskwarrior

# Add user to docker group if not already
if ! groups | grep -q docker; then
    show_progress "Adding user to docker group"
    sudo usermod -aG docker "$USER"
    log_success "Added $USER to docker group"
    log_warning "You may need to log out and back in for docker group changes to take effect"
else
    log_success "User already in docker group"
fi

# Install Ollama
if check_command "ollama"; then
    log_success "Ollama already installed"
else
    show_progress "Installing Ollama"
    curl -fsSL https://ollama.com/install.sh | sh >/dev/null 2>&1
    if check_command "ollama"; then
        log_success "Ollama installed successfully"
    else
        log_error "Failed to install Ollama"
        exit 1
    fi
fi

#############################################################################
# Project Setup
#############################################################################

log_info "Setting up project..."

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        show_progress "Creating .env from .env.example"
        cp .env.example .env
        log_success ".env file created"
        log_warning "Please edit .env and add your API keys"
    else
        log_error ".env.example not found"
        exit 1
    fi
else
    log_success ".env file already exists"
fi

# Create Python virtual environment
if [ ! -d "venv" ]; then
    show_progress "Creating Python virtual environment"
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_success "Virtual environment already exists"
fi

# Activate venv and install Python dependencies
show_progress "Installing Python dependencies"
source venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt >/dev/null 2>&1
log_success "Python dependencies installed"

#############################################################################
# Taskwarrior Setup
#############################################################################

log_info "Initializing Taskwarrior..."

if [ ! -d "$HOME/.task" ]; then
    task rc.confirmation=off add "Hybrid AI Stack - Installation" project:vps_ai.tier2.setup +setup >/dev/null 2>&1
    task 1 done >/dev/null 2>&1
    log_success "Taskwarrior initialized with project structure"
else
    log_success "Taskwarrior already initialized"
fi

#############################################################################
# Directory Verification
#############################################################################

log_info "Verifying directory structure..."

REQUIRED_DIRS=(
    "scripts"
    "gateway"
    "configs"
    "terraform/aws"
    "terraform/gcp"
    "ansible"
    "workflows"
    "prompts"
    "tests"
    "docs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        log_success "Directory exists: $dir"
    else
        log_warning "Directory missing: $dir"
    fi
done

#############################################################################
# Service Status Check
#############################################################################

log_info "Checking service status..."

# Check Docker
if systemctl is-active --quiet docker; then
    log_success "Docker service is running"
else
    show_progress "Starting Docker service"
    sudo systemctl start docker
    sudo systemctl enable docker >/dev/null 2>&1
    log_success "Docker service started"
fi

# Check if Ollama can run
if check_command "ollama"; then
    if ollama list >/dev/null 2>&1; then
        log_success "Ollama is functional"
    else
        log_warning "Ollama installed but may need configuration"
    fi
fi

#############################################################################
# Installation Summary
#############################################################################

echo
echo -e "${GREEN}PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP${NC}"
echo -e "${GREEN}  Hybrid AI Stack Installation Complete!${NC}"
echo -e "${GREEN}PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP${NC}"
echo
log_info "Next steps:"
echo "  1. Edit .env and add your API keys:"
echo "     - ANTHROPIC_API_KEY=your-key-here"
echo "     - OPENAI_API_KEY=your-key-here (optional)"
echo
echo "  2. Start the stack:"
echo "     docker-compose --profile cpu up -d"
echo
echo "  3. Test the API Gateway:"
echo "     curl http://localhost:8080/health"
echo
echo "  4. Access services:"
echo "     - n8n:       http://localhost:5678"
echo "     - Grafana:   http://localhost:3000 (admin/admin)"
echo "     - Prometheus: http://localhost:9090"
echo
log_warning "If you were added to the docker group, log out and back in"
echo

# Create installation completion task
task add "Hybrid AI Stack - Installation Complete" project:vps_ai.tier2.setup +complete done:now >/dev/null 2>&1

deactivate 2>/dev/null || true
exit 0
