from __future__ import annotations

from datetime import datetime
from pathlib import Path


REPORT_TITLE = "====== 오픈소스클라우드플랫폼 월간정기점검 보고서 ======"

REPORT_TEMPLATE = """
====== 오픈소스클라우드플랫폼 월간정기점검 보고서 ======

===== 1. OpenStack 플랫폼 점검 =====

==== 1.1 노드 운영체제 상태 ====
=== 1.1.1 CPU 점검 ===
=== 1.1.2 메모리 점검 ===
=== 1.1.3 파일시스템 점검 ===
=== 1.1.4 시간 동기화 점검 ===

==== 1.2 미들웨어 구성요소 상태 ====
=== 1.2.1 HAProxy 점검 ===
=== 1.2.2 PCSD 점검 ===
=== 1.2.3 Pacemaker 점검 ===
=== 1.2.4 Corosync 점검 ===
=== 1.2.5 RabbitMQ 점검 ===
=== 1.2.6 Memcached 점검 ===
=== 1.2.7 HTTPD 점검 ===
=== 1.2.8 PerconaDB 점검 ===
=== 1.2.9 Open vSwitch 점검 ===

==== 1.3 클러스터 운영 상태 ====
=== 1.3.1 CPU 및 메모리 여유 용량 점검 ===
=== 1.3.2 주요 서비스 상태 점검 ===
=== 1.3.3 볼륨 상태 점검 ===
=== 1.3.4 OS 이미지 점검 ===
=== 1.3.5 불필요 네트워크 포트 점검 ===
=== 1.3.6 하이퍼바이저 상태 점검 ===

==== 1.4 프로세스 점검 ====
=== 1.4.1 Control 노드 프로세스 점검 ===
=== 1.4.2 Compute 노드 프로세스 점검 ===

===== 2. Kubernetes 플랫폼 점검 =====

==== 2.1 노드 운영체제 상태 ====
=== 2.1.1 CPU 점검 ===
=== 2.1.2 메모리 점검 ===
=== 2.1.3 파일시스템 점검 ===
=== 2.1.4 시간 동기화 점검 ===

==== 2.2 클러스터 제어면 및 핵심 구성요소 ====
=== 2.2.1 클러스터별 상태 점검 ===
=== 2.2.2 kube-apiserver 점검 ===
=== 2.2.3 kube-controller-manager 점검 ===
=== 2.2.4 kube-scheduler 점검 ===
=== 2.2.5 kubelet 점검 ===
=== 2.2.6 etcd 점검 ===
=== 2.2.7 리소스 여유량 점검 ===
=== 2.2.8 발생 이벤트 점검 ===

==== 2.3 워크로드 및 스토리지 상태 ====
=== 2.3.1 Pod 상태 점검 ===
=== 2.3.2 DaemonSet/StatefulSet/Deployment/Job 상태 점검 ===
=== 2.3.3 PV/PVC 상태 점검 ===

==== 2.4 관리 플랫폼 점검 ====
=== 2.4.1 Rancher 상태 점검 ===
=== 2.4.2 Nexus 상태 점검 ===

===== 3. 공통 보안 및 운영 점검 =====

==== 3.1 인증서 만료일 점검 ====
=== 3.1.1 OpenStack 인증서 만료일 점검 ===
=== 3.1.2 Kubernetes 인증서 만료일 점검 ===
""".strip()


def build_prompt(collected: list[dict[str, str]], input_path: str) -> str:
    host_names = _extract_hosts(collected)
    host_summary = ", ".join(host_names) if host_names else "호스트 식별 실패(파일명 규칙 확인 필요)"

    header = f"""
당신은 오픈소스클라우드플랫폼 월간정기점검 보고서를 작성하는 SRE 감사 보조 AI입니다.
아래 수집 데이터를 근거로 반드시 지정 템플릿을 유지하여 한국어 DokuWiki 문법 보고서를 작성하세요.

작성 규칙:
1) 템플릿의 제목/섹션/하위섹션 순서와 문구를 그대로 유지
   - 섹션명/소분류명을 임의로 변경, 통합, 삭제, 재배치 금지
   - 특히 Kubernetes 섹션(2.x)은 데이터가 없어도 반드시 출력
2) 각 소분류마다 아래 4개 항목을 반드시 작성
   - 점검결과: 정상 | 주의 | 장애 | 확인 필요
   - 근거: 파일명/로그 라인/수치 기반으로 간단 명시
   - 위험도: High | Medium | Low
   - 조치사항: 즉시 실행 가능한 조치 1~3개
   - CPU 판정 기준(완화): idle 20% 이상=정상, 10~20%=주의, 10% 미만=장애
   - idle 90% 미만을 주의/장애로 판정하는 과도한 기준은 사용 금지
3) 각 소분류마다 호스트 결과를 아래 기준으로 반드시 작성
   - 이상 호스트 수가 10대 이하: 본문에 '이상 호스트: host1, host2 ...' 형태로 직접 기재
   - 이상 호스트 수가 11대 이상: 본문에는 '이상 호스트: 별첨 참조(총 N대)'로 표기하고 별첨으로 분리
   - 정상 호스트는 나열하지 말고, '비정상 호스트 수: N대'를 반드시 기재
   - '비정상 호스트'는 실제 오류/임계치 초과/서비스 down 근거가 있는 경우에만 집계
   - 데이터 없음, 수집 실패, [skipped], 점검 미대상은 비정상 호스트로 집계 금지 (비정상 호스트 수 0 가능)
4) 데이터에 '[skipped]'가 있으면 해당 항목은 점검 미대상으로 간주
   - 점검결과: '확인 필요(점검 미대상)'로 작성
   - 근거에 '[skipped]' 문자열을 명시
   - 점검 미대상/데이터 없음 항목은 위험도 기본값을 Low 또는 N/A로 표기하고 비정상 호스트에 포함하지 말 것
   - 특정 항목 데이터가 아예 없더라도 해당 항목 헤더는 유지하고 아래 기본 문구로 채울 것:
     * 점검결과: 확인 필요(점검 미대상)
     * 근거: 데이터 없음(수집 대상 제외 또는 결과 미수집)
     * 위험도: N/A
     * 비정상 호스트 수: 0대
     * 조치사항: 점검 대상/수집 스크립트 포함 여부 확인
5) 별첨 섹션을 문서 마지막에 추가
   - 섹션명: '별첨. 항목별 이상 호스트 상세'
   - 형식: '항목명 | 이상 호스트 목록'
6) 근거가 없는 추정은 금지하고, 데이터가 없으면 '확인 필요'로 명시
7) 보고서 마지막에 '종합 요약' 섹션 추가
   - 전체 이슈 개수(High/Medium/Low)
   - 호스트별 이슈 요약(호스트명: High/Medium/Low 건수)
   - 즉시 조치(24시간), 단기(7일), 중기(30일) 액션 아이템
8) 불필요한 서론/사족 없이 결과만 출력
9) 입력 데이터는 정형 JSON이 아니라 CLI 원문 로그일 수 있음
   - 예: `top -bn1 | grep Cpu`, `free -m`, `df -h`, `kubectl get pods -A`, `openstack service list`
   - 명령어 라인과 그 아래 출력 결과를 근거로 판단
   - 값 파싱이 애매하면 추정하지 말고 '확인 필요'로 처리
   - check 파일에 명령어 원문이 포함되면, 해당 명령어의 의도(이상 항목 grep/awk 필터 여부)를 해석해서 판정
   - 특히 '이상 항목만 출력' 명령에서 결과가 비어있으면 정상으로 판정 가능
   - 파일시스템 점검은 디바이스명이 아닌 마운트 경로 기준으로 해석하고, `/dev/loop*` 관련 출력은 무시
   - OpenStack Control의 MySQL은 클러스터 기준으로 `mysql@bootstrap` 1대 + `mysqld` 2대(총 3대) 구성은 정상으로 간주
10) 근거는 가능한 경우 '명령어 + 핵심 출력값' 형태로 작성
   - 예: `top -bn1 | grep Cpu -> idle 7.2%`
   - 예: `df -h -> / 92%`
   - 근거가 없으면 '데이터 없음'만 쓰고 비정상 판정/호스트 지정 금지
11) 출력 문법은 DokuWiki 문법만 사용
   - 헤더는 `======`, `=====`, `====`, `===` 사용
   - 목록은 `  *` 사용
   - Markdown 헤더(`#`), 코드펜스(````), 테이블 파이프 Markdown 문법은 사용 금지
12) 줄바꿈/레이아웃 규칙을 반드시 준수
   - 소분류 헤더(예: `=== 1.1.1 CPU 점검 ===`)는 단독 한 줄로만 출력
   - 소분류 본문은 반드시 다음 5줄을 각 줄바꿈으로 출력:
     1) `  * 점검결과: ...`
     2) `  * 근거: ...`
     3) `  * 위험도: ...`
     4) `  * 비정상 호스트 수: ...`
     5) `  * 조치사항: ...`
   - 헤더와 첫 번째 목록 사이, 소분류 블록과 다음 소분류 헤더 사이에 빈 줄 1줄을 넣을 것
13) TODO/빈 결과 처리 규칙
   - `TODO`, `command will be provided later`, `xxxxxxx` 같은 플레이스홀더는 점검 미완료로 보되, 자동으로 비정상으로 집계하지 말 것
   - `grep/awk` 등으로 문제 항목만 출력하는 명령의 결과가 빈 문자열이면 점검결과를 정상으로 처리 가능
   - 위 경우 근거에는 `이상 항목 grep 결과 없음` 또는 `TODO(명령 미정)`을 명시
14) 최종 출력 전 자체 검증
   - 템플릿의 모든 섹션/소분류가 출력에 존재하는지 확인 후 응답
   - 누락 항목이 있으면 반드시 '확인 필요(점검 미대상)' 블록으로 보완해서 출력

입력 경로: {input_path}
수집 시각: {datetime.now().isoformat()}
점검 대상 호스트(파일명 기준): {host_summary}
""".strip()

    blocks: list[str] = [header, "\n[고정 보고서 템플릿]\n", REPORT_TEMPLATE, "\n\n[수집 데이터]\n"]

    for item in collected:
        blocks.append(f"\n### FILE: {item['path']}\n")
        blocks.append(item["content"])

    blocks.append("\n\n위 템플릿을 그대로 유지한 최종 보고서를 출력하세요.")

    return "\n".join(blocks)


def _extract_hosts(collected: list[dict[str, str]]) -> list[str]:
    hosts: set[str] = set()
    for item in collected:
        name = Path(item["path"]).name
        if name.endswith("_check"):
            hosts.add(name.removesuffix("_check"))
            continue
        stem = Path(name).stem
        if stem.endswith("_check"):
            hosts.add(stem.removesuffix("_check"))
    return sorted(hosts)


def wrap_report(content: str, input_path: str, model: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized = content.strip()
    if normalized.startswith(REPORT_TITLE):
        normalized = normalized[len(REPORT_TITLE):].lstrip()
    if normalized.startswith("# 오픈소스클라우드플랫폼 월간정기점검 보고서"):
        normalized = normalized[len("# 오픈소스클라우드플랫폼 월간정기점검 보고서"):].lstrip()

    return (
        f"{REPORT_TITLE}\n\n"
        f"  * 생성시각: {now}\n"
        f"  * 입력경로: ''{input_path}''\n"
        f"  * 생성모델: ''{model}''\n\n"
        f"{normalized}\n"
    )
