# Open Source Cloud Report Agent

OpenStack/Kubernetes 점검 스크립트 결과를 읽어 Markdown 보고서를 생성하는 Python 기반 AI Agent입니다.
LLM backend는 Ollama 또는 OpenAI-compatible(vLLM) 중 선택할 수 있습니다.

## 프로젝트 구조
- `app/`: Python 애플리케이션 코드 (웹 UI 포함)
- `requirements.txt`: Python 의존성
- `wheelhouse/`: 오프라인 Python wheel 저장 경로(에어갭 빌드 필수)
- `docker/`: Docker 빌드/실행 관련 파일
- `helm/oss-report-agent`: Helm Chart 배포 파일 (PVC + Ingress)
- `check/`: `<hostname>_check` 파일 적재 디렉터리

## 핵심 환경 변수
- `LLM_PROVIDER` (`ollama` 또는 `openai`)
- `OLLAMA_BASE_URL` (필수 권장)
- `OLLAMA_MODEL` (기본: `llama3.1:8b`)
- `OPENAI_BASE_URL` (vLLM OpenAI endpoint, 예: `http://vllm-openai.default.svc.cluster.local:8000`)
- `OPENAI_MODEL` (예: `meta-llama/Llama-3.1-8B-Instruct`)
- `OPENAI_API_KEY` (선택)
- `CHECK_INPUT_PATH` (기본 Helm: `/input/checks`)
- `CHECK_PATH_PATTERN` (fallback 기본: `/tmp/check_{date}`)
- `OUTPUT_DIR` (기본 Helm: `/input/checks/reports`)
- `REQUEST_TIMEOUT_SECONDS` (기본: `180`)

## 1) 완전 에어갭 준비 (인터넷망에서 수행)

### 1-1. 베이스 이미지 저장
```bash
docker pull python:3.11-slim
docker save -o base-images.tar python:3.11-slim
```

### 1-2. Python 의존성 wheel 다운로드
프로젝트 루트에서:
```bash
pip download -r requirements.txt -d wheelhouse
```

생성물:
- `base-images.tar`
- `wheelhouse/` 디렉터리

위 2개를 소스와 함께 내부망으로 반입합니다.

## 2) 완전 에어갭 빌드 (내부망에서 수행)

### 2-1. 베이스 이미지 로드
```bash
docker load -i base-images.tar
```

### 2-2. Docker 빌드 (오프라인)
현재 Dockerfile은 `wheelhouse`를 사용해 `--no-index`로 설치하므로 인터넷 없이 빌드됩니다.
```bash
docker build -t oss-report-agent:0.1.0 -f docker/Dockerfile .
```

PowerShell:
```powershell
./docker/build.ps1 -Tag oss-report-agent:0.1.0
```

## 3) check 파일 준비
`check/` 경로에 `<hostname>_check` 파일들을 넣습니다.

예시:
- `controller01_check`
- `worker01_check`
- `worker02_check`

앱은 확장자 없는 `_check` 파일도 읽습니다.

## 4) Helm 배포 (PVC + 내부망 LLM)
이 차트는 기본적으로 PVC를 생성하고(`/input/checks` 마운트), 해당 경로의 파일을 읽습니다.
StorageClass 기본값은 `sc-dell-xfs-retain`입니다.

Ollama 사용 예시:
```bash
helm upgrade --install oss-report-agent ./helm/oss-report-agent \
  --set image.repository=oss-report-agent \
  --set image.tag=0.1.0 \
  --set env.LLM_PROVIDER=ollama \
  --set env.OLLAMA_BASE_URL=http://<OLLAMA_SVC>:11434 \
  --set checkStorage.mode=pvc \
  --set checkStorage.pvc.storageClassName=sc-dell-xfs-retain
```

vLLM(OpenAI-compatible) 사용 예시:
```bash
helm upgrade --install oss-report-agent ./helm/oss-report-agent \
  --set image.repository=oss-report-agent \
  --set image.tag=0.1.0 \
  --set env.LLM_PROVIDER=openai \
  --set env.OPENAI_BASE_URL=http://<VLLM_NODE_IP>:<NODEPORT> \
  --set env.OPENAI_MODEL=<VLLM_MODEL_NAME> \
  --set checkStorage.mode=pvc \
  --set checkStorage.pvc.storageClassName=sc-dell-xfs-retain
```

## 5) check 파일을 PVC에 복사
Helm 배포 후 Running 상태의 report-agent Pod로 `kubectl cp`를 수행해 `check/` 파일들을 `/input/checks`에 복사합니다.

RHEL8/bash:
```bash
chmod +x ./helm/oss-report-agent/scripts/copy-check-files-to-pvc.sh
./helm/oss-report-agent/scripts/copy-check-files-to-pvc.sh default oss-report-agent ./check /input/checks
```

PowerShell(옵션):
```powershell
./helm/oss-report-agent/scripts/copy-check-files-to-pvc.ps1 -Namespace default -ReleaseName oss-report-agent -SourceDir ..\..\..\check -TargetDir /input/checks
```

배포 + 파일복사를 한 번에 실행(자동):
```bash
chmod +x ./helm/oss-report-agent/scripts/deploy-with-sync.sh
./helm/oss-report-agent/scripts/deploy-with-sync.sh \
  default \
  oss-report-agent \
  ./helm/oss-report-agent \
  oss-report-agent-check-pvc \
  ./check \
  oss-report-agent \
  0.1.0 \
  ollama \
  http://<OLLAMA_SVC>:11434 \
  llama3.1:8b
```

vLLM(OpenAI-compatible) 자동 배포+복사:
```bash
./helm/oss-report-agent/scripts/deploy-with-sync.sh \
  default \
  oss-report-agent \
  ./helm/oss-report-agent \
  oss-report-agent-check-pvc \
  ./check \
  oss-report-agent \
  0.1.0 \
  openai \
  http://<VLLM_NODE_IP>:<NODEPORT> \
  <VLLM_MODEL_NAME>
```

## 6) 웹 UI로 보고서 생성/조회
서비스 루트(`/`)에 웹 페이지가 제공됩니다.

Ingress를 쓰지 않는 경우(임시):
```bash
kubectl -n default port-forward svc/oss-report-agent 8000:8000
```
브라우저에서 `http://localhost:8000` 접속 후,
- 입력 경로/출력 경로 입력(선택)
- `보고서 생성` 클릭
- 하단 목록에서 `보기/다운로드`

## 7) Ingress 노출
`values.yaml`의 ingress 값을 사용하거나, 설치 시 `--set`으로 지정합니다.

```bash
helm upgrade --install oss-report-agent ./helm/oss-report-agent \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=report.example.local \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix
```

DNS 또는 hosts에 `report.example.local` 매핑 후 `http://report.example.local` 접속.

## 8) API 확인
```bash
curl http://<service-endpoint>/health
curl http://<service-endpoint>/health/llm
curl http://<service-endpoint>/health/ollama
curl -X POST http://<service-endpoint>/generate -H "Content-Type: application/json" -d '{}'
curl http://<service-endpoint>/api/reports
```

## 참고
- ConfigMap 1MiB 제한 문제를 피하기 위해 파일 입력은 PVC 방식으로 전환했습니다.
- PowerFlex CSI + `sc-dell-xfs-retain` 환경을 기본값으로 설정했습니다.
