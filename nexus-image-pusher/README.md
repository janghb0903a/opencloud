# Nexus Image Pusher

업로드한 `docker save` 아카이브(`.tar`)에서 이미지 이름/태그를 읽고,
선택한 사설 넥서스 레지스트리로 경로를 재작성해 push 하는 웹 애플리케이션입니다.

## 주요 기능

- 웹 UI에서 이미지 파일 업로드
- 메타코드(소문자 4자리) 검증
- 넥서스 대상 선택
- 이미지 경로 재작성 규칙 적용
  - 입력: `docker.io/library/python:3.11`
  - 메타코드: `ocps`
  - 대상 레지스트리: `registry.example.local:5000`
  - 결과: `registry.example.local:5000/ocps/python:3.11`
- 진행 상태/로그/완료 여부 표시

## 로컬 실행

```bash
docker buildx build --load -t nexus-image-pusher:0.1.0 .
docker run --rm -p 8000:8000 nexus-image-pusher:0.1.0
```

브라우저에서 `http://localhost:8000` 접속.

## 컨테이너 이미지 빌드/푸시 예시

```bash
docker buildx build --load -t <your-registry>/nexus-image-pusher:0.1.0 .
docker push <your-registry>/nexus-image-pusher:0.1.0
```

## Helm 배포

```bash
helm upgrade --install nexus-image-pusher ./helm/nexus-image-pusher \
  --namespace nexus-tools --create-namespace \
  --set image.repository=<your-registry>/nexus-image-pusher \
  --set image.tag=0.1.0
```

## 기본 레지스트리 목록

1. `registry.example.local:5000`

## 환경 변수

- `REGISTRY_OPTIONS`: 쉼표(,) 구분 레지스트리 목록
- `NEXUS_USERNAME`: 필수 (기본값 없음)
- `NEXUS_PASSWORD`: 필수 (기본값 없음)

## 빌드 실패(apt 503) 대응

외부 `deb.debian.org`가 불안정하면 사내/대체 미러를 지정해 빌드하세요.

```bash
docker buildx build --load \
  --build-arg APT_SCHEME=https \
  --build-arg APT_MIRROR=ftp.kr.debian.org \
  -t nexus-image-pusher:0.1.0 .
```

## 내부망 오프라인 빌드 (Python 3.11 wheelhouse)

외부망(인터넷 가능) 환경에서 Python 3.11 전용 wheel 파일을 먼저 수집합니다.

```bash
cd nexus-image-pusher
python3.11 -m pip download \
  --dest wheelhouse \
  --only-binary=:all: \
  --python-version 311 \
  --implementation cp \
  --abi cp311 \
  --platform manylinux2014_x86_64 \
  -r requirements.txt
```

생성된 `wheelhouse/` 폴더를 프로젝트와 함께 내부망으로 반입한 뒤, 오프라인 모드로 빌드합니다.

```bash
docker buildx build --load \
  --build-arg OFFLINE_PIP=true \
  -t nexus-image-pusher:0.1.0 .
```

참고:
- 오프라인 모드는 Python 패키지 설치만 `wheelhouse/`에서 수행합니다.
- `skopeo`는 OS 패키지(`apt`)라서 내부망에서 Debian 미러 접근이 가능해야 합니다.
- 내부망에서 Debian 미러가 없다면 `skopeo`와 의존성 `.deb`를 별도 반입해 설치하는 방식으로 추가 변경이 필요합니다.

## 내부망 오프라인 빌드 (APT .deb 포함)

`debs/` 폴더에 `skopeo`와 의존성 `.deb`를 미리 넣어두면 내부망에서 그대로 설치할 수 있습니다.

외부망에서 `.deb` 수집:

```bash
cd nexus-image-pusher
docker run --rm \
  -v "${PWD}:/work" \
  -w /work \
  python:3.11-bookworm \
  bash -lc "apt-get update && apt-get install -y --download-only --no-install-recommends skopeo ca-certificates && cp /var/cache/apt/archives/*.deb /work/debs/"
```

내부망 완전 오프라인 빌드:

```bash
docker buildx build --load \
  --build-arg OFFLINE_APT=true \
  --build-arg OFFLINE_PIP=true \
  -t nexus-image-pusher:0.1.0 .
```

주의:
- `debs/`에는 `skopeo`와 의존성 패키지가 모두 있어야 합니다.
- 누락 시 빌드 중 apt 의존성 오류가 발생합니다.
