# opencloud

OpenCloud 운영, 진단, 마이그레이션, 모니터링, 자동화 도구를 모아둔 저장소입니다. 각 디렉터리는 독립적으로 빌드하거나 배포할 수 있도록 README, 컨테이너 빌드 파일, Helm chart, 실행 스크립트를 함께 포함합니다.

## 프로젝트 목록

| 디렉터리 | 설명 | 실행/배포 방식 |
| --- | --- | --- |
| [`ansible-monthly-check/`](./ansible-monthly-check/README.md) | Bastion 서버에서 OpenStack/Kubernetes 월간 점검을 수행하고 호스트별 점검 파일을 생성합니다. | Ansible |
| [`grafana-ai-assistant/`](./grafana-ai-assistant/README.md) | Prometheus 메트릭 정보와 AI backend를 사용해 자연어 요청을 Grafana dashboard JSON으로 변환합니다. | Next.js, FastAPI, Helm |
| [`helm-ai-agent/`](./helm-ai-agent/README.md) | Kubernetes YAML manifest를 Helm chart 구조로 변환하는 AI 보조 도구입니다. | FastAPI, Nginx, Docker Compose |
| [`nexus-image-pusher/`](./nexus-image-pusher/README.md) | `docker save` 이미지 아카이브를 사설 Nexus registry 경로로 재태깅하고 push합니다. | FastAPI, Docker, Helm |
| [`ocp-k8s-diagnostic-mcp/`](./ocp-k8s-diagnostic-mcp/README.md) | Kubernetes/OCP 클러스터 상태를 읽기 전용으로 진단하는 MCP 서버입니다. | Python, MCP, Helm |
| [`ocp-openstack-diagnostic-mcp/`](./ocp-openstack-diagnostic-mcp/README.md) | OpenStack 장애 분석과 진단을 위한 읽기 전용 MCP 서버입니다. | Python, MCP, Helm |
| [`openstack-migration-web/`](./openstack-migration-web/README.md) | OpenStack 볼륨/VM 마이그레이션 절차와 명령어를 단계별로 계획하는 웹 UI입니다. | Node.js, Docker Compose |
| [`openstack-vm-name-exporter/`](./openstack-vm-name-exporter/README.md) | OpenStack VM UUID와 이름 매핑 정보를 Prometheus metric으로 노출합니다. | Python, Docker, Helm |
| [`openstack-vm-recovery-auto/`](./openstack-vm-recovery-auto/README.md) | OpenStack VM을 자동 탐색하고 ping 실패 누적 시 복구 정책을 수행합니다. | Python, CronJob, Helm |
| [`oss-report-agent/`](./oss-report-agent/README.md) | 인프라 점검 결과 파일을 읽어 LLM 기반 Markdown 보고서를 생성합니다. | Python, Docker, Helm |
| [`vm-ip-guide-web/`](./vm-ip-guide-web/README.md) | VM IP와 hostname 안내 페이지를 제공하는 정적 웹 서비스입니다. | Nginx, Docker, Helm |

## 용도별 분류

### 진단 도구

- `ocp-k8s-diagnostic-mcp/`
- `ocp-openstack-diagnostic-mcp/`
- `openstack-vm-name-exporter/`

### 자동화 및 복구

- `ansible-monthly-check/`
- `openstack-vm-recovery-auto/`
- `nexus-image-pusher/`

### AI 기반 도구

- `grafana-ai-assistant/`
- `helm-ai-agent/`
- `oss-report-agent/`

### 웹 유틸리티

- `openstack-migration-web/`
- `vm-ip-guide-web/`

## 사용 흐름

1. 필요한 기능에 맞는 프로젝트 디렉터리로 이동합니다.
2. 해당 디렉터리의 `README.md`에서 빌드, 실행, 배포 방법을 확인합니다.
3. Kubernetes 배포가 필요한 경우 각 프로젝트의 `helm/` 또는 `deploy/helm/` chart를 사용합니다.
4. 내부망 또는 air-gapped 환경으로 반입해야 하는 프로젝트는 wheelhouse, image tar, offline package 등을 먼저 준비합니다.

## 저장소 관리 원칙

- 실제 인증정보, kubeconfig, OpenStack `clouds.yaml`, Prometheus token, AI API key는 Git에 커밋하지 않습니다.
- 예제 값은 placeholder로 유지하고, 실제 값은 Kubernetes Secret, 환경 변수, 외부 Secret Manager 등을 통해 주입합니다.
- 각 도구는 가능한 한 자기 디렉터리 안에 source, README, Dockerfile, Helm chart, helper script를 함께 둡니다.
- 운영 환경별 설정은 chart 기본값을 직접 수정하기보다 별도 values 파일로 관리하는 것을 권장합니다.
