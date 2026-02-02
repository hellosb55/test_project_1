# 개발 계획 (Development Plan)

## 프로젝트 개요
실시간 시스템 리소스 모니터링 에이전트 개발 프로젝트

**목표**: Prometheus 형식으로 시스템 메트릭을 수집하고 HTTP 엔드포인트로 노출하는 경량 모니터링 에이전트 구축

---

## Phase 1: MVP - 메트릭 수집 에이전트 (Week 1-4)

### Week 1: 프로젝트 구조 및 기본 수집기 구현
- [x] 프로젝트 초기 설정 (디렉토리 구조, 의존성 관리)
- [x] BaseCollector 추상 클래스 설계
  - 에러 핸들링 프레임워크
  - 상태 추적 (healthy/unhealthy)
  - 메트릭 등록 인터페이스
- [x] CPU 수집기 구현
  - CPU 사용률 (user, system, idle, iowait)
  - CPU 로드 평균 (1분, 5분, 15분)
  - 코어별 사용률
- [x] 메모리 수집기 구현
  - 물리 메모리 (total, used, available, cached/buffers)
  - 스왑 메모리 (total, used, usage%)
- [x] 유닛 테스트 작성 (pytest)

### Week 2: 고급 수집기 구현
- [x] 디스크 수집기 구현
  - 디스크 사용량 (파티션별)
  - 디스크 I/O 메트릭 (읽기/쓰기 바이트, IOPS)
  - 레이트 계산 로직 (이전 카운터 상태 저장)
- [x] 네트워크 수집기 구현
  - 인터페이스별 트래픽 (수신/송신 바이트, 패킷)
  - 연결 상태 통계 (ESTABLISHED, TIME_WAIT 등)
  - 레이트 계산 로직
- [x] 프로세스 수집기 구현
  - Top N 프로세스 (CPU/메모리 기준)
  - 프로세스별 메트릭 (PID, 이름, CPU%, 메모리, 사용자)
- [x] 통합 테스트 작성

### Week 3: Prometheus 통합 및 에이전트 오케스트레이션
- [x] Prometheus Exporter 구현
  - HTTP 서버 설정 (기본 포트 9100)
  - `/metrics` 엔드포인트
  - 에이전트 자체 메트릭 노출
    - `agent_collector_last_success_timestamp`
    - `agent_collector_errors_total`
    - `agent_collector_duration_seconds`
    - `agent_collector_status`
- [x] Agent 오케스트레이터 구현
  - 수집기 스레드 관리 (독립적인 간격으로 실행)
  - Graceful shutdown (SIGINT/SIGTERM 처리)
  - 자체 모니터링 스레드 (CPU/메모리 제한 체크)
- [x] 설정 시스템 구현
  - YAML 기반 설정 파일
  - 환경 변수 오버라이드
  - 설정 검증 로직

### Week 4: 최적화 및 크로스 플랫폼 지원
- [x] 리소스 최적화
  - 에이전트 자체 CPU 사용률 < 2%
  - 메모리 사용량 < 50MB
  - ProcessCollector 카디널리티 제한 (top_n)
- [x] 크로스 플랫폼 호환성
  - Linux, macOS, Windows 지원
  - 플랫폼별 예외 처리 (getloadavg, 메모리 캐시 속성 등)
- [x] 에러 핸들링 강화
  - AccessDenied, NoSuchProcess 등 예상 에러 처리
  - 연속 실패 감지 및 unhealthy 상태 전환
- [x] 코드 품질 개선
  - Black 포맷팅
  - Flake8 린팅
  - Mypy 타입 체크
  - 테스트 커버리지 > 80%

---

## Phase 2: 기능 확장 (Week 5-8)

### Week 5: 알림 시스템 구현
- [x] 알림 규칙 엔진 개발
  - 임계값 기반 조건 평가 (>, <, >=, <=, ==, !=)
  - 지속 시간 조건 (for_duration_minutes)
  - 알림 빈도 제한 (cooldown_minutes)
- [x] 알림 채널 구현
  - 이메일 전송 (SMTP with TLS/SSL, HTML 템플릿)
  - Slack Webhook 통합 (rich formatting, @channel mention)
  - 커스텀 Webhook (JSON payload, custom headers)
- [x] 알림 이력 저장
  - SQLite 스키마 구현 (WAL 모드, 인덱싱)
  - 발생/해결 시간 추적 (triggered_at, resolved_at)
  - 알림 상태 관리 (triggered, active, resolved)

### Week 6: 백엔드 API 개발
- [ ] FastAPI 또는 Express 기반 REST API
  - `/api/metrics/{metric_type}` - 메트릭 조회
  - `/api/status` - 현재 상태 조회
  - `/api/alerts/rules` - 알림 규칙 CRUD
  - `/api/alerts/history` - 알림 이력 조회
- [ ] 인증/인가 구현 (JWT 또는 API Key)
- [ ] Rate Limiting (사용자당 1000 req/hour)
- [ ] Redis 캐싱 (5분 TTL)
- [ ] API 문서화 (OpenAPI/Swagger)

### Week 7: 프론트엔드 대시보드 개발
- [ ] React/Vue.js 기반 SPA
  - 메인 대시보드 (전체 시스템 상태)
  - 메트릭 상세 페이지 (CPU, 메모리, 디스크, 네트워크)
  - 프로세스 모니터링 페이지
  - 알림 관리 페이지
- [ ] 차트 라이브러리 통합 (Chart.js, Recharts, ECharts)
  - 실시간 라인 차트
  - 바 차트, 스택 차트
  - 시간 범위 선택기
- [ ] WebSocket 연결 (실시간 데이터 스트리밍)
- [ ] 반응형 디자인 (모바일 지원)
- [ ] 다크 모드 구현

### Week 8: 데이터 저장 및 쿼리 최적화
- [ ] 시계열 DB 통합 (Prometheus 또는 InfluxDB)
  - 데이터 보존 정책 설정 (24시간 Raw, 7일 중간, 30일 저해상도)
  - 자동 다운샘플링
- [ ] 쿼리 성능 최적화
  - 인덱싱 전략
  - 집계 쿼리 최적화
- [ ] 통합 테스트 및 부하 테스트
  - 동시 접속 100명 이상 지원 검증
  - API 응답 시간 < 500ms (p95) 검증

---

## Phase 3: 운영화 (Week 9-10)

### Week 9: 배포 자동화 및 문서화
- [ ] Docker 컨테이너화
  - Dockerfile 작성 (multi-stage build)
  - Docker Compose 구성 (에이전트, DB, 백엔드, 프론트엔드)
- [ ] Kubernetes 배포 매니페스트 (옵션)
  - Deployment, Service, ConfigMap
  - HPA (Horizontal Pod Autoscaler)
- [ ] CI/CD 파이프라인 구축
  - GitHub Actions 또는 GitLab CI
  - 자동 테스트 실행
  - 자동 배포
- [ ] 운영 문서 작성
  - 설치 가이드
  - 설정 가이드
  - 트러블슈팅 가이드
  - 아키텍처 다이어그램

### Week 10: 프로덕션 배포 및 모니터링
- [ ] 프로덕션 환경 배포
  - HTTPS 설정 (TLS 1.2+)
  - 보안 설정 (방화벽, 인증)
  - 백업 및 복구 계획
- [ ] 메타 모니터링 구축
  - 에이전트 자체 상태 모니터링
  - Health check 엔드포인트
  - 로그 집계 (구조화된 JSON 로그)
- [ ] 성능 튜닝
  - 리소스 사용량 최적화
  - DB 쿼리 최적화
- [ ] 사용자 가이드 작성
  - 사용자 매뉴얼
  - API 레퍼런스
  - FAQ

---

## 주요 마일스톤

| 마일스톤 | 목표 날짜 | 주요 산출물 |
|---------|----------|-----------|
| MVP 완료 | Week 4 | 메트릭 수집 에이전트, Prometheus 통합 |
| 알림 시스템 완료 | Week 5 | 이메일/Slack 알림, 규칙 엔진 |
| API 완료 | Week 6 | REST API, 인증, 캐싱 |
| 대시보드 완료 | Week 7 | React/Vue 대시보드, 실시간 차트 |
| 데이터 저장 완료 | Week 8 | 시계열 DB 통합, 쿼리 최적화 |
| 배포 준비 완료 | Week 9 | Docker, CI/CD, 문서화 |
| 프로덕션 배포 | Week 10 | 운영 환경 배포, 메타 모니터링 |

---

## 기술 스택 요약

### MVP (Phase 1)
- **언어**: Python 3.9+
- **수집 라이브러리**: psutil 5.9.8
- **메트릭 수출**: prometheus-client 0.20.0
- **설정 관리**: PyYAML 6.0.1
- **테스트**: pytest 8.0.0, pytest-cov, pytest-mock
- **코드 품질**: black, flake8, mypy

### Phase 2
- **백엔드**: FastAPI (Python) 또는 Express (Node.js)
- **프론트엔드**: React 또는 Vue.js
- **차트**: Chart.js, Recharts, 또는 ECharts
- **DB**: PostgreSQL/MySQL (메타데이터), Prometheus/InfluxDB (시계열)
- **캐싱**: Redis

### Phase 3
- **컨테이너**: Docker, Docker Compose
- **오케스트레이션**: Kubernetes (옵션)
- **CI/CD**: GitHub Actions, GitLab CI
- **로깅**: 구조화된 JSON 로그

---

## 성공 기준

### 기능 요구사항
- [x] 5개 메트릭 수집기 구현 (CPU, 메모리, 디스크, 네트워크, 프로세스)
- [x] Prometheus `/metrics` 엔드포인트 노출
- [ ] 알림 시스템 (이메일, Slack)
- [ ] REST API
- [ ] 실시간 대시보드

### 비기능 요구사항
- [x] 에이전트 CPU 사용률 < 2%
- [x] 에이전트 메모리 사용량 < 50MB
- [x] 메트릭 수집 지연 < 1초
- [ ] API 응답 시간 < 500ms (p95)
- [ ] 동시 접속 100명 이상 지원
- [ ] 코드 커버리지 > 80%

### 품질 요구사항
- [x] 크로스 플랫폼 지원 (Linux, macOS, Windows)
- [x] Graceful shutdown
- [x] 에러 핸들링 및 복구
- [ ] 자동화된 테스트 (Unit, Integration, E2E)
- [ ] CI/CD 파이프라인

---

## 위험 관리

| 위험 | 대응 방안 | 상태 |
|------|----------|------|
| 높은 카디널리티로 인한 메모리 과다 사용 | ProcessCollector top_n 제한, 레이블 최소화 | 완료 |
| 크로스 플랫폼 호환성 이슈 | 플랫폼별 예외 처리, hasattr() 체크 | 완료 |
| 에이전트 자체 리소스 초과 | 자체 모니터링 스레드, 리소스 제한 체크 | 완료 |
| 대량 메트릭으로 인한 DB 부하 | 다운샘플링, 보존 정책, 캐싱 | 진행 중 |
| 알림 폭주 (Alert Storm) | 알림 빈도 제한, 그룹핑 | 계획 단계 |

---

## 다음 단계 (Phase 2 시작)

1. **즉시**: 알림 규칙 엔진 설계 시작
2. **Week 5**: 이메일/Slack 알림 채널 구현
3. **Week 6**: FastAPI 기반 REST API 개발
4. **Week 7**: React 대시보드 개발 시작
