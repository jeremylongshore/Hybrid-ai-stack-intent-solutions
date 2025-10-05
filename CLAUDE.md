# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**Hybrid AI Stack** is a production-ready AI orchestration system that intelligently routes requests between local CPU-based models and cloud APIs to achieve 60-80% cost reduction. The system uses multi-factor complexity estimation to automatically select the optimal model for each request.

**Repository**: https://github.com/jeremylongshore/Hybrid-ai-stack-intent-solutions

## Project Purpose

Reduce AI API costs through intelligent routing:
- **Simple queries** (complexity < 0.3) → TinyLlama (local, free)
- **Medium queries** (0.3 - 0.6) → Phi-2 (local, free)
- **Complex queries** (> 0.6) → Claude Sonnet (cloud, paid)

This achieves **60-80% cost reduction** vs. cloud-only approaches while maintaining quality.

## System Architecture

### Core Components

```
User Request
     ↓
API Gateway (Flask + Gunicorn) :8080
     ↓
Smart Router (scripts/smart_router.py)
     ↓
├── TinyLlama (Ollama, local, free)
├── Phi-2 (Ollama, local, free)
└── Claude Sonnet (Anthropic API, paid)
```

### Technology Stack

**Backend**:
- Python 3.11+
- Flask 3.1 (API Gateway)
- Anthropic SDK (Claude API)
- Ollama (local model serving)

**Infrastructure**:
- Docker Compose (8 services)
- Terraform (AWS/GCP deployment)
- Prometheus + Grafana (monitoring)
- n8n (workflow automation)
- Taskwarrior (task tracking)

**Models**:
- TinyLlama 1.1B (700MB RAM, simple queries)
- Phi-2 2.7B (1.6GB RAM, medium queries)
- Mistral-7B (4GB RAM, optional, high-quality)
- Claude Sonnet 4 (cloud API, complex queries)

## Directory Structure

```
hybrid-ai-stack/
├── scripts/
│   ├── smart_router.py           # Core routing logic (CRITICAL)
│   ├── moderation_pipeline.py    # Example: content moderation
│   ├── support_router.py         # Example: customer support
│   └── tw-helper.sh              # Taskwarrior helper functions
├── gateway/
│   ├── app.py                    # Flask API Gateway
│   ├── Dockerfile                # Gateway container
│   └── requirements.txt          # Gateway dependencies
├── terraform/
│   ├── aws/                      # AWS Terraform configs
│   │   ├── main.tf               # EC2 instances, security groups
│   │   ├── variables.tf          # Tier configurations
│   │   └── outputs.tf            # SSH commands, IPs
│   └── gcp/                      # GCP Terraform configs
├── workflows/                     # n8n workflow definitions
│   ├── smart_routing.json        # Automated routing workflow
│   ├── cost_monitor.json         # Cost alerting
│   ├── performance_monitor.json  # Performance reports
│   └── orchestrator_pipeline.json # Multi-stage orchestration
├── docs/                          # GitHub Pages documentation
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   ├── VPS-TIERS.md
│   ├── DEPLOYMENT.md
│   ├── SMART-ROUTER.md
│   ├── COST-OPTIMIZATION.md
│   ├── MONITORING.md
│   ├── TROUBLESHOOTING.md
│   ├── EXAMPLES.md
│   ├── N8N-WORKFLOWS.md
│   └── TASKWARRIOR.md
├── configs/                       # Service configurations
│   ├── prometheus.yml
│   └── grafana-datasources.yml
├── tests/
│   └── test_router.py            # Pytest test suite
├── docker-compose.yml            # Complete stack definition
├── install.sh                    # One-command installation
├── deploy-all.sh                 # One-command deployment
├── .env.example                  # Environment template
└── requirements.txt              # Python dependencies
```

## Key Files & Their Purposes

### Critical Files (DO NOT MODIFY WITHOUT UNDERSTANDING)

**`scripts/smart_router.py`** (375 lines)
- Core intelligent routing logic
- Multi-factor complexity estimation:
  - Length analysis (30% weight)
  - Keyword detection (30% weight)
  - Code presence (25% weight)
  - Task type classification (15% weight)
- Model selection algorithm
- Ollama integration for local models
- Claude API integration
- Taskwarrior logging
- Cost tracking

**`gateway/app.py`** (230 lines)
- Flask API Gateway
- Endpoints:
  - `POST /api/v1/chat` - Main chat with auto-routing
  - `POST /api/v1/complexity` - Complexity estimation only
  - `GET /api/v1/stats` - Routing statistics
  - `GET /health` - Health check
  - `GET /metrics` - Prometheus metrics
- Prometheus metrics export
- Error handling and logging

**`docker-compose.yml`** (Complete stack)
- 8 services: api-gateway, ollama-cpu, n8n, prometheus, grafana, redis, qdrant, postgres
- CPU and GPU profiles
- Volume mounts and networks
- Auto-pulls TinyLlama and Phi models on startup

### Deployment Scripts

**`install.sh`** (314 lines)
- NEVER runs as root (explicit check)
- Sudo keep-alive for long operations
- Idempotent package installation
- Docker, Ollama, Python setup
- Creates virtual environment
- Initializes Taskwarrior
- Creates .env from .env.example

**`deploy-all.sh`** (392 lines)
- One-command deployment for docker/aws/gcp
- Tier validation (1-4)
- Taskwarrior task creation
- Health checks
- Cost warnings for cloud deployments

### Configuration Files

**`.env.example`**
- Required: `ANTHROPIC_API_KEY`
- Optional: `OPENAI_API_KEY`
- Ollama URL, complexity thresholds
- Deployment tier and cloud provider

**`configs/prometheus.yml`**
- Scrapes API Gateway metrics every 15s
- Monitors Ollama health every 30s
- Alert rules for high costs, errors, slow responses

## Development Workflow

### Local Development

```bash
# 1. Install
./install.sh

# 2. Configure
nano .env  # Add ANTHROPIC_API_KEY

# 3. Deploy locally
./deploy-all.sh docker

# 4. Test
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Python?"}'

# 5. View logs
docker-compose logs -f api-gateway

# 6. Run tests
source venv/bin/activate
pytest tests/
```

### Cloud Deployment

```bash
# AWS Tier 2 (Standard: 4GB RAM, 2 CPU, $52/mo)
./deploy-all.sh aws 2

# GCP Tier 3 (Performance: 8GB RAM, 4 CPU, $120/mo)
./deploy-all.sh gcp 3
```

## Common Development Tasks

### Modify Routing Logic

Edit `scripts/smart_router.py`:

```python
# Change complexity thresholds
COMPLEXITY_THRESHOLD_TINY = 0.3  # Default
COMPLEXITY_THRESHOLD_PHI = 0.6   # Default

# Adjust factor weights
complexity = (
    factors['length'] * 0.3 +      # 30%
    factors['keywords'] * 0.3 +    # 30%
    factors['code'] * 0.25 +       # 25%
    factors['task_type'] * 0.15    # 15%
)
```

### Add New Endpoint

Edit `gateway/app.py`:

```python
@app.route('/api/v1/your-endpoint', methods=['POST'])
def your_endpoint():
    # Your logic here
    return jsonify({'result': 'success'}), 200
```

### Add Custom Workflow

Create JSON file in `workflows/`:
- Use n8n UI to design workflow
- Export as JSON
- Place in `workflows/` directory
- Import via n8n UI at http://localhost:5678

### Modify Terraform Deployment

Edit `terraform/aws/main.tf` or `terraform/gcp/main.tf`:
- Instance types defined in `variables.tf`
- User data scripts install system on boot
- Security groups configured for required ports

## Testing

### Run Test Suite

```bash
source venv/bin/activate
pytest tests/ -v

# With coverage
pytest --cov=scripts tests/

# Test routing logic
python tests/test_router.py
```

### Test Specific Components

```bash
# Test complexity estimation
python -c "
from scripts.smart_router import SmartRouter
router = SmartRouter()
complexity, reasoning = router.estimate_complexity('What is Python?')
print(f'Complexity: {complexity}, Reasoning: {reasoning}')
"

# Test Ollama connection
curl http://localhost:11434/api/generate \
  -d '{"model": "tinyllama", "prompt": "test", "stream": false}'

# Test Claude routing
curl -X POST http://localhost:8080/api/v1/chat \
  -d '{"prompt": "Write a complex algorithm"}' -H "Content-Type: application/json"
```

## Monitoring & Observability

### Prometheus Metrics

Key metrics exported by API Gateway:
- `api_gateway_requests_total{model, backend, status}` - Total requests
- `api_gateway_request_duration_seconds{model, backend}` - Latency
- `api_gateway_cost_total{model}` - Cumulative costs

Access: http://localhost:9090

### Grafana Dashboards

Pre-configured dashboards:
- Request distribution (local vs cloud)
- Cost tracking and trends
- Latency heatmaps
- Model performance

Access: http://localhost:3000 (admin/admin)

### Taskwarrior Tracking

Every AI request creates a task:
```bash
# View routing tasks
task project:vps_ai.router list

# Cost report
source scripts/tw-helper.sh
tw_cost_report

# Routing statistics
tw_routing_stats
```

## Cost Optimization

### Current Strategy

- **Simple queries** (40-50% of traffic) → TinyLlama → $0
- **Medium queries** (20-30% of traffic) → Phi-2 → $0
- **Complex queries** (20-30% of traffic) → Claude → $0.003-0.015 each

**Result**: 60-80% cost reduction vs. cloud-only

### Optimization Opportunities

1. **Adjust thresholds** - Make routing more aggressive (more local, less cloud)
2. **Cache responses** - Redis caching for common queries
3. **Batch processing** - Group similar requests
4. **Model cascading** - Try local first, fallback to cloud if quality poor
5. **Time-based routing** - Use local during peak hours, cloud during off-peak

## VPS Tier Recommendations

| Tier | RAM | CPU | Cost/mo | Models | Local % | Savings |
|------|-----|-----|---------|--------|---------|---------|
| 1 | 2GB | 1 | $26 | TinyLlama | 30% | 30% |
| 2 | 4GB | 2 | $52 | TinyLlama + Phi-2 | 70% | 60-70% |
| 3 | 8GB | 4 | $120 | + Mistral-7B | 85% | 75-85% |
| 4 | 16GB+GPU | 8 | $310 | All + GPU | 95% | 85-95% |

**Recommended**: Tier 2 for most production use cases

## Potential Modifications

### Switch to Vertex AI (Instead of Claude)

If user has GCP access with startup credits:

1. Modify `scripts/smart_router.py`:
```python
def execute_vertex_ai_request(self, prompt):
    """Execute request on Vertex AI Gemini"""
    from google.cloud import aiplatform
    # Implementation here
```

2. Update `.env`:
```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
```

3. Benefits:
- Free during startup program
- Gemini 1.5 Flash is fast
- Gemini 1.5 Pro rivals Claude
- Better GCP ecosystem integration

### Add GPT-4 Support

Modify `scripts/smart_router.py`:
```python
def execute_openai_request(self, prompt):
    """Execute request on OpenAI GPT-4"""
    import openai
    # Implementation here
```

## Important Conventions

### Error Handling

All functions should:
- Return dict with `success`, `error`, `data` keys
- Log errors with context
- Never expose API keys in logs
- Gracefully degrade (use fallback model if primary fails)

### Logging

- Use Python `logging` module
- Log levels: DEBUG, INFO, WARNING, ERROR
- Include request ID for tracing
- Log costs and model selections

### Code Style

- Follow PEP 8
- Type hints where appropriate
- Docstrings for all functions
- Comments for complex logic
- 80-character line limit (flexible)

## Security Considerations

1. **API Keys**: Never commit to git, use `.env`
2. **Docker**: Containers run as non-root user
3. **Network**: Security groups limit access to required ports
4. **Secrets**: Use cloud provider secrets managers in production
5. **CORS**: Configure appropriately for your use case

## Deployment Checklist

Before deploying to production:

- [ ] API keys configured in `.env`
- [ ] Health checks passing: `curl http://localhost:8080/health`
- [ ] Models pulled: `docker exec ollama ollama list`
- [ ] Tests passing: `pytest tests/`
- [ ] Monitoring configured (Prometheus, Grafana)
- [ ] Backup strategy defined
- [ ] Scaling plan documented
- [ ] Cost alerts configured

## Support Resources

- **Documentation**: See `docs/` directory (12 comprehensive guides)
- **Examples**: See `scripts/moderation_pipeline.py` and `scripts/support_router.py`
- **Tests**: See `tests/test_router.py` for testing patterns
- **Workflows**: See `workflows/` for n8n automation examples

## Known Limitations

1. **Ollama CPU**: Slower than GPU (1-5s per request)
2. **Complexity Estimation**: Not perfect, requires tuning
3. **Model Quality**: Local models inferior to Claude for complex tasks
4. **Scaling**: Single-server setup (can be load-balanced)
5. **Context**: Local models have smaller context windows

## Future Enhancements

Potential improvements:
- [ ] Multi-model ensembles
- [ ] Active learning from user feedback
- [ ] A/B testing framework
- [ ] Cost prediction ML model
- [ ] Automatic threshold tuning
- [ ] Multi-language support
- [ ] Streaming responses
- [ ] WebSocket support

## Contact & Contribution

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Pull Requests**: Always welcome with tests

---

**Last Updated**: October 5, 2025
**Version**: 1.0.0
**Status**: Production-ready
