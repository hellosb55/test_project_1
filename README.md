# Metrics Collection Agent

실시간 시스템 리소스 모니터링을 위한 Python 기반 메트릭 수집 에이전트입니다.

## 기능

- **CPU 메트릭**: 사용률, 코어별 사용률, 로드 평균, CPU 시간 분석
- **메모리 메트릭**: 물리 메모리 및 스왑 메모리 사용량
- **디스크 메트릭**: 파티션별 사용량, I/O 성능
- **네트워크 메트릭**: 인터페이스별 트래픽, 연결 상태
- **프로세스 메트릭**: Top N 프로세스 CPU/메모리 사용량

## 요구사항

- Python 3.9 이상
- 지원 OS: Linux, macOS, Windows

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 설정 파일 생성 (선택사항)

```bash
cp config/agent.example.yaml config/agent.yaml
# config/agent.yaml 파일을 수정하여 설정 변경
```

## 실행

### 기본 실행 (기본 설정 사용)

```bash
python run_agent.py
```

### 설정 파일 지정

```bash
python run_agent.py --config config/agent.yaml
```

### 로그 레벨 변경

```bash
python run_agent.py --log-level DEBUG
```

### 도움말

```bash
python run_agent.py --help
```

## 설정

### 설정 파일 (YAML)

설정 파일 예시는 `config/agent.example.yaml`을 참고하세요.

주요 설정 항목:

- **agent**: 에이전트 기본 설정 (호스트명, 로그 레벨 등)
- **prometheus**: Prometheus HTTP 서버 설정 (포트, 바인드 주소)
- **collectors**: 각 수집기 활성화 및 간격 설정
- **resource_limits**: 에이전트 자체 리소스 제한

### 환경 변수

설정 파일 대신 환경 변수로도 설정 가능합니다:

```bash
# Prometheus 포트 변경
export PROMETHEUS_PORT=9200

# 로그 레벨 변경
export LOG_LEVEL=DEBUG

# CPU 수집 간격 변경
export COLLECTOR_CPU_INTERVAL=10

# Process 수집기 비활성화
export COLLECTOR_PROCESS_ENABLED=false
```

## Prometheus 연동

### Scrape 설정

`prometheus.yml`에 다음 설정 추가:

```yaml
scrape_configs:
  - job_name: 'system-metrics-agent'
    scrape_interval: 15s
    static_configs:
      - targets:
          - 'localhost:9100'
        labels:
          environment: 'production'
```

### 메트릭 확인

에이전트 시작 후 브라우저에서 접속:

```
http://localhost:9100/metrics
```

## 수집되는 메트릭

### CPU 메트릭

- `cpu_usage_percent`: 전체 CPU 사용률
- `cpu_usage_percent_per_core{core}`: 코어별 CPU 사용률
- `cpu_load_average{period}`: 로드 평균 (1m, 5m, 15m)
- `cpu_time_seconds{mode}`: CPU 시간 (user, system, idle, iowait)

### 메모리 메트릭

- `memory_total_bytes`: 전체 메모리
- `memory_used_bytes`: 사용 중인 메모리
- `memory_available_bytes`: 사용 가능한 메모리
- `memory_cached_bytes`: 캐시된 메모리
- `memory_usage_percent`: 메모리 사용률
- `swap_total_bytes`: 전체 스왑
- `swap_used_bytes`: 사용 중인 스왑
- `swap_usage_percent`: 스왑 사용률

### 디스크 메트릭

- `disk_usage_bytes{mount_point, type}`: 디스크 사용량
- `disk_usage_percent{mount_point}`: 디스크 사용률
- `disk_io_read_bytes_total{device}`: 읽기 바이트 (Counter)
- `disk_io_write_bytes_total{device}`: 쓰기 바이트 (Counter)
- `disk_io_read_operations_total{device}`: 읽기 작업 수
- `disk_io_write_operations_total{device}`: 쓰기 작업 수

### 네트워크 메트릭

- `network_receive_bytes_total{interface}`: 수신 바이트 (Counter)
- `network_transmit_bytes_total{interface}`: 송신 바이트 (Counter)
- `network_receive_packets_total{interface}`: 수신 패킷
- `network_transmit_packets_total{interface}`: 송신 패킷
- `network_receive_errors_total{interface}`: 수신 에러
- `network_transmit_errors_total{interface}`: 송신 에러
- `network_connections{state}`: 연결 상태별 개수

### 프로세스 메트릭

- `process_cpu_percent{pid, name, user}`: 프로세스 CPU 사용률
- `process_memory_bytes{pid, name, user}`: 프로세스 메모리 (RSS)
- `process_runtime_seconds{pid, name, user}`: 프로세스 실행 시간

### 에이전트 자체 메트릭

- `agent_info{version, hostname}`: 에이전트 정보
- `agent_collector_last_success_timestamp{collector}`: 마지막 성공 시각
- `agent_collector_errors_total{collector}`: 수집 에러 횟수
- `agent_collector_duration_seconds{collector}`: 수집 소요 시간
- `agent_collector_status{collector}`: 수집기 상태 (1=정상, 0=비정상)

## PromQL 쿼리 예시

### CPU 사용률 (최근 5분 평균)

```promql
avg_over_time(cpu_usage_percent[5m])
```

### 메모리 사용률

```promql
memory_usage_percent
```

### 디스크 읽기 속도 (bytes/s)

```promql
rate(disk_io_read_bytes_total[5m])
```

### 네트워크 수신 속도 (bytes/s)

```promql
rate(network_receive_bytes_total{interface="eth0"}[5m])
```

### Top 5 프로세스 (CPU 기준)

```promql
topk(5, process_cpu_percent)
```

### Top 5 프로세스 (메모리 기준)

```promql
topk(5, process_memory_bytes)
```

## 트러블슈팅

### 포트가 이미 사용 중입니다

다른 포트로 변경:

```bash
export PROMETHEUS_PORT=9200
python run_agent.py
```

### Permission denied 에러

일부 메트릭은 관리자 권한이 필요할 수 있습니다:

```bash
# Linux/Mac
sudo python run_agent.py

# Windows (관리자 권한으로 CMD/PowerShell 실행)
python run_agent.py
```

### 특정 수집기 비활성화

설정 파일에서 `enabled: false` 설정 또는:

```bash
export COLLECTOR_PROCESS_ENABLED=false
```

### 메모리 사용량이 높습니다

프로세스 수집기의 top_n 값을 줄이거나 비활성화:

```yaml
collectors:
  process:
    enabled: false
```

## 개발

### 개발 의존성 설치

```bash
pip install -r requirements-dev.txt
```

### 테스트 실행

```bash
pytest tests/
```

### 코드 포맷팅

```bash
black src/
```

### Linting

```bash
flake8 src/
```

## 라이센스

MIT License

## 기여

이슈 및 Pull Request를 환영합니다!

## 관련 문서

- [PRD (Product Requirements Document)](docs/README.md)
- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [psutil 문서](https://psutil.readthedocs.io/)
