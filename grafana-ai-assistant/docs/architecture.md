# Architecture Diagram (Mermaid)

```mermaid
flowchart LR
  U[User Browser\nNext.js + Monaco] -->|Prompt / Search| B[FastAPI Backend]
  B -->|POST /v1/chat/completions| A[GPT-OSS-120B\nNodePort]
  B -->|GET /api/v1/metadata| P[Prometheus\nRancher Monitoring]
  H[Helm Values + Secret] -->|Env Injection| B
  H -->|Env Injection| U
  A -->|Grafana JSON| B -->|Live Preview| U
```
