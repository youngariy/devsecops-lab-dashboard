# 📘 DevOps Lab Dashboard

### DevSecOps 파이프라인 시각화 및 보안 결과 수집 시스템

---

# 1. 프로젝트 개요

## 1-1. 프로젝트명

**DevOps Lab Dashboard**

## 1-2. 프로젝트 목적

GitHub Actions 기반 CI / Security / CD 파이프라인의 실행 결과와 보안 스캔 데이터를 수집·정규화하여 시각화하는 DevSecOps 대시보드 시스템을 구축한다.

## 1-3. 기획 배경

현재 저장소는 다음과 같은 DevSecOps 구조를 가진다:

* CI: Docker Compose 기반 테스트
* Security: Semgrep / Bandit / pip-audit / Trivy / Gitleaks
* CD: 이미지 빌드 → 보안 게이트 → SBOM 생성 → Cosign 서명 → 원격 배포

그러나 다음과 같은 한계가 존재한다:

* 워크플로 실행 결과를 장기적으로 비교·분석할 수 없다.
* 보안 도구별 취약점 개수 추이를 확인할 수 없다.
* 이미지 digest 및 Cosign 서명 검증 결과를 시각적으로 추적할 수 없다.
* DevSecOps 흐름을 체계적으로 기록·학습할 수 없다.

따라서, 파이프라인 데이터를 자동 수집하고 구조화하여 시각화하는 시스템을 구축한다.

---

# 2. 시스템 목표

## 2-1. 1차 목표 (MVP)

1. GitHub Actions Workflow 실행 결과 수집
2. GitHub Artifact 기반 보안 결과(JSON) 수집
3. CI / Security / CD 상태 요약 카드 제공
4. 보안 스캔 결과 요약 표시
5. CD 보안 게이트 및 무결성 상태 시각화

## 2-2. 2차 목표 (고도화)

1. 취약점 발생 추이 그래프 제공
2. 배포 타임라인 시각화
3. Webhook 기반 이벤트 중심(Event-Driven) 아키텍처 전환
4. Slack 알림 연동

---

# 3. 시스템 아키텍처

## 3-1. 전체 구성

```
[ GitHub Actions ]
        ↓
(Artifact 생성 및 업로드)
        ↓
[ Flask Ingestion API ]
        ↓
[ Database ]
        ↓
[ Next.js Dashboard ]
```
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f8ff', 'edgeLabelBackground':'#ffffff', 'tertiaryColor': '#e8e8e8'}}}%%
graph TD
    %% 스타일 정의
    classDef ghActions fill:#24292f,stroke:#333,stroke-width:2px,color:white,font-weight:bold;
    classDef storage fill:#f8f9fa,stroke:#666,stroke-width:2px,stroke-dasharray: 5 5;
    classDef backend fill:#fff3cd,stroke:#d6a519,stroke-width:2px;
    classDef db fill:#d1e7dd,stroke:#0f5132,stroke-width:2px;
    classDef frontend fill:#cfe2ff,stroke:#084298,stroke-width:2px;
    classDef process fill:#ffffff,stroke:#333,stroke-width:1px;

    subgraph CI_CD ["GitHub Actions (CI / Security / CD)"]
        direction TB
        A1([Workflow 시작]) --> A2[보안 도구 실행\n(Trivy, Bandit, Cosign 등)];
        A2 --> A3[결과 JSON/SARIF 생성];
        A3 --> A4[[upload-artifact 액션 실행]];
    end
    class A1,A2,A3,A4 ghActions;

    subgraph GH_Cloud ["GitHub Cloud"]
        B1[(Artifact 저장소\nJSON 파일들)];
    end
    class B1 storage;

    A4 -.->|업로드| B1;

    subgraph Backend_System ["Backend (Flask API)"]
        direction TB
        C1(Polling / Webhook 트리거) --> C2[① Run 정보 조회\n(GitHub API)];
        C2 --> C3[② Artifact 목록 조회\n(GitHub API)];
        C3 --> C4[③ 특정 Artifact 다운로드\n(GitHub API)];
        C4 --> C5[④ JSON 파싱 & ⑤ 정규화];
        C5 --> C6[(DB 저장\nPostgreSQL/SQLite)];
    end
    class C1,C2,C3,C4,C5 process;
    class C6 db;

    B1 -.->|다운로드| C4;

    subgraph Frontend_System ["Frontend (Next.js)"]
        D1[대시보드 UI\n(요약/이력/상세)];
    end
    class D1 frontend;

    C6 <==>|데이터 조회| D1;

    %% 전체적인 흐름 설명
    linkStyle 4,8 stroke:#d6a519,stroke-width:2px,color:#d6a519;
```

---

## 3-2. 보안 스캔 데이터 수집 구조 (핵심 설계)

GitHub API는 workflow 실행의 성공/실패(conclusion) 정보만 제공하며,
보안 도구(Trivy, Bandit 등)의 상세 결과는 반환하지 않는다.

따라서 본 시스템은 **GitHub Artifact API 기반 수집 구조**를 채택한다.

### 데이터 수집 흐름

1. GitHub Actions에서 보안 도구 실행
2. JSON 결과 파일 생성
3. `upload-artifact` 액션으로 결과 업로드
4. Flask 서버가 다음 순서로 처리:

   ① Run 정보 조회
   ② Artifact 목록 조회
   ③ Artifact 다운로드
   ④ JSON 파싱
   ⑤ 정규화 후 DB 저장

---

# 4. 기능 정의

## 4-1. 대시보드 홈

### 표시 정보

* CI 최근 실행 상태
* Security 최근 실행 상태
* CD 최근 배포 상태
* 최근 실패 목록
* 전체 성공률

---

## 4-2. Pipeline 실행 이력

* 최근 실행 10~30건 표시
* 필터: CI / Security / CD
* 브랜치 필터
* 실행 시간 및 duration 표시
* GitHub 상세 링크 연결

---

## 4-3. 보안 결과 요약 페이지

### 수집 대상 도구

* Semgrep
* Bandit
* pip-audit
* Trivy
* Gitleaks

### 표시 항목

* Severity별 취약점 개수
* 도구별 이슈 개수
* 시크릿 탐지 여부
* 취약점 추이 그래프(Phase 2)

---

## 4-4. Deployment 정보 페이지

* 배포 환경(dev/prod)
* 배포 태그
* 이미지 digest
* Cosign 서명 여부
* Cosign 검증 여부
* SBOM 생성 여부
* HTTPS 헬스체크 결과

---

# 5. 데이터 모델 설계

## 5-1. WorkflowRun

| 필드            | 설명                 |
| ------------- | ------------------ |
| id            | GitHub Run ID      |
| workflow_name | CI / Security / CD |
| conclusion    | success / failure  |
| branch        | 브랜치                |
| commit_sha    | 커밋 해시              |
| started_at    | 시작 시간              |
| completed_at  | 종료 시간              |
| duration      | 실행 시간              |
| html_url      | GitHub 링크          |
| summary_json  | 정규화된 보안 결과         |

---

## 5-2. summary_json 구조 예시

```json
{
  "tools": {
    "trivy": { "critical": 0, "high": 2 },
    "bandit": { "high": 1 },
    "semgrep": { "findings": 12 },
    "pip_audit": { "vuln_packages": 2 },
    "gitleaks": { "leaks": 0 }
  },
  "supply_chain": {
    "sbom_generated": true,
    "cosign_signed": true,
    "cosign_verified": true
  }
}
```

---

# 6. API 설계

## GET /api/pipelines/summary

최근 실행 요약 반환

## GET /api/pipelines/runs

실행 이력 목록 반환

## POST /api/pipelines/sync

GitHub API 호출 후 최신 데이터 동기화

---

# 7. 데이터 수집 전략 (Polling → Webhook 고도화)

## Phase 1: Polling 기반 동기화 (MVP)

* Flask가 일정 주기로 GitHub API 호출
* 최근 N회 실행 데이터만 동기화
* Rate Limit 최소화를 위한 범위 제한

## Phase 2: Webhook 기반 Event-Driven 구조

* `workflow_run` 이벤트 수신
* 이벤트 발생 시에만 Artifact 수집
* 실시간성 확보 및 API 호출 최소화

---

# 8. 기술 스택

## Frontend

* Next.js (App Router)
* TypeScript
* Chart.js (확장)

## Backend

* Flask
* SQLAlchemy
* GitHub REST API
* GitHub Artifact API
* JSON/SARIF 파싱

## DevSecOps 도구

* Semgrep
* Bandit
* pip-audit
* Trivy
* Gitleaks
* Cosign
* SBOM 생성

## Infra

* Docker
* Docker Compose
* Nginx
* Certbot

---

# 9. 차별화 요소

1. Artifact 기반 보안 결과 수집 구조
2. DevSecOps 파이프라인 데이터 정규화
3. 이미지 digest 및 서명 검증 시각화
4. 보안 취약점 추이 분석 가능
5. Polling → Webhook 아키텍처 고도화 전략 포함

---

# 10. 개발 단계 계획

## Phase 1

* Artifact 수집 로직 구현
* WorkflowRun 모델 구현
* Dashboard MVP UI

## Phase 2

* 취약점 추이 그래프
* Deployment 타임라인
* Webhook 연동

## Phase 3

* Slack 알림
* Kubernetes 연동 확장

---

# 11. 기대 효과

* DevSecOps 파이프라인 이해도 향상
* 보안 게이트 운영 경험 축적
* 공급망 보안(Supply Chain Security) 실무 감각 확보
* 실전형 DevSecOps 포트폴리오 구축

---

이 기획서는
**“GitHub Actions 상태 조회 서비스”가 아니라
“Artifact 기반 DevSecOps 데이터 수집·정규화·시각화 시스템”**이라는 점을 명확히 보여주는 구조입니다.
