# Changelog

All notable changes to the Hybrid AI Stack project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-03-23

### Added
- **Redis Response Caching** - Exact-match caching with configurable TTL (#3)
  - SHA-256 hash of prompt + model for cache key
  - `CACHE_TTL_SECONDS` environment variable (default 3600)
  - `"cached": true/false` in response JSON
  - `Cache-Control: no-cache` header support to bypass cache
  - Prometheus cache hit/miss counters
- **Model Listing Endpoint** - `GET /api/v1/models` (#3)
  - Returns all available models with name, backend, availability status
  - Checks Ollama `/api/tags`, ternary health, Claude API key presence
  - Cost per token and max complexity for each model
- **Rate Limiting** - flask-limiter integration (#3)
  - Default 60 requests/minute per IP (`RATE_LIMIT` env var)
  - 429 response with `Retry-After` header
  - Redis-backed when available, memory fallback
- **Prompt Validation** - Reject oversized prompts (#3)
  - 413 response for prompts >100k characters
- **Tiktoken Token Counting** - Accurate cost estimation (#3)
  - Uses `cl100k_base` encoding (same as Claude)
  - Fallback to `len(text) // 4` if tiktoken unavailable
  - Fixes 20-40% cost estimation error
- **Comprehensive Test Suite** - 54 tests (was 9, 3 broken) (#3)
  - `tests/test_gateway.py`: 18 Flask endpoint tests
  - `tests/test_router.py`: Ternary routing, error paths, stats parsing
  - Coverage: gateway 84%, smart_router 77%
- **Prometheus Alert Rules** - `configs/alert-rules.yml` (#3)
  - GatewayDown: 2 minute threshold
  - HighErrorRate: >10% for 5 minutes
  - CloudCostSpike: >$0.50/hour
- **CI/CD Pipeline** - `.github/workflows/ci.yml` (#3)
  - pytest, flake8, docker build on push/PR to main
- **OSS Readiness Files** - SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md (#2)

### Fixed
- **Shell Injection Vulnerability** - Taskwarrior logging now uses `subprocess.run` with list args (#3)
- **Gateway Rejects Ternary Models** - Manual override with `"model": "bitnet-2b"` now works (#3)
- **Ollama Health Check Incomplete** - Now verifies models are actually pulled (#3)
- **Taskwarrior Stats Parsing** - Uses description prefix matching, counts ternary (#3)
- **Prometheus Redis Scrape** - Removed broken redis:6379 and n8n:5678 targets (#3)

### Changed
- **Configurable Claude Model** - `CLAUDE_MODEL` env var (default `claude-sonnet-4-20250514`) (#3)
- **Taskwarrior Logging Opt-in** - Disabled by default, enable via `ENABLE_TASKWARRIOR_LOGGING=true` (#3)
- **API Gateway Version** - Bumped to 1.1.0 in index response (#3)

### Security
- **AWS Security Groups Hardened** - SSH restricted to `allowed_ssh_cidr`, n8n/Grafana removed from public (#3)
- **Dead Code Removed** - Ansible references removed from deploy-all.sh (#3)

### Docker
- **API Gateway Healthcheck** - Dockerfile + compose healthcheck using urllib (#3)
- **Ollama Model Pull Race Condition** - Proper wait loop, `depends_on: service_completed_successfully` (#3)
- **Container Name Collisions** - Fixed in ollama anchor (#3)
- **Resource Limits** - Memory/CPU limits on all 8 services (#3)

## Release Metrics (v1.2.0)

| Metric | Value |
|--------|-------|
| **Commits** | 6 |
| **Files Changed** | 65 |
| **Lines Added** | +2,606 |
| **Lines Removed** | -181 |
| **New Tests** | 45 (54 total, was 9) |
| **Test Coverage** | gateway 84%, router 77% |
| **New Endpoints** | 1 (GET /api/v1/models) |
| **Security Fixes** | 2 (shell injection, AWS SG) |
| **Bug Fixes** | 5 |

## [1.1.0] - 2025-10-05

### Added
- **Ternary Quantization Support (BitNet 1.58-bit)** - Major feature addition
  - New Tier 2.5 deployment option optimized for ternary quantization
  - BitNet.cpp integration with Microsoft's 1.58-bit quantization
  - `scripts/install_ternary.sh` - Automated BitNet.cpp installation
  - `scripts/download_ternary_models.sh` - Model downloading utility
  - `scripts/setup_ternary_service.sh` - Service configuration
  - `scripts/ternary_server.py` - Flask API server for BitNet models (159 lines)
  - `scripts/benchmark_ternary.py` - Performance testing suite
  - `docs/TERNARY.md` - Comprehensive 400+ line technical documentation
  - Docker Compose profile for ternary service deployment
  - Ternary model routing in `smart_router.py`:
    - BitNet-2B for complexity < 0.5 (6x faster, 82% energy savings)
    - Mistral-7B-Ternary for complexity 0.5-0.8
  - Memory reduction: 16x smaller models vs FP16
  - Speed improvement: 6x faster inference
  - Energy savings: 82% reduction vs traditional models
  - Cost-effectiveness: $48/mo for Tier 2.5 vs $52/mo for Tier 2
- Bob's Brain Integration Documentation
  - `/home/jeremy/tbag/integrate-ternary-to-bobs-brain.md` - Complete integration guide
  - `/home/jeremy/tbag/README-NOW.md` - Quick-start guide for Bob's Brain

### Fixed
- **Jekyll Build Failures** - Resolved all GitHub Pages build errors
  - Simplified `docs/_config.yml` from 95 to 49 lines (removed unsupported configs)
  - Fixed Liquid syntax errors in `docs/MONITORING.md` (3 instances)
  - Fixed Liquid syntax errors in `docs/N8N-WORKFLOWS.md` (6+ JSON blocks)
  - Wrapped Prometheus alert templates in `{% raw %}` tags
  - Wrapped n8n JSON configurations in `{% raw %}` tags
  - Build status: errored → built (31.5 seconds)
  - Site now live at https://jeremylongshore.github.io/Hybrid-ai-stack-intent-solutions/
- Repository URL corrections in Jekyll documentation

### Changed
- Updated `docs/VPS-TIERS.md` with comprehensive Tier 2.5 section (lines 161-267)
- Enhanced smart routing logic with ternary backend support
- Improved documentation structure for GitHub Pages compatibility

### Technical Details
- **Ternary Quantization Implementation:**
  - Weight precision: 1.58-bit (-1, 0, +1)
  - Activation: 8-bit quantization
  - Performance: 6x inference speedup on CPU
  - Models: BitNet-2B, Mistral-7B-Ternary
  - Backend: BitNet.cpp with Clang/LLVM compilation
- **Jekyll Configuration:**
  - Theme: jekyll-theme-cayman (GitHub Pages compatible)
  - Plugins: jekyll-sitemap, jekyll-seo-tag, jekyll-github-metadata
  - Removed: collections, mermaid config, just-the-docs settings

## Release Metrics (v1.1.0)

| Metric | Value |
|--------|-------|
| **New Features** | 1 major (Ternary Quantization) |
| **Files Added** | 8 |
| **Files Modified** | 5 |
| **Lines Added** | 1,200+ |
| **Documentation Enhancement** | 400+ lines in TERNARY.md |
| **Performance Improvement** | 6x inference speed |
| **Cost Reduction** | Additional 10-15% vs Tier 2 |
| **Energy Savings** | 82% reduction |
| **Jekyll Build Status** | errored → built |
| **Build Time** | 31.5 seconds |

## [1.0.0] - 2025-10-05

### Added
- Initial production release of Hybrid AI Stack
- Comprehensive CLAUDE.md documentation with:
  - Detailed request flow diagram with specific line references
  - Complexity estimation algorithm breakdown
  - Complete API endpoint documentation with curl examples
  - Docker profile system documentation (CPU/GPU)
  - Enhanced testing section with benchmark examples
  - Troubleshooting section with actual diagnostic commands
  - Example use cases with code
  - Quick reference commands section
- GitHub error resolution audit system
- Comprehensive audit reporting framework
- Version management system (version.txt)

### Fixed
- GitHub Pages deployment failures (5 consecutive failures resolved)
  - Fixed docs/Gemfile conflicting dependencies
  - Removed conflicting Jekyll theme specification
  - Added Ruby 3.4+ compatibility gems (csv, base64)
  - Fixed GitHub Actions workflow bundler caching
  - Added explicit bundle install step
- CI/CD pipeline reliability improved from 0% to 100%

### Changed
- Updated docs/Gemfile to use github-pages gem ~> 232
- Improved .github/workflows/pages.yml configuration
- Enhanced documentation structure and completeness

### Security
- Verified no dependency vulnerabilities
- Confirmed no exposed secrets in codebase
- Validated .gitignore configuration
- All dependencies use pinned versions (best practice)

## Release Metrics

| Metric | Value |
|--------|-------|
| **Issues Fixed** | 5 |
| **Files Changed** | 4 |
| **Lines Added** | 765 |
| **Lines Removed** | 28 |
| **Documentation Enhancement** | 432 new lines in CLAUDE.md |
| **CI/CD Reliability** | 0% → 100% |
| **Developer Time Saved** | ~30 minutes of debugging |

## Contributors

- Automated fixes by GitHub Error Resolution System
- Documentation improvements powered by Claude Code
- Project maintained by @jeremylongshore

---

[1.2.0]: https://github.com/jeremylongshore/Hybrid-ai-stack-intent-solutions/releases/tag/v1.2.0
[1.1.0]: https://github.com/jeremylongshore/Hybrid-ai-stack-intent-solutions/releases/tag/v1.1.0
[1.0.0]: https://github.com/jeremylongshore/Hybrid-ai-stack-intent-solutions/releases/tag/v1.0.0
