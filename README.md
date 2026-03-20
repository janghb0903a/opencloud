# opencloud

이 저장소는 OpenCloud 운영 및 자동화 도구를 모아둔 레포지토리입니다.

## Directory Overview

### `ansible-monthly-check/`
- Ansible 기반으로 OpenStack 및 Kubernetes 월간 인프라 점검을 수행합니다.
- 배스천 호스트에서 실행되며, 호스트별로 출력 파일(`<hostname>_check`)을 생성합니다.
- 점검 결과는 `oss-report-agent` 입력 데이터로 활용할 수 있습니다.

### `nexus-image-pusher/`
- `docker save` 아카이브(`.tar`)의 이미지를 사설 Nexus 레지스트리로 재태깅/푸시하는 웹 앱입니다.
- 메타코드 기반 경로 재작성 규칙(예: `<registry>/<metacode>/<image>:<tag>`)을 적용합니다.
- 컨테이너 런타임 및 Helm 배포를 지원합니다.

### `openstack-vm-name-exporter/`
- OpenStack VM 이름과 관련 메타데이터를 수집해 모니터링/리포팅에 활용할 수 있도록 내보냅니다.

### `oss-report-agent/`
- `*_check` 파일을 읽어 Markdown 보고서를 생성하는 Python 리포트 에이전트입니다.
- Ollama 및 OpenAI 호환(vLLM) 백엔드를 지원합니다.
- Docker/Helm 배포와 PVC 기반 입력 경로를 지원합니다.

### `vm-ip-guide-web/`
- VM IP 조회 및 안내 워크플로우를 제공하는 웹 서비스입니다.
- Kubernetes 배포 매니페스트를 포함합니다.

## Quick Links

- [ansible-monthly-check](./ansible-monthly-check/README.md)
- [nexus-image-pusher](./nexus-image-pusher/README.md)
- [openstack-vm-name-exporter](./openstack-vm-name-exporter/README.md)
- [oss-report-agent](./oss-report-agent/README.md)
- [vm-ip-guide-web](./vm-ip-guide-web/README.md)
