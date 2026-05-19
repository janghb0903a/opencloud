# Project Spec: Grafana Dashboard AI Assistant

## 1. Overview
- Goal: Generate Grafana dashboard JSON from natural-language requests using internal Prometheus metrics.
- Core capabilities:
  - Prometheus metadata extraction and cache
  - AI context injection with relevant metrics
  - Real-time JSON generation and preview
- Target environment: Rancher Monitoring (Prometheus) + on-prem AI GPU server (NodePort)

## 2. Technical Stack
- Frontend: Next.js 14+ (App Router)
- UI/UX: Tailwind CSS (+ optional shadcn/ui)
- Backend: FastAPI (Python, async)
- AI Model: GPT-OSS-120B (OpenAI API spec compatible)
- Code Editor: Monaco Editor

## 3. Required Environment Variables
```yaml
config:
  PROMETHEUS_URL: "http://rancher-monitoring-prometheus.cattle-monitoring-system:9090"
  PROMETHEUS_TOKEN: "Bearer <SERVICE_ACCOUNT_TOKEN>"
  AI_BACKEND_URL: "http://<AI_NODE_PORT_IP>:<PORT>/v1"
  AI_MODEL_NAME: "gpt-oss-120b"
```

## 4. Architecture and Data Flow
1. Metadata Fetching: Backend fetches and caches `/api/v1/metadata` from `PROMETHEUS_URL` at startup.
2. User Request: User asks for dashboard generation in UI.
3. Context Construction: Backend extracts related metrics/labels and injects into AI prompt.
4. AI Generation: Internal model generates Grafana dashboard JSON.
5. Streaming and Preview: Output streams to Monaco Editor with live preview.

## 5. Frontend UX Requirements
- Modern dark UI (OpenAI / Vercel style)
- Bento grid layout for summary and JSON areas
- Interactive chat flow with Framer Motion animations
- DX features:
  - One-click copy
  - Live validation
  - Metric search and prompt attachment

## 6. Deployment and Operations
- Docker: Multi-stage builds for frontend/backend
- Kubernetes:
  - NodePort AI backend via direct IP or ExternalName
  - `PROMETHEUS_TOKEN` stored in Kubernetes Secret
- Helm:
  - Cluster-specific Prometheus and AI endpoint settings via `values.yaml`
