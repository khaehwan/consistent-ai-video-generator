# 라즈베리파이 웨어러블 센서 - VP 서버 연결 가이드

## 1. 설정 파일 수정

`config.yaml` 파일을 열고 WebSocket URL을 VP 서버 주소로 변경하세요:

```yaml
# API Configuration
api:
    # 기존 HTTP API (백업용)
    base_url: "http://localhost:8000"

    # WebSocket settings for real-time VP communication
    websocket:
        # VP 서버가 같은 네트워크에 있는 경우
        url: "ws://<VP_SERVER_IP>:8001/vp/sensor-events"

        # 예시:
        # url: "ws://192.168.0.100:8001/vp/sensor-events"  # 로컬 네트워크
        # url: "ws://localhost:8001/vp/sensor-events"      # 같은 기기

        reconnect_delay: 5    # 재연결 대기 시간 (초)
        ping_interval: 30     # 핑 주기 (초)
```

## 2. 필수 패키지 설치

라즈베리파이에서 WebSocket 클라이언트 패키지를 설치하세요:

```bash
pip install websocket-client
```

## 3. VP API 서버 실행

VP 서버를 실행 중인 컴퓨터에서:

```bash
cd virtual-production/api
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**중요**: `--host 0.0.0.0`으로 실행해야 외부에서 접속 가능합니다.

## 4. 네트워크 설정 확인

### 4.1 VP 서버 IP 확인

VP 서버를 실행 중인 컴퓨터에서:

```bash
# macOS/Linux
ifconfig | grep "inet "

# Windows
ipconfig
```

예: `192.168.0.100`

### 4.2 라즈베리파이에서 연결 테스트

```bash
# VP 서버 연결 테스트
ping 192.168.0.100

# WebSocket 포트 확인
curl http://192.168.0.100:8001/health
```

성공하면 `{"status": "healthy"}` 응답이 옵니다.

## 5. 라즈베리파이 웨어러블 센서 실행

```bash
cd virtual-production/wearable-rpi
python main.py
```

### 실행 로그 예시

```
Configuration loaded from config.yaml
Wearable Sensor Application initialized
Initializing system components...
API client initialized
VP WebSocket client initialized
Behavior detector initialized
Starting Wearable Sensor System...
VP WebSocket connection started
Connecting to WebSocket: ws://192.168.0.100:8001/vp/sensor-events
WebSocket connected
System started successfully
```

## 6. 연결 확인

### 라즈베리파이에서 확인
- LED 매트릭스에 "READY" 메시지 표시
- 로그에 "WebSocket connected" 메시지

### VP 웹 플레이어에서 확인
1. 브라우저에서 `http://<VP_SERVER_IP>:5173` 접속
2. 상단 상태 바에서 "서버: 연결됨" 표시 확인
3. "컨트롤 보기" 클릭 → "행동 시뮬레이션"으로 테스트

**참고**:
- **서버: 연결됨** - VP API 서버와의 연결 상태
- **센서: 활성/비활성** - 실제 센서 데이터 수신 여부 (5초 이내 이벤트)

## 7. 동작 테스트

라즈베리파이를 움직여서 센서 이벤트 발생:

1. **걷기**: 천천히 위아래로 흔들기
   - VP 플레이어에서 배경이 "walk" 영상으로 전환

2. **달리기**: 빠르게 흔들기
   - VP 플레이어에서 배경이 "run" 영상으로 전환

3. **낙상**: 빠르게 아래로 떨어뜨리기
   - VP 플레이어에서 배경이 "fall" 영상으로 전환

4. **정지**: 가만히 두기
   - VP 플레이어에서 배경이 "stop" 영상으로 전환

### 센서 이벤트 디스플레이

VP 웹 플레이어 우측 하단의 "센서 이벤트" 패널에서:
- 시간, 행동 종류, 메타데이터 확인
- 실시간으로 이벤트 추가 확인

## 8. 트러블슈팅

### WebSocket 연결 실패

**증상**: "WebSocket disconnected. Reconnecting..." 반복

**해결**:
1. VP 서버가 실행 중인지 확인
   ```bash
   curl http://<VP_SERVER_IP>:8001/health
   ```

2. 방화벽 확인
   ```bash
   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

   # 포트 8001 허용
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/uvicorn
   ```

3. `config.yaml`의 WebSocket URL 확인
   - IP 주소가 맞는지
   - 포트 번호가 8001인지
   - `ws://`로 시작하는지 (`wss://` 아님)

### 센서 이벤트가 전송되지 않음

**증상**: WebSocket은 연결되지만 이벤트가 안 보임

**해결**:
1. 라즈베리파이 로그 확인
   ```bash
   # 이벤트 전송 로그 확인
   tail -f logs/events.log
   ```

2. VP 서버 로그 확인
   - uvicorn 실행 터미널에서 WebSocket 메시지 확인

3. 매핑 파일 확인
   ```bash
   # VP 서버에서
   cat {WORK_DIR}/{ENTITY_SET_NAME}/virtual-production/mappings/action_mapping.json
   ```
   - 매핑이 없으면 배경이 전환되지 않음

### 배경 영상이 없음

**증상**: "No background found" 또는 빈 화면

**해결**:
1. 배경 생성 API 실행 확인
   ```python
   import requests

   # 1. 씬 분석
   requests.post("http://localhost:8001/vp/analyze-scenes", ...)

   # 2. 배경 생성
   requests.post("http://localhost:8001/vp/generate-backgrounds", ...)

   # 3. 매핑 생성
   requests.post("http://localhost:8001/vp/generate-mapping", ...)
   ```

2. 생성된 파일 확인
   ```bash
   ls {WORK_DIR}/{ENTITY_SET_NAME}/virtual-production/backgrounds/
   ```

## 9. 고급 설정

### 자동 재연결 설정

`config.yaml`:
```yaml
websocket:
    reconnect_delay: 3    # 빠른 재연결 (3초)
    ping_interval: 20     # 자주 연결 확인 (20초)
```

### 오프라인 모드

네트워크 연결이 불안정한 경우, 오프라인 저장 활성화:

```yaml
system:
    offline_storage: true
    offline_storage_path: "data/offline_events.json"
```

- 연결이 끊기면 이벤트를 로컬에 저장
- 연결이 복구되면 자동으로 전송

### 디바이스 식별

여러 센서를 사용하는 경우:

```yaml
system:
    device_id: "rpi_wearable_001"    # 각 센서마다 고유 ID
    location: "studio_A"              # 위치 정보
```

## 10. 실전 사용 워크플로우

### 촬영 준비

1. **VP 서버 시작**
   ```bash
   cd virtual-production/api
   python -m uvicorn main:app --host 0.0.0.0 --port 8001
   ```

2. **웹 플레이어 시작**
   ```bash
   cd virtual-production/frontend
   npm run dev
   ```
   → 브라우저: `http://localhost:5173`

3. **배경 영상 생성** (최초 1회)
   - Python API로 씬 분석 → 배경 생성 → 매핑 생성

4. **라즈베리파이 착용**
   ```bash
   cd virtual-production/wearable-rpi
   python main.py
   ```

### 촬영 시작

1. 웹 플레이어에서 "WebSocket: 연결됨" 확인
2. 초기 씬 선택 (필요시)
3. 배우가 센서를 착용하고 연기 시작
4. 배경이 자동으로 전환됨

### 촬영 종료

1. 라즈베리파이: `Ctrl+C`
2. LED에 "BYE" 표시 후 종료

## 참고

- VP API 문서: `http://localhost:8001/docs`
- 전체 문서: `virtual-production/README.md`
- 센서 상세: `virtual-production/wearable-rpi/README.md`
