# Azure Kinect 자세 감지 시스템

Azure Kinect DK를 사용하여 사용자의 자세를 감지하고, Virtual Production 서버와 연동하여 실시간으로 배경 영상을 전환하는 시스템입니다.

## 기능

### 감지 가능한 자세

- **standing** (서있음): 사용자가 서있는 자세
- **sitting** (앉음): 사용자가 앉아있는 자세
- **lying** (누움): 사용자가 누워있는 자세
- **left_arm_up** (왼팔 들기): 왼팔을 어깨보다 높이 든 자세
- **right_arm_up** (오른팔 들기): 오른팔을 어깨보다 높이 든 자세

### 주요 특징

- **실시간 자세 감지**: Azure Kinect Body Tracking을 사용한 정확한 자세 인식
- **WebSocket 통신**: VP 서버와 실시간으로 연동
- **설정 가능한 감지 임계값**: 자세 감지 민감도 조절 가능
- **Debounce 기능**: 불필요한 자세 전환 방지
- **자동 재연결**: 네트워크 연결 끊김 시 자동으로 재연결

## 요구사항

### 하드웨어

- [Azure Kinect DK](https://azure.microsoft.com/en-us/products/kinect-dk/)
- Windows 10/11 (64-bit)
- USB 3.0 포트

### 소프트웨어

- Python 3.8 이상
- Azure Kinect SDK
- Azure Kinect Body Tracking SDK

## 설치

### 1. Azure Kinect SDK 설치

1. [Azure Kinect Sensor SDK](https://learn.microsoft.com/en-us/azure/kinect-dk/sensor-sdk-download)를 다운로드하여 설치
2. [Azure Kinect Body Tracking SDK](https://learn.microsoft.com/en-us/azure/kinect-dk/body-sdk-download)를 다운로드하여 설치

**설치 경로 (기본값):**
- Sensor SDK: `C:\Program Files\Azure Kinect SDK v1.4.1`
- Body Tracking SDK: `C:\Program Files\Azure Kinect Body Tracking SDK`

### 2. 환경 변수 설정

시스템 환경 변수에 다음 경로를 추가:

```
Path에 추가:
C:\Program Files\Azure Kinect SDK v1.4.1\tools
C:\Program Files\Azure Kinect Body Tracking SDK\tools
```

### 3. Python 패키지 설치

```bash
cd virtual-production/kinect
pip install -r requirements.txt
```

**주요 패키지:**
- `opencv-python`: 비디오 처리
- `websockets`: WebSocket 클라이언트
- `PyYAML`: 설정 파일 파싱

**참고:** 이 시스템은 Azure Kinect SDK를 직접 호출하는 커스텀 ctypes 래퍼(`k4a_wrapper.py`)를 사용합니다. pykinect_azure 패키지는 더 이상 필요하지 않습니다.

## 설정

`config.yaml` 파일을 수정하여 시스템을 설정합니다.

### 주요 설정 항목

#### API 서버 연결

```yaml
api_server:
  host: "192.168.0.10"  # VP 서버 IP 주소
  ws_port: 8001         # WebSocket 포트
  http_port: 8000       # HTTP 포트 (fallback)
```

#### 센서 ID

```yaml
kinect:
  sensor_id: "kinect_001"  # 센서 고유 ID (여러 대 사용 시 구분)
  debounce_seconds: 0.0    # 자세 유지 시간 (0 = 즉시 감지)
```

#### 자세 감지 임계값

```yaml
posture_detection:
  arm_raise_threshold: 0.2      # 팔 들기 감지 민감도
  sitting_threshold: 0.5        # 앉음 감지 임계값
  lying_threshold: 0.3          # 누움 감지 임계값
  joint_confidence_threshold: 0.5  # 관절 신뢰도 최소값
```

**임계값 설명:**
- `arm_raise_threshold`: 손이 어깨보다 얼마나 높아야 팔을 들었다고 인식할지 (0.2 = 20%)
- `sitting_threshold`: 엉덩이와 무릎의 높이 차이 임계값
- `lying_threshold`: 누움으로 인식할 전체 높이 비율
- `joint_confidence_threshold`: 관절 추적 신뢰도 (낮으면 노이즈 증가, 높으면 감지 실패 증가)

#### Debounce 설정

```yaml
kinect:
  debounce_seconds: 2.0  # 자세가 2초 이상 유지되어야 전환
```

Debounce를 설정하면 잠깐의 움직임으로 인한 불필요한 전환을 방지할 수 있습니다.

## 시뮬레이션 모드 (Kinect 없이 테스트)

Kinect 하드웨어 없이도 시스템을 테스트할 수 있는 시뮬레이션 모드를 제공합니다.

### 시뮬레이션 모드 설정

`config.yaml`에서 시뮬레이션 모드를 활성화:

```yaml
simulation:
  enabled: true       # 시뮬레이션 모드 활성화
  auto_mode: true     # true: 자동 순환, false: 키보드 입력
  auto_interval: 5.0  # 자동 모드 자세 변경 간격 (초)
```

### 두 가지 시뮬레이션 모드

#### 1. 자동 모드 (Auto Mode)
```yaml
simulation:
  enabled: true
  auto_mode: true
  auto_interval: 5.0  # 5초마다 자세 변경
```

자세가 자동으로 순환합니다: standing → sitting → lying → left_arm_up → right_arm_up → (반복)

#### 2. 키보드 모드 (Keyboard Mode)
```yaml
simulation:
  enabled: true
  auto_mode: false
```

키보드로 수동 제어:
- `1`: standing (서있음)
- `2`: sitting (앉음)
- `3`: lying (누움)
- `4`: left_arm_up (왼팔 들기)
- `5`: right_arm_up (오른팔 들기)
- `q`: 종료

### 실제 Kinect 사용

Windows 환경에서 실제 Kinect를 사용하려면:

```yaml
simulation:
  enabled: false  # 실제 Kinect 사용
```

**주의**: Kinect 연결 실패 시 프로그램이 종료됩니다. 시뮬레이션 모드를 사용하려면 `enabled: true`로 설정하세요.

## 사용법

### 1. VP API 서버 시작

먼저 Virtual Production API 서버가 실행 중이어야 합니다.

```bash
cd virtual-production/api
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 2. Kinect 시스템 시작

```bash
cd virtual-production/kinect
python main.py
```

### 3. 시스템 확인

정상적으로 시작되면 다음과 같은 로그가 출력됩니다:

```
============================================================
Starting Kinect VP System
============================================================
1. Starting Azure Kinect...
✅ Azure Kinect started successfully
2. Connecting to VP server via WebSocket...
3. Waiting for WebSocket connection...
✅ WebSocket connected
============================================================
✅ System started successfully
============================================================

Detecting postures:
  - standing: 서있음
  - sitting: 앉음
  - lying: 누움
  - left_arm_up: 왼팔 들기
  - right_arm_up: 오른팔 들기

Press Ctrl+C to stop
============================================================
```

### 4. 자세 감지 확인

Kinect 앞에서 다양한 자세를 취하면 다음과 같은 로그가 출력됩니다:

```
🔄 Posture changed: unknown → standing
📤 Sending posture event: standing
✅ Event sent successfully: standing (total: 1)

🔄 Posture changed: standing → sitting
📤 Sending posture event: sitting
✅ Event sent successfully: sitting (total: 2)
```

## 문제 해결 (Windows)

### 🔧 빠른 진단

먼저 설치 상태를 확인하세요:

```bash
cd virtual-production\kinect
python check_installation.py
```

이 스크립트가 모든 필수 구성 요소를 자동으로 확인합니다.

### ❌ Kinect 연결 실패 ("Failed to start Kinect")

#### 1단계: 하드웨어 확인

**Azure Kinect Viewer로 테스트:**

```bash
test_kinect.bat
```

또는:

```bash
"C:\Program Files\Azure Kinect SDK v1.4.1\tools\k4aviewer.exe"
```

**Viewer에서 장치가 보이지 않으면:**
- ✅ USB 3.0 포트에 연결되어 있는지 확인
- ✅ 다른 USB 포트로 변경해보기
- ✅ Device Manager에서 "Azure Kinect" 확인
- ✅ Kinect 전원 LED가 켜져 있는지 확인

**Viewer에서는 보이는데 Python에서 실패하면** → 2단계로

#### 2단계: SDK 설치 확인

**필수 구성 요소:**

1. **Visual C++ Redistributable 2015-2019**
   - 다운로드: https://aka.ms/vs/16/release/vc_redist.x64.exe
   - 설치 후 재부팅

2. **Azure Kinect Sensor SDK** (v1.4.1 또는 v1.4.2)
   - 다운로드: https://learn.microsoft.com/en-us/azure/kinect-dk/sensor-sdk-download
   - 기본 경로에 설치: `C:\Program Files\Azure Kinect SDK v1.4.x\`

3. **Azure Kinect Body Tracking SDK**
   - 다운로드: https://learn.microsoft.com/en-us/azure/kinect-dk/body-sdk-download
   - 기본 경로에 설치: `C:\Program Files\Azure Kinect Body Tracking SDK\`

#### 3단계: 환경 변수 설정

**임시 설정 (현재 세션만):**

```bash
setup_environment.bat
python main.py
```

**영구 설정:**

1. 시스템 속성 → 환경 변수 → 시스템 변수 → Path 편집
2. 다음 경로들을 추가:

```
C:\Program Files\Azure Kinect SDK v1.4.1\sdk\windows-desktop\amd64\release\bin
C:\Program Files\Azure Kinect SDK v1.4.1\tools
C:\Program Files\Azure Kinect Body Tracking SDK\tools
```

3. 재부팅

#### 4단계: Python 패키지 설치

```bash
cd virtual-production/kinect
pip install -r requirements.txt
```

또는 수동 설치:

```bash
pip install numpy opencv-python websockets requests PyYAML python-json-logger
```

**참고:** pykinect-azure 패키지는 더 이상 필요하지 않습니다. 커스텀 ctypes 래퍼(`k4a_wrapper.py`)를 사용합니다.

### 🐍 DLL 로딩 오류

**오류 메시지:**
```
RuntimeError: Azure Kinect SDK not found
```

**해결 방법:**

1. Azure Kinect SDK가 올바르게 설치되어 있는지 확인
2. 다음 위치 중 하나에 SDK가 설치되어 있어야 함:
   - `C:\Program Files\Azure Kinect SDK v1.4.2\`
   - `C:\Program Files\Azure Kinect SDK v1.4.1\`
   - `C:\Program Files\Azure Kinect SDK v1.4.0\`

**필수 DLL 파일:**
- `k4a.dll`
- `depthengine_2_0.dll`
- `k4abt.dll` (Body Tracking)

위치: `C:\Program Files\Azure Kinect SDK v1.4.x\sdk\windows-desktop\amd64\release\bin\`

### ⚙️ config.yaml의 sensor_id

**sensor_id는 단순히 식별용 이름입니다 (하드웨어 설정 아님):**

```yaml
kinect:
  sensor_id: "kinect_001"  # 원하는 이름 사용 가능
```

여러 Kinect를 사용할 때 구분하기 위한 것으로, `"office_kinect"`, `"studio_kinect"` 등 어떤 이름이든 OK!

### WebSocket 연결 실패

1. VP API 서버가 실행 중인지 확인
2. `config.yaml`의 `api_server.host`가 올바른지 확인
3. 방화벽에서 포트 8001이 허용되어 있는지 확인

### 자세 감지가 부정확함

`config.yaml`에서 임계값을 조정하세요:

**팔 들기가 너무 민감한 경우:**
```yaml
posture_detection:
  arm_raise_threshold: 0.3  # 더 높게 설정 (기본값 0.2)
```

**앉음/누움 감지가 잘 안되는 경우:**
```yaml
posture_detection:
  sitting_threshold: 0.6    # 조절
  lying_threshold: 0.4      # 조절
```

**관절 추적이 불안정한 경우:**
```yaml
posture_detection:
  joint_confidence_threshold: 0.4  # 낮추기 (기본값 0.5)
```

### 자세가 너무 자주 바뀜

Debounce를 설정하여 자세가 일정 시간 유지되어야 전환되도록 설정:

```yaml
kinect:
  debounce_seconds: 2.0  # 2초 이상 유지되어야 전환
```

## 디버그 모드

디버그 정보를 출력하려면 `config.yaml`에서 설정:

```yaml
debug:
  print_joint_positions: true  # 관절 위치 출력
  show_skeleton: false         # 스켈레톤 시각화 (추후 구현)
  save_frames: false           # 프레임 저장 (추후 구현)

logging:
  level: "DEBUG"  # 상세 로그 출력
```

## 아키텍처

```
┌─────────────────┐
│  Azure Kinect   │
│      DK         │
└────────┬────────┘
         │ USB 3.0
         ▼
┌─────────────────┐
│   k4a.dll       │  ← Azure Kinect SDK (C)
│   k4abt.dll     │     Body Tracking SDK
└────────┬────────┘
         │ ctypes
         ▼
┌─────────────────┐
│  k4a_wrapper    │  ← 커스텀 ctypes 래퍼
└────────┬────────┘
         │ Python API
         ▼
┌─────────────────┐
│ kinect_handler  │  ← 디바이스 핸들러
└────────┬────────┘
         │ 관절 데이터
         ▼
┌─────────────────┐
│posture_detector │  ← 자세 분류 로직
└────────┬────────┘
         │ 자세 변경 이벤트
         ▼
┌─────────────────┐
│ websocket_client│  ← VP 서버 통신
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│   VP Server     │  ← API 서버
│   (main.py)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Frontend      │  ← 배경 영상 재생
└─────────────────┘
```

## 파일 구조

```
kinect/
├── main.py                  # 메인 진입점
├── config.yaml              # 설정 파일
├── k4a_wrapper.py           # Azure Kinect SDK ctypes 래퍼
├── kinect_handler.py        # Kinect 디바이스 핸들러
├── posture_detector.py      # 자세 감지 및 분류
├── websocket_client.py      # WebSocket 통신
├── simulator.py             # 시뮬레이션 모드
├── requirements.txt         # Python 의존성
├── README.md               # 이 파일
└── check_installation.py    # 설치 상태 확인 스크립트
```

## 참고 자료

- [Azure Kinect DK 문서](https://learn.microsoft.com/en-us/azure/kinect-dk/)
- [Azure Kinect Body Tracking](https://learn.microsoft.com/en-us/azure/kinect-dk/body-joints)
- [PyKinect Azure](https://github.com/ibaiGorordo/pyKinectAzure)

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
