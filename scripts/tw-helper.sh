#!/usr/bin/env bash

#############################################################################
# Taskwarrior Helper Functions
# Utility functions for managing Hybrid AI Stack tasks in Taskwarrior
#############################################################################

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

#############################################################################
# Helper Functions
#############################################################################

# Start a task and add annotation with timestamp
tw_start() {
    local task_id=$1
    local annotation=${2:-"Started"}

    if [ -z "$task_id" ]; then
        echo "Usage: tw_start <task_id> [annotation]"
        return 1
    fi

    task $task_id start rc.verbose=nothing 2>/dev/null
    task $task_id annotate "$(date '+%Y-%m-%d %H:%M:%S') - $annotation" rc.verbose=nothing 2>/dev/null

    echo -e "${GREEN}${NC} Task $task_id started: $annotation"
}

# Complete a task with annotation
tw_complete() {
    local task_id=$1
    local annotation=${2:-"Completed"}

    if [ -z "$task_id" ]; then
        echo "Usage: tw_complete <task_id> [annotation]"
        return 1
    fi

    task $task_id annotate "$(date '+%Y-%m-%d %H:%M:%S') - $annotation" rc.verbose=nothing 2>/dev/null
    task $task_id done rc.verbose=nothing 2>/dev/null

    echo -e "${GREEN}${NC} Task $task_id completed: $annotation"
}

# Create a dependency chain of tasks
tw_chain() {
    local project=$1
    shift
    local tasks=("$@")

    if [ ${#tasks[@]} -lt 2 ]; then
        echo "Usage: tw_chain <project> <task1> <task2> [task3...]"
        echo "Example: tw_chain vps_ai.tier2 'Install Docker' 'Pull models' 'Start services'"
        return 1
    fi

    echo -e "${BLUE}Creating task chain in project: $project${NC}"

    local prev_id=""
    for task_desc in "${tasks[@]}"; do
        if [ -z "$prev_id" ]; then
            # First task
            prev_id=$(task add "$task_desc" project:$project rc.verbose=nothing 2>/dev/null | grep -oP 'Created task \K\d+')
            echo -e "  ${GREEN}’${NC} Created task $prev_id: $task_desc"
        else
            # Subsequent tasks depend on previous
            local new_id=$(task add "$task_desc" project:$project depends:$prev_id rc.verbose=nothing 2>/dev/null | grep -oP 'Created task \K\d+')
            echo -e "  ${GREEN}’${NC} Created task $new_id: $task_desc (depends on $prev_id)"
            prev_id=$new_id
        fi
    done

    echo -e "${GREEN}${NC} Created chain of ${#tasks[@]} tasks"
}

# Annotate with system information
tw_annotate_system() {
    local task_id=$1

    if [ -z "$task_id" ]; then
        echo "Usage: tw_annotate_system <task_id>"
        return 1
    fi

    # Get system info
    local hostname=$(hostname)
    local os=$(cat /etc/os-release | grep "^PRETTY_NAME" | cut -d= -f2 | tr -d '"')
    local ram=$(free -h | awk '/^Mem:/ {print $2}')
    local cpu=$(nproc)

    task $task_id annotate "System: $hostname | $os | RAM: $ram | CPUs: $cpu" rc.verbose=nothing 2>/dev/null

    echo -e "${GREEN}${NC} Added system info to task $task_id"
}

# Create project structure for a new deployment
tw_init_deployment() {
    local tier=${1:-2}
    local deployment_type=${2:-docker}

    echo -e "${BLUE}Initializing Taskwarrior project structure for Tier $tier ($deployment_type)${NC}"

    # Create main project tasks
    local tasks=(
        "Setup: Install dependencies:vps_ai.tier${tier}.setup:+setup"
        "Setup: Configure environment:vps_ai.tier${tier}.setup:+setup"
        "Setup: Pull models:vps_ai.tier${tier}.setup:+setup"
        "Deploy: Start services:vps_ai.tier${tier}.deployment:+deploy"
        "Deploy: Health checks:vps_ai.tier${tier}.deployment:+deploy"
        "Deploy: Verify routing:vps_ai.tier${tier}.deployment:+deploy"
        "Monitor: Track costs:vps_ai.tier${tier}.monitoring:+monitor"
        "Monitor: Check performance:vps_ai.tier${tier}.monitoring:+monitor"
    )

    for task_entry in "${tasks[@]}"; do
        IFS=: read -r desc project tags <<< "$task_entry"
        task add "$desc" project:$project $tags rc.verbose=nothing 2>/dev/null
        echo -e "  ${GREEN}’${NC} Created: $desc"
    done

    echo -e "${GREEN}${NC} Deployment project structure initialized"
}

# Show routing statistics from Taskwarrior
tw_routing_stats() {
    echo -e "${BLUE}Routing Statistics (from Taskwarrior)${NC}"
    echo

    local total=$(task project:vps_ai.router count 2>/dev/null || echo "0")
    local tinyllama=$(task project:vps_ai.router /tinyllama/ count 2>/dev/null || echo "0")
    local phi2=$(task project:vps_ai.router /phi/ count 2>/dev/null || echo "0")
    local claude=$(task project:vps_ai.router /claude/ count 2>/dev/null || echo "0")

    echo "  Total requests: $total"
    echo "  TinyLlama (local): $tinyllama"
    echo "  Phi-2 (local): $phi2"
    echo "  Claude (cloud): $claude"
    echo

    if [ "$total" -gt 0 ]; then
        local local_count=$((tinyllama + phi2))
        local local_pct=$((local_count * 100 / total))
        echo -e "  ${GREEN}Local requests:${NC} $local_pct%"
    fi
}

# Create a cost tracking task
tw_track_cost() {
    local amount=$1
    local model=$2
    local description=${3:-"API request"}

    if [ -z "$amount" ] || [ -z "$model" ]; then
        echo "Usage: tw_track_cost <amount> <model> [description]"
        echo "Example: tw_track_cost 0.015 claude-sonnet 'Complex code generation'"
        return 1
    fi

    task add "$description" \
        project:vps_ai.costs \
        +cost \
        "model:$model" \
        "amount:$amount" \
        done:now \
        rc.verbose=nothing 2>/dev/null

    echo -e "${GREEN}${NC} Tracked cost: \$$amount for $model"
}

# Show total costs from Taskwarrior
tw_cost_report() {
    local period=${1:-"week"}

    echo -e "${BLUE}Cost Report ($period)${NC}"
    echo

    # This would need jq to parse JSON properly
    # For now, showing simple counts
    local total_tasks=$(task project:vps_ai.costs count 2>/dev/null || echo "0")

    echo "  Total cost tracking tasks: $total_tasks"
    echo "  (Install jq for detailed cost breakdowns)"

    # If jq is available, show detailed breakdown
    if command -v jq >/dev/null 2>&1; then
        echo
        echo "  Breakdown by model:"
        task project:vps_ai.costs export 2>/dev/null | \
            jq -r '.[] | select(.tags[]? == "cost") | .description' | \
            sort | uniq -c | sort -rn
    fi
}

# Bulk update - mark all setup tasks as done
tw_complete_setup() {
    local tier=${1:-2}

    echo -e "${YELLOW}Marking all setup tasks as complete for Tier $tier${NC}"

    task project:vps_ai.tier${tier}.setup status:pending rc.verbose=nothing done 2>/dev/null

    echo -e "${GREEN}${NC} All setup tasks completed"
}

# List active deployment tasks
tw_deployment_status() {
    local tier=${1:-2}

    echo -e "${BLUE}Deployment Status - Tier $tier${NC}"
    echo

    task project:vps_ai.tier${tier} status:pending rc.verbose=nothing
}

# Quick task creation with smart project detection
tw_quick_add() {
    local description=$1

    if [ -z "$description" ]; then
        echo "Usage: tw_quick_add <description>"
        return 1
    fi

    # Auto-detect project based on keywords
    local project="vps_ai"
    local tags=""

    if [[ "$description" =~ (deploy|start|launch) ]]; then
        project="vps_ai.deployment"
        tags="+deploy"
    elif [[ "$description" =~ (install|setup|config) ]]; then
        project="vps_ai.setup"
        tags="+setup"
    elif [[ "$description" =~ (monitor|check|health) ]]; then
        project="vps_ai.monitoring"
        tags="+monitor"
    elif [[ "$description" =~ (route|request|model) ]]; then
        project="vps_ai.router"
        tags="+routing"
    fi

    local task_id=$(task add "$description" project:$project $tags rc.verbose=nothing 2>/dev/null | grep -oP 'Created task \K\d+')

    echo -e "${GREEN}${NC} Created task $task_id in $project: $description"
}

#############################################################################
# Usage Examples
#############################################################################

tw_help() {
    cat << 'EOF'
Taskwarrior Helper Functions for Hybrid AI Stack

Usage:
  source scripts/tw-helper.sh

Functions:
  tw_start <id> [note]          - Start task with timestamp annotation
  tw_complete <id> [note]       - Complete task with annotation
  tw_chain <project> <t1> <t2>  - Create dependency chain
  tw_annotate_system <id>       - Add system info to task
  tw_init_deployment [tier]     - Initialize deployment project
  tw_routing_stats              - Show routing statistics
  tw_track_cost <amt> <model>   - Track API cost
  tw_cost_report [period]       - Show cost report
  tw_complete_setup [tier]      - Mark all setup tasks done
  tw_deployment_status [tier]   - Show deployment status
  tw_quick_add <description>    - Quick task creation with auto-detection
  tw_help                       - Show this help

Examples:
  # Start and complete tasks
  tw_start 42 "Beginning deployment"
  tw_complete 42 "Deployment successful"

  # Create task chain
  tw_chain vps_ai.tier2 "Pull models" "Start Docker" "Test API"

  # Track costs
  tw_track_cost 0.015 claude-sonnet "Complex analysis"
  tw_cost_report week

  # Quick deployment setup
  tw_init_deployment 2 docker
  tw_deployment_status 2

Project Structure:
  vps_ai.tier{1,2,3,4}
     .setup        - Installation tasks
     .deployment   - Deployment tasks
     .monitoring   - Monitoring tasks
     .router       - Routing decisions
     .costs        - Cost tracking

EOF
}

# If sourced, show help
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    tw_help
fi
