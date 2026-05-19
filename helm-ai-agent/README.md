# Helm AI Agent

Kubernetes YAML manifest를 입력받아 Helm chart 구조로 변환하는 AI 보조 도구입니다. FastAPI backend가 변환 요청을 받고, Bedrock 기반 LLM backend가 chart template과 values 구성을 보완한 뒤 ZIP 파일로 결과를 제공합니다.

## 주요 기능

- Kubernetes YAML 업로드 또는 입력
- 리소스 구조 분석
- `templates/`, `values.yaml`, chart metadata 생성
- AWS Bedrock 기반 Helm template 보완
- Web UI에서 변환 결과 ZIP 다운로드

## 구성

```text
helm-ai-agent/
|- api/
|  |- app.py           # FastAPI endpoint
|  |- builder.py       # Helm chart builder
|  |- llm_backend.py   # Bedrock 호출 로직
|  |- schemas.py       # request/response schema
|  `- Dockerfile
|- web/
|  |- Dockerfile
|  `- dist/            # 정적 UI 빌드 산출물
|- nginx/
|  `- default.conf
`- docker-compose.yaml
```

## 동작 흐름

1. 사용자가 Web UI에서 YAML manifest를 업로드합니다.
2. API 서버의 `/convert` endpoint가 요청을 수신합니다.
3. `builder.py`가 Kubernetes 리소스를 Helm chart 구조로 변환합니다.
4. `llm_backend.py`가 Bedrock 모델을 호출해 template과 values 구성을 보완합니다.
5. 완성된 chart를 ZIP 파일로 반환합니다.

## 환경 변수

| Name | Description |
| --- | --- |
| `LLM_BACKEND` | 기본값 `bedrock` |
| `AWS_REGION` | Bedrock 사용 region |
| `BEDROCK_MODEL_ID` | 호출할 Bedrock model ID |
| `AWS_ACCESS_KEY_ID` | 필요한 경우 환경 변수 또는 Secret으로 주입 |
| `AWS_SECRET_ACCESS_KEY` | 필요한 경우 환경 변수 또는 Secret으로 주입 |
| `AWS_SESSION_TOKEN` | 임시 자격증명 사용 시 주입 |

## 실행

```bash
docker-compose up --build
```

접속:

- Web UI: `http://localhost`
- API docs: `http://localhost/api/docs`

## 보안 메모

- AWS credential은 코드나 README에 직접 기록하지 않습니다.
- 운영 환경에서는 IAM Role, Secrets Manager, Kubernetes Secret 같은 외부 Secret 관리 방식을 사용합니다.
- 생성된 Helm chart는 배포 전 사람이 한 번 더 검토하는 것을 권장합니다.
