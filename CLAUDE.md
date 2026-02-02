# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

실시간 시스템 리소스 모니터링을 위한 Python 기반 메트릭 수집 에이전트. Prometheus 형식으로 CPU, 메모리, 디스크, 네트워크, 프로세스 메트릭을 수집하여 HTTP 엔드포인트(/metrics)로 노출합니다.

**핵심 요구사항:**
- 에이전트 자체 리소스 사용량: CPU < 2%, Memory < 50MB
- 메트릭 수집 지연 < 1초
- 5개 수집기: CPU(5초), Memory(5초), Disk(5/30초), Network(5초), Process(10초)

## 실행 및 개발 명령어

### 에이전트 실행
```bash
# 기본 설정으로 실행
python run_agent.py

# 설정 파일 지정
python run_agent.py --config config/agent.yaml

# 로그 레벨 변경
python run_agent.py --log-level DEBUG

# 환경 변수로 설정 오버라이드
export PROMETHEUS_PORT=9200
export LOG_LEVEL=DEBUG
export COLLECTOR_PROCESS_ENABLED=false
python run_agent.py
```

### 개발 도구
```bash
# 의존성 설치
pip install -r requirements.txt        # 프로덕션
pip install -r requirements-dev.txt    # 개발

# 테스트
pytest tests/                          # 전체 테스트
pytest tests/test_collectors/         # 수집기 테스트만
pytest --cov=src --cov-report=html    # 커버리지

# 코드 품질
black src/                             # 포맷팅
flake8 src/                            # 린팅
mypy src/                              # 타입 체크
```

### 메트릭 확인
```bash
# HTTP 엔드포인트 (기본 포트 9100)
curl http://localhost:9100/metrics

# Prometheus 쿼리 예시
# CPU 사용률: avg_over_time(cpu_usage_percent[5m])
# Top 5 프로세스: topk(5, process_cpu_percent)
# 디스크 읽기 속도: rate(disk_io_read_bytes_total[5m])
```

## 아키텍처

### 3계층 구조

1. **Agent 레이어** (`src/agent.py`)
   - 수집기 오케스트레이션 및 스케줄링
   - 각 수집기를 독립적인 스레드로 실행 (interval 기반)
   - Prometheus HTTP 서버 라이프사이클 관리
   - 자체 모니터링 스레드 (CPU/메모리 제한 체크)
   - 신호 처리 (SIGINT, SIGTERM) 및 graceful shutdown

2. **Collector 레이어** (`src/collectors/`)
   - **BaseCollector**: 추상 클래스, 에러 핸들링 및 상태 추적
     - `collect()`: 메트릭 수집 로직 (서브클래스 구현)
     - `register_metrics(registry)`: Prometheus 메트릭 등록
     - `run_collection()`: 타이밍 및 에러 핸들링 래퍼
     - `is_healthy()`: 연속 실패 3회 시 unhealthy

   - **개별 수집기**: BaseCollector 상속
     - `CPUCollector`: psutil.cpu_percent(), cpu_times(), getloadavg()
     - `MemoryCollector`: psutil.virtual_memory(), swap_memory()
     - `DiskCollector`: disk_partitions(), disk_usage(), disk_io_counters()
       - **중요**: I/O 레이트 계산을 위해 이전 카운터 상태 저장 (`prev_io_counters`)
     - `NetworkCollector`: net_io_counters(), net_connections()
       - **중요**: 레이트 계산을 위해 이전 카운터 상태 저장 (`prev_net_counters`)
     - `ProcessCollector`: process_iter()로 전체 프로세스 조회 후 CPU/메모리 상위 N개 추출
       - **주의**: 높은 카디널리티로 인한 메모리 사용 증가 가능

3. **Exporter 레이어** (`src/exporters/prometheus_exporter.py`)
   - Prometheus HTTP 서버 (prometheus_client 사용)
   - `/metrics` 엔드포인트 노출 (기본 포트 9100)
   - 에이전트 자체 메트릭 관리:
     - `agent_collector_last_success_timestamp`
     - `agent_collector_errors_total`
     - `agent_collector_duration_seconds`
     - `agent_collector_status` (1=healthy, 0=unhealthy)

### 설정 시스템 (`src/config/settings.py`)

**우선순위**: 환경 변수 > YAML 파일 > 기본값

- `load_config(path)`: YAML 로드 → 환경 변수 오버라이드 → 검증
- `override_from_env()`: `PROMETHEUS_PORT`, `LOG_LEVEL`, `COLLECTOR_<NAME>_ENABLED` 등
- `validate_config()`: 포트 범위, 간격 양수, top_n 범위 등 검증

환경 변수 규칙:
- `PROMETHEUS_*`: Prometheus 설정
- `COLLECTOR_<NAME>_*`: 수집기별 설정 (예: `COLLECTOR_CPU_INTERVAL=10`)
- `LOG_LEVEL`, `LOG_FILE`, `LOG_FORMAT`: 로깅 설정

### 스레딩 모델

```
Main Thread
├─ Prometheus HTTP Server (daemon thread, prometheus_client 내부)
├─ Collector Thread: CPU (interval=5s loop)
├─ Collector Thread: Memory (interval=5s loop)
├─ Collector Thread: Disk (interval=5s loop)
├─ Collector Thread: Network (interval=5s loop)
├─ Collector Thread: Process (interval=10s loop)
└─ Self-Monitor Thread (interval=60s, CPU/메모리 체크)
```

각 수집기 스레드는 `_run_collector_loop()`에서 독립 실행:
- `collector.run_collection()` 호출
- `exporter.update_agent_metrics()` 호출
- `time.sleep(interval)` 대기

## 새 수집기 추가하기

1. `src/collectors/new_collector.py` 생성:
   ```python
   from prometheus_client import Gauge, Counter
   from src.collectors.base import BaseCollector

   class NewCollector(BaseCollector):
       def register_metrics(self, registry):
           self.my_metric = Gauge('my_metric', 'Description', registry=registry)

       def collect(self):
           # psutil 등으로 데이터 수집
           value = get_some_data()
           self.my_metric.set(value)
   ```

2. `src/agent.py`의 `_init_collectors()`에 등록:
   ```python
   collector_classes = {
       'cpu': CPUCollector,
       # ... 기존 수집기들
       'new': NewCollector,  # 추가
   }
   ```

3. `config/agent.example.yaml`에 설정 추가:
   ```yaml
   collectors:
     new:
       enabled: true
       interval: 5
   ```

4. 테스트 작성: `tests/test_collectors/test_new_collector.py`

## 메트릭 타입 선택 가이드

- **Gauge**: 증가/감소 가능한 값 (CPU %, 메모리 사용량, 연결 수)
- **Counter**: 단조 증가하는 누적값 (총 바이트 수, 총 작업 수)
  - Prometheus에서 `rate()` 함수로 초당 변화율 계산
  - 에이전트 내부에서 레이트 계산하지 말 것 (DiskCollector, NetworkCollector는 이전 값 저장만)

## 중요한 제약사항

### 리소스 제한
- 에이전트 CPU 사용률 2% 초과 시: `resource_limits.action_on_exceed` 동작 (log/disable_collectors/stop)
- 메모리 50MB 초과 시: 동일
- ProcessCollector가 가장 많은 리소스 사용 → `top_n` 값 조정 또는 비활성화

### 플랫폼 차이 처리
- `psutil.getloadavg()`: Unix 계열만 지원, Windows는 AttributeError
  - CPUCollector에서 `hasattr()` 체크 및 예외 처리
- 메모리 캐시: Linux는 `cached`, macOS는 `buffers` 속성
- 네트워크 연결 상태: Windows에서 관리자 권한 필요할 수 있음

### 에러 핸들링 패턴
- `psutil.AccessDenied`: DEBUG 레벨 로깅 (예상된 상황)
- `psutil.NoSuchProcess`: 프로세스 종료됨, 무시
- 일반 Exception: ERROR 레벨, 연속 3회 실패 시 수집기 unhealthy

## 설정 우선순위 예시

```yaml
# config/agent.yaml
collectors:
  cpu:
    interval: 5
```

```bash
export COLLECTOR_CPU_INTERVAL=10  # 환경 변수가 YAML보다 우선
```

최종 결과: `cpu.interval = 10`

## Prometheus 통합

### Scrape 설정
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'system-metrics-agent'
    scrape_interval: 15s  # 수집기 interval보다 길게 설정 권장
    static_configs:
      - targets: ['localhost:9100']
```

### 유용한 PromQL 쿼리
```promql
# 메트릭 수집 실패 감지
increase(agent_collector_errors_total[5m]) > 0

# 수집기 상태 확인 (0이면 unhealthy)
agent_collector_status

# 네트워크 수신 속도 (bytes/s)
rate(network_receive_bytes_total{interface!="lo"}[5m])

# 디스크 I/O 대기 (iowait가 높으면 디스크 병목)
cpu_time_seconds{mode="iowait"}
```

## 문서 참조

- **PRD**: `docs/README.md` - 전체 시스템 요구사항 및 로드맵
- **사용자 가이드**: `README.md` - 설치, 실행, 트러블슈팅
- **설정 예시**: `config/agent.example.yaml` - 모든 설정 옵션

## 주의사항

1. **절대 BaseCollector 없이 직접 Prometheus 메트릭 업데이트하지 말 것**
   - 에러 핸들링, 타이밍, 상태 추적 기능 누락

2. **Counter 메트릭은 `.inc()` 사용, 절대 `.set()` 사용 금지**
   - Counter는 단조 증가만 가능

3. **높은 카디널리티 레이블 주의**
   - ProcessCollector의 pid 레이블: 수천 개 프로세스 시 메모리 문제
   - `top_n` 값으로 제한

4. **스레드 안전성**
   - Prometheus 메트릭 업데이트는 thread-safe
   - 수집기 내부 상태 (`prev_io_counters` 등)는 단일 스레드에서만 접근

5. **Graceful Shutdown**
   - SIGTERM/SIGINT 수신 시 `agent.stop()` 호출
   - 모든 수집기 스레드 종료 대기 (5초 timeout)
   - HTTP 서버 종료
