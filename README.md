# DevSecOps Lab Dashboard

GitHub Actions 기반 CI/Security/CD 실행 결과와 보안 산출물(artifact)을 수집해 대시보드로 보여주는 모노레포 프로젝트입니다.

## 1. 프로젝트 구성

- `apps/web`: Next.js 14 + TypeScript 대시보드
- `apps/api`: Flask API (수집/집계/조회)
- `infra/docker`: 로컬/운영 docker compose
- `infra/nginx`: Nginx 템플릿

## 2. 현재 아키텍처(구현 기준)

```text
GitHub Actions runs + artifacts
            |
            v
Flask API (/api/pipelines/sync 또는 polling)
            |
            v
SQLite (workflow_runs.db)
            |
            v
Next.js Dashboard
```

백엔드 init 흐름:

- `create_app()`에서 config 적용, blueprint 등록, polling 시작
- `PipelineService` 생성은 `app.extensions["pipeline_service_factory"]`로 단일화
- routes/poller는 공통 factory를 사용

## 3. 주요 기능

### 3.1 Pipeline 상태/이력

- CI / Security / CD 상태 카드
- 실행 이력 목록
- 필터: `category`, `branch`
- 페이지네이션

### 3.2 Security 요약

- artifact(JSON/SARIF) 파싱 후 `summary_json` 저장
- severity 합계(critical/high/medium/low/unknown)
- 도구별 집계(trivy/bandit/semgrep/pip_audit/gitleaks)
- secret leak 탐지 여부(gitleaks 기반)

### 3.3 Security 추이

- 최근 N일(기본 14일) findings 추이 API
- 대시보드에서 막대 그래프로 렌더링

### 3.4 Deployment 정보

- 최신 CD 실행 정보(시간 기준 최신 run 선택)
- environment(prod/dev) 추정
- supply chain 신호:
  - `sbom_generated`
  - `cosign_signed`
  - `cosign_verified`
  - `https_ok`
  - `image_digest`
  - `image_tag`

### 3.5 수집 방식

- 수동 sync: `POST /api/pipelines/sync`
- 자동 polling: 환경변수 기반 주기 동기화

## 4. 데이터 저장소

- 기본 저장소: SQLite (`workflow_runs.db`)
- 레거시 JSON(`workflow_runs.json`)이 있으면 DB가 비어 있을 때 1회 자동 이관

## 5. API 명세

- `GET /api/pipelines/runs`
  - query: `limit`, `page`, `category`, `branch`
- `GET /api/pipelines/summary`
- `GET /api/pipelines/deployment`
- `GET /api/pipelines/security-trends?days=14`
- `POST /api/pipelines/sync`
  - header: `X-Sync-Token`

## 6. 로컬 실행

### 6.1 전체 스택

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

- Nginx: `http://localhost:8080`
- Web: `http://localhost:3000` (컨테이너 내부 expose)
- API: `http://localhost:5000` (컨테이너 내부 expose)

### 6.2 개별 실행

```bash
# API
cd apps/api
pip install -r requirements.txt
python src/main.py

# Web
cd apps/web
npm install
npm run dev
```

## 7. 테스트

### 7.1 API 테스트(로컬)

```bash
cd apps/api
pytest tests
```

### 7.2 API 테스트(Docker compose)

`infra/docker/docker-compose.yml`에는 `api` 컨테이너에서 테스트 실행 가능하도록 아래를 마운트합니다.

- `../../apps/api/tests:/app/tests:ro`
- `../../apps/api/pytest.ini:/app/pytest.ini:ro`

실행:

```bash
docker compose -f infra/docker/docker-compose.yml exec -T api pytest tests
```

## 8. 환경변수

`.env.example` 기준 핵심 값:

- GitHub:
  - `GITHUB_OWNER`
  - `GITHUB_REPO`
  - `GITHUB_TOKEN`
  - `SYNC_TOKEN`
- Storage:
  - `RUNS_STORAGE_PATH` (기본: `apps/api/data/workflow_runs.db`)
  - `RUNS_LEGACY_JSON_PATH` (기본: `apps/api/data/workflow_runs.json`)
- Polling:
  - `POLLING_ENABLED` (기본 `true`)
  - `POLLING_INTERVAL_SECONDS` (기본 `300`, 최소 `30`)
  - `POLLING_PER_PAGE` (기본 `30`, 최대 `100`)

## 9. 운영 참고

- 현재 sync는 "최신 N건 fetch 후 저장" 방식입니다.
  - N은 `per_page` 또는 `POLLING_PER_PAGE`
  - 전체 히스토리 누적 저장이 필요하면 upsert + pagination 확장 필요
- `DOMAIN` 미설정 경고는 일부 compose 실행에서 출력될 수 있음(기능 치명도 낮음)

## 10. 미구현/확장 예정

- webhook 기반 event-driven 수집
- Slack 알림 연동
- 고도화된 시각화(도구별 추이, 기간 비교)
- 운영 환경에서의 외부 스케줄러 분리(멀티 워커 중복 호출 방지 고도화)
