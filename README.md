# opencloud

OpenCloud 운영, 진단, 마이그레이션, 자동화 도구를 모아둔 모노레포입니다. 각 디렉터리는 독립적으로 빌드하거나 배포할 수 있도록 README, Dockerfile, Helm chart 또는 실행 스크립트를 함께 둡니다.

## Repository Map

| Directory | Purpose | Main Runtime / Deploy |
| --- | --- | --- |
| [`ansible-monthly-check/`](./ansible-monthly-check/README.md) | OpenStack/Kubernetes 월간 점검 결과를 호스트별 파일로 생성 | Ansible |
| [`grafana-ai-assistant/`](./grafana-ai-assistant/README.md) | Prometheus 메트릭 컨텍스트와 AI 모델을 사용해 Grafana dashboard JSON 생성 | Next.js, FastAPI, Helm |
| [`helm-ai-agent/`](./helm-ai-agent/README.md) | Kubernetes YAML을 Helm chart 형태로 변환하는 AI 보조 도구 | FastAPI, Nginx, Docker Compose |
| [`nexus-image-pusher/`](./nexus-image-pusher/README.md) | `docker save` 이미지 아카이브를 사설 Nexus 레지스트리로 재태깅/푸시 | FastAPI, Docker, Helm |
| [`ocp-k8s-diagnostic-mcp/`](./ocp-k8s-diagnostic-mcp/README.md) | Kubernetes/OCP 클러스터를 읽기 전용으로 진단하는 MCP 서버 | Python, MCP, Helm |
| [`ocp-openstack-diagnostic-mcp/`](./ocp-openstack-diagnostic-mcp/README.md) | OpenStack 장애 분석을 위한 읽기 전용 MCP 서버 | Python, MCP, Helm |
| [`openstack-migration-web/`](./openstack-migration-web/README.md) | OpenStack 볼륨/VM 마이그레이션 명령을 단계별로 계획하는 웹 UI | Node.js, Docker Compose |
| [`openstack-vm-name-exporter/`](./openstack-vm-name-exporter/README.md) | OpenStack VM UUID와 이름을 Prometheus metric으로 노출 | Python, Docker, Helm |
| [`openstack-vm-recovery-auto/`](./openstack-vm-recovery-auto/README.md) | OpenStack VM을 자동 발견하고 ping 실패 누적 시 복구 정책 수행 | Python, CronJob, Helm |
| [`oss-report-agent/`](./oss-report-agent/README.md) | 점검 결과 파일을 읽어 LLM 기반 Markdown 보고서 생성 | Python, Docker, Helm |
| [`vm-ip-guide-web/`](./vm-ip-guide-web/README.md) | VM IP/Hostname 안내용 정적 웹 서비스 | Nginx, Docker, Helm |

## Excluded Local Workspaces

아래 경로는 현재 로컬 작업공간에는 있지만 이 저장소 push 대상에서 제외합니다.

- `EconomyNewsDashboard-Installer/`
- `grafana-ai-assistant+/`
- `openstack-vm-recovery/`
- `wally-infra-sanitized/`

## Suggested Use

1. 필요한 도구 디렉터리로 이동합니다.
2. 해당 디렉터리의 `README.md`에서 빌드/실행/배포 절차를 확인합니다.
3. Kubernetes 배포가 필요한 도구는 각 디렉터리의 `helm/` 또는 `deploy/helm/` chart를 사용합니다.
4. 내부망 반입이 필요한 도구는 `wheelhouse`, `wheels`, image tar 저장 절차를 먼저 수행합니다.

## Security Notes

- 실제 인증정보, kubeconfig, OpenStack `clouds.yaml`, Prometheus token, AI API key는 커밋하지 않습니다.
- README와 values 예시는 placeholder 또는 Secret 참조 방식만 사용합니다.
- 배포 전에는 각 chart의 `values.yaml`을 환경별 별도 파일로 분리해 관리하는 것을 권장합니다.
