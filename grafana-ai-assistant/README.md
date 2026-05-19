# Grafana Dashboard AI Assistant

Prometheus 메트릭 컨텍스트와 OpenAI-compatible AI 모델을 사용해 Grafana dashboard JSON을 생성하는 도구입니다. 사용자는 자연어로 원하는 대시보드를 요청하고, 백엔드는 Prometheus metadata를 참고해 관련 metric을 프롬프트에 주입한 뒤 JSON 생성을 수행합니다.

## 주요 기능

- Prometheus `/api/v1/metadata` 기반 metric 검색 및 컨텍스트 구성
- 자연어 요청을 Grafana dashboard JSON으로 변환
- SSE streaming 응답 지원
- Monaco Editor 기반 JSON 미리보기 및 검증
- Docker Compose, Kubernetes manifest, Helm chart 배포 지원

## 구성

```text
grafana-ai-assistant/
|- backend/                       # FastAPI backend
|- frontend/                      # Next.js frontend
|- deploy/
|  |- helm/grafana-ai-assistant/  # Helm chart
|  `- k8s/all-in-one.yaml         # 단일 manifest 예시
|- docs/                          # architecture and project spec
`- docker-compose.yml
```

## 주요 환경 변수

| Name | Description |
| --- | --- |
| `PROMETHEUS_URL` | Rancher Monitoring 또는 Prometheus endpoint |
| `PROMETHEUS_TOKEN` | Prometheus 접근용 bearer token. Kubernetes Secret으로 관리 |
| `AI_BACKEND_URL` | OpenAI-compatible AI endpoint |
| `AI_MODEL_NAME` | 사용할 모델명 |
| `AI_API_KEY` | AI endpoint가 요구하는 경우 설정 |

## 로컬 실행

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker Compose:

```bash
APP_VERSION=0.1.3 IMAGE_TAG=0.1.3 docker compose up --build -d
```

## Helm 배포

```bash
helm upgrade --install grafana-ai-assistant ./deploy/helm/grafana-ai-assistant \
  -n ai-tools --create-namespace
```

환경별 Prometheus URL, token, AI endpoint는 `values.yaml` 또는 별도 values 파일로 주입합니다.

## 주요 API

- `GET /healthz`: backend 상태 확인
- `GET /api/metrics/search?q=<keyword>`: Prometheus metric 검색
- `POST /api/dashboard/generate`: dashboard JSON 생성
- `POST /api/dashboard/stream`: dashboard JSON streaming 생성

## 보안 메모

- `PROMETHEUS_TOKEN`과 `AI_API_KEY`는 Secret으로 관리합니다.
- AI backend가 NodePort 등으로 노출되는 경우 네트워크 접근 제어를 별도로 적용합니다.
- 운영 배포에서는 Ingress TLS와 RBAC 정책을 환경에 맞게 적용합니다.
