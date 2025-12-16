# 버츄얼 프로덕션 시스템 (Virtual Production System)

AIoT 기반 객체 일관성을 유지한 버츄얼 프로덕션 영상 자동 생성 및 상호작용 시스템

## 🎯 개요

이 시스템은 시나리오 텍스트만으로 AI가 자동으로 버츄얼 프로덕션용 배경 영상을 생성하고, 배우가 착용한 웨어러블 센서의 행동 감지에 따라 실시간으로 배경을 전환하는 완전 자동화된 버츄얼 프로덕션 환경을 제공합니다.

### 주요 특징

- **자동 배경 생성**: 시나리오 분석 → 씬 분석 → 행동 기반 배경 영상 자동 생성
- **일관성 유지**: consistentvideo 패키지를 활용하여 객체(인물, 사물, 배경) 일관성 유지
- **실시간 상호작용**: 웨어러블 센서 행동 감지 → 배경 자동 전환 (크로스디졸브 효과)
- **LLM 기반 매핑**: 센서 행동과 배경 영상을 AI가 자동으로 매핑
- **웹 기반 컨트롤**: SvelteKit 프론트엔드로 실시간 모니터링 및 제어

## 📁 프로젝트 구조

```
virtual-production/
├── vp_package/              # 핵심 Python 패키지
│   ├── entity_filter.py     # 주인공 제거 및 배경 중심 프롬프트
│   ├── scene_analyzer.py    # 씬별 필요 행동 분석
│   ├── vp_cut_generator.py  # VP 배경용 컷 생성
│   └── action_mapper.py     # LLM 기반 센서-배경 매핑
│
├── api/                     # FastAPI 서버
│   ├── main.py             # REST API + WebSocket 엔드포인트
│   ├── models.py           # Pydantic 데이터 모델
│   └── requirements.txt
│
├── frontend/               # SvelteKit 웹 인터페이스
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte          # 메인 플레이어
│   │   │   └── preview/+page.svelte  # 배경 미리보기
│   │   └── lib/
│   │       ├── VideoPlayer.svelte    # 크로스디졸브 비디오 플레이어
│   │       ├── SensorDisplay.svelte  # 센서 이벤트 표시
│   │       └── websocket.ts          # WebSocket 클라이언트
│   └── package.json
│
├── wearable-rpi/           # 라즈베리파이 웨어러블 센서
│   ├── api/
│   │   ├── client.py          # HTTP API 클라이언트
│   │   └── websocket_client.py # WebSocket 클라이언트 (신규)
│   ├── behaviors/             # 행동 감지 모듈
│   ├── sensors/              # 센서 래퍼
│   └── config.yaml           # 설정 파일
│
└── kinect/                 # Azure Kinect 자세 감지 (Windows)
    ├── main.py                # 메인 진입점
    ├── config.yaml            # 설정 파일
    ├── k4a_wrapper.py         # ctypes 기반 SDK 래퍼 (핵심)
    ├── kinect_handler.py      # Kinect 디바이스 핸들러
    ├── posture_detector.py    # 자세 감지 및 분류
    ├── websocket_client.py    # WebSocket 통신
    ├── simulator.py           # 시뮬레이터 (Kinect 없이 테스트)
    ├── check_installation.py  # 설치 상태 진단
    ├── test_wrapper.py        # ctypes 래퍼 테스트
    ├── test_kinect.bat        # Kinect Viewer 실행
    ├── setup_environment.bat  # 환경 변수 설정
    └── requirements.txt       # Python 의존성
```

## 🚀 시작하기

### 1. 환경 설정

#### Python 환경
```bash
# 기본 패키지 (루트)
pip install -r requirements.txt

# VP API 서버
cd virtual-production/api
pip install -r requirements.txt
```

#### Node.js 환경 (프론트엔드)
```bash
cd virtual-production/frontend
npm install
```

#### 라즈베리파이 (웨어러블 센서)
```bash
cd virtual-production/wearable-rpi
pip install -r requirements.txt
# websocket-client 추가 설치
pip install websocket-client
```

#### Azure Kinect (Windows 전용)
```bash
cd virtual-production/kinect
pip install -r requirements.txt
```

**필수 구성 요소 (Windows):**
1. Visual C++ Redistributable 2015-2019
2. Azure Kinect Sensor SDK v1.4.0, v1.4.1, 또는 v1.4.2
3. Azure Kinect Body Tracking SDK

**자동 진단:**
```bash
python check_installation.py  # 설치 상태 자동 확인
```

**참고:** 이 시스템은 `pykinect-azure` 대신 커스텀 ctypes 래퍼(`k4a_wrapper.py`)를 사용합니다.

### 2. API 키 설정

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### 3. 서버 실행

#### VP API 서버 (포트 8001)
```bash
cd virtual-production/api
python -m uvicorn main:app --reload --port 8001
```

#### 프론트엔드 개발 서버 (포트 5173)
```bash
cd virtual-production/frontend
npm run dev
```

## 📖 사용 방법

### Phase 1: 배경 영상 생성

#### 🌐 웹 인터페이스 (권장)

배경 생성 페이지에서 간편하게 생성할 수 있습니다:

```bash
# 브라우저에서 접속
http://localhost:5173/generate
```

**단계별 진행**:
1. **프로젝트 설정** - Work Directory, Entity Set Name 입력
2. **스토리 입력** - 텍스트 입력 또는 파일 업로드
3. **AI 모델 설정** - 텍스트/이미지/비디오 모델, 화풍, 품질 선택
4. **생성 시작** - 자동으로 씬 분석 → 배경 생성 → 매핑 생성
5. **완료** - 자동으로 메인 플레이어로 이동

#### 💻 Python API (고급)

<details>
<summary>Python API 사용 방법 보기</summary>

**프로젝트 준비**
```python
WORK_DIR = "/path/to/work/directory"
ENTITY_SET_NAME = "my_project"

# consistentvideo를 사용하여 기본 엔티티, 씬 생성 완료 필요
# - reference/entity_list.txt (필수)
# - story/scene.txt (필수)
# - story/story_text.txt (선택)
#
# cut.txt는 1단계에서 자동 생성됩니다
```

**1단계: VP 컷 생성 (story/cut.txt)**
```python
import requests

response = requests.post("http://localhost:8001/vp/generate-vp-cuts", json={
    "work_dir": WORK_DIR,
    "entity_set_name": ENTITY_SET_NAME,
    "story_text": "...",  # 스토리 텍스트
    "model": "gpt-4.1"
})

result = response.json()
# result['cuts_generated']: 생성된 컷 개수
# result['scenes_processed']: 처리된 씬 개수
```

**2단계: VP 비디오 생성 (이미지 + 영상)**
```python
response = requests.post("http://localhost:8001/vp/generate-vp-videos", json={
    "work_dir": WORK_DIR,
    "entity_set_name": ENTITY_SET_NAME,
    "image_model": "gpt-image-1",
    "video_model": "veo-3.0-fast-generate-preview",
    "style": "realistic",
    "quality": "medium",
    "size": "1024x1024"
})

result = response.json()
# result['images_generated']: 생성된 이미지 개수
# result['videos_generated']: 생성된 비디오 개수
```

**3단계: 센서-배경 매핑 생성**
```python
response = requests.post("http://localhost:8001/vp/generate-mapping", json={
    "work_dir": WORK_DIR,
    "entity_set_name": ENTITY_SET_NAME,
    "model": "gpt-4.1"
})

result = response.json()
# result['mapping']: {
#   '1': {'1': {'action': 'stop', 'video_path': '...'}, ...},
#   'sensor_mapping': {'1': {'stop': 'S0001-C0001_video.mp4', ...}}
# }
```

</details>

### Phase 2: 실시간 버츄얼 프로덕션

#### 2-1. 웹 플레이어 열기
```bash
# 브라우저에서 접속
http://localhost:5173
```

#### 2-2. 센서 시작

**웨어러블 센서 (라즈베리파이):**
```bash
cd virtual-production/wearable-rpi

# config.yaml에서 WebSocket URL 확인/수정
# api:
#   websocket:
#     url: "ws://localhost:8001/vp/sensor-events"

# 센서 시작
python main.py
```

센서가 정상적으로 연결되면:
- 라즈베리파이 LED에 "READY" 표시
- 웹 플레이어 상태 바에 "센서: 활성" (초록색) 표시

**Azure Kinect (Windows):**

*시뮬레이션 모드 (Kinect 하드웨어 없이 테스트):*
```bash
cd virtual-production/kinect

# config.yaml에서 시뮬레이션 활성화
# simulation:
#   enabled: true
#   auto_mode: true  # 자동 순환 또는 false로 키보드 제어

python main.py
```

*실제 Kinect 사용:*
```bash
cd virtual-production/kinect

# 1. 환경 변수 설정 (필수)
setup_environment.bat

# 2. config.yaml에서 시뮬레이션 비활성화
# simulation:
#   enabled: false

# 3. 같은 CMD 창에서 Python 실행
python main.py
```

정상 연결 시 출력:
```
✅ Azure Kinect started successfully
✅ WebSocket connected
✅ System started successfully

Detecting postures:
  - standing: 서있음
  - sitting: 앉음
  - lying: 누움
  - left_arm_up: 왼팔 들기
  - right_arm_up: 오른팔 들기
```

#### 2-3. 행동 시뮬레이션 (테스트)
웹 플레이어에서 "컨트롤 보기" 버튼 클릭 → "행동 시뮬레이션" 버튼 사용

또는 API 직접 호출:
```python
response = requests.post("http://localhost:8001/vp/simulate-action", json={
    "action": "walk",
    "metadata": {}
})
```

### Phase 3: 미리보기

```bash
# 브라우저에서 접속
http://localhost:5173/preview?workDir=/path/to/work&entitySetName=my_project
```

## 🎬 작동 원리

### 1. 배경 생성 과정

```
시나리오 텍스트
    ↓
[1단계] VPCutGenerator - VP 컷 생성
    - VPSceneAnalyzer: 씬별 필요 행동 분석 (stop, walk, run, fall, ...)
    - EntityFilter: 주인공 제거 + 배경 중심 프롬프트 생성
    - 씬-액션 조합마다 cut 생성 → story/cut.txt 저장
    ↓
[2단계] 표준 파이프라인 - 이미지 + 비디오 생성
    - CutImageGenerator: cut.txt 기반 이미지 생성 → video/cut-images/
    - VideoGenerator: 이미지 기반 비디오 생성 → video/output/
    ↓
[3단계] ActionMapper - 센서-배경 자동 매핑
    - cut.txt 로드 (각 컷의 action 정보)
    - LLM 기반 센서 행동 → 배경 영상 매핑
    - action_mapping.json 생성
```

### 2. 실시간 배경 전환

```
웨어러블 센서 (Raspberry Pi)
    ↓
행동 감지 (stop, walk, run, fall, turn, shout, dark, bright)
    ↓
WebSocket (/vp/sensor-events) [센서 → 서버]
    ↓
VP API 서버 (FastAPI)
    - action_mapping.json 조회
    - 현재 씬 + 행동 → 배경 영상 매핑
    ↓
WebSocket 브로드캐스트 (/vp/player-events) [서버 → 프론트엔드]
    ↓
프론트엔드 (SvelteKit)
    - VideoPlayer 크로스디졸브 전환
    - SensorDisplay에 이벤트 표시
```

**WebSocket 엔드포인트**:
- `/vp/sensor-events` - 센서로부터 이벤트 수신 (센서 → 서버)
- `/vp/player-events` - 프론트엔드로 이벤트 전송 (서버 → 프론트엔드)

### 3. 센서가 감지하는 행동

#### 웨어러블 센서 (8개 행동)

| 행동 | 설명 | 센서 |
|------|------|------|
| stop | 정지 상태 | 가속도계 |
| walk | 걷기 | 가속도계 (1-3 Hz 패턴) |
| run | 달리기 | 가속도계 (빠른 패턴) |
| fall | 낙상 | 가속도계 + 자이로스코프 |
| turn | 뒤돌아보기 | 자이로스코프 |
| shout | 소리지름 | USB 마이크 |
| dark | 어두워짐 | NoIR 카메라 |
| bright | 밝아짐 | NoIR 카메라 |

#### Azure Kinect 자세 (5개 행동)

| 행동 | 설명 | 감지 방법 |
|------|------|----------|
| standing | 서있음 | 골반-무릎-발목 Y축 높이 비교 |
| sitting | 앉음 | 골반과 무릎 높이 차이 < 임계값 |
| lying | 누움 | 전체 신체 높이 < 임계값 |
| left_arm_up | 왼팔 들기 | 왼손이 왼쪽 어깨보다 높음 |
| right_arm_up | 오른팔 들기 | 오른손이 오른쪽 어깨보다 높음 |

**Kinect 자세 분류 알고리즘:**
- Body Tracking SDK로 32개 관절 추적
- Y축 높이 비교로 자세 분류
- 우선순위: 팔들기 > 누움 > 앉음 > 서있음
- 관절 신뢰도 임계값 설정 가능 (`config.yaml`)
- Debounce 기능으로 불필요한 전환 방지

## 🔧 API 엔드포인트

### VP 생성 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/vp/generate-vp-cuts` | VP 배경용 컷 생성 (story/cut.txt) |
| POST | `/vp/generate-vp-videos` | VP 비디오 생성 (이미지 + 영상) |
| POST | `/vp/generate-mapping` | 센서-배경 자동 매핑 (cut.txt 기반) |
| PUT | `/vp/update-mapping` | 매핑 수동 수정 |
| GET | `/vp/load-mapping` | 매핑 로드 |

### 실시간 제어 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/vp/current-background` | 현재 배경 정보 |
| POST | `/vp/change-scene` | 씬 수동 변경 |
| POST | `/vp/simulate-action` | 행동 시뮬레이션 |
| WS | `/vp/sensor-events` | 센서 이벤트 WebSocket |

### 기타 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/vp/preview` | 배경 미리보기 목록 |
| GET | `/vp/backgrounds/{filename}` | 배경 영상 스트리밍 |
| GET | `/sensor/available-actions` | 센서 행동 목록 |

## 📂 데이터 구조

### 프로젝트 디렉토리 구조

```
{WORK_DIR}/{ENTITY_SET_NAME}/
├── reference/
│   ├── analyzer/
│   ├── images/
│   └── entity_list.txt
├── story/
│   ├── scene.txt
│   ├── cut.txt              # VP 컷 포함 (action 필드 추가)
│   └── story_text.txt
├── video/                    # 표준 consistentvideo 경로
│   ├── cut-images/
│   │   ├── S0001-C0001.png
│   │   ├── S0001-C0002.png
│   │   └── ...
│   └── output/
│       ├── S0001-C0001_video.mp4
│       ├── S0001-C0002_video.mp4
│       └── ...
└── virtual-production/
    └── mappings/
        └── action_mapping.json
```

### action_mapping.json 예시

```json
{
  "1": {
    "1": {
      "action": "stop",
      "video_path": "/path/to/video/output/S0001-C0001_video.mp4"
    },
    "2": {
      "action": "walk",
      "video_path": "/path/to/video/output/S0001-C0002_video.mp4"
    }
  },
  "2": {
    "1": {
      "action": "stop",
      "video_path": "/path/to/video/output/S0002-C0001_video.mp4"
    },
    "2": {
      "action": "run",
      "video_path": "/path/to/video/output/S0002-C0002_video.mp4"
    }
  },
  "sensor_mapping": {
    "1": {
      "stop": "S0001-C0001_video.mp4",
      "walk": "S0001-C0002_video.mp4",
      "run": "S0001-C0002_video.mp4",
      "default": "S0001-C0001_video.mp4"
    },
    "2": {
      "stop": "S0002-C0001_video.mp4",
      "run": "S0002-C0002_video.mp4",
      "walk": "S0002-C0001_video.mp4",
      "default": "S0002-C0001_video.mp4"
    }
  }
}
```

## 🎨 프론트엔드 기능

### 배경 생성 (/generate)

- **3단계 자동 생성 워크플로우**:
  1. VP 컷 생성 - 스토리 분석하여 씬-액션 조합으로 컷 생성 (story/cut.txt)
  2. VP 비디오 생성 - 표준 파이프라인으로 이미지 + 비디오 생성
  3. 매핑 생성 - cut.txt 기반 센서 행동과 배경 자동 매핑
- **프로젝트 설정**: Work Directory, Entity Set Name
- **스토리 입력**: 직접 입력 또는 파일 업로드
- **AI 모델 선택**: 텍스트/이미지/비디오 모델, 화풍, 품질
- **진행 상태 표시**: 단계별 진행률 및 로그 출력
- **자동 완료**: 생성 완료 후 자동으로 메인 플레이어로 이동

### 메인 플레이어 (/)

- **전체화면 비디오 플레이어**: 크로스디졸브 효과로 배경 전환
- **상태 바**:
  - 현재 씬, 행동 표시
  - **서버: 연결됨/연결 끊김** - VP API 서버와의 WebSocket 연결 상태
  - **센서: 활성/비활성** - 실제 센서 데이터 수신 여부 (5초 이내)
- **센서 디스플레이**: 최근 센서 이벤트 표시 (토글 가능)
- **컨트롤 패널** (선택):
  - 씬 수동 선택
  - 행동 시뮬레이션 버튼

### 초기 설정 (/setup)

- **매핑 로드**: 기존 프로젝트의 매핑 파일 로드
- **배경 생성 바로가기**: /generate 페이지로 이동
- **프로젝트 정보 입력**: Work Directory, Entity Set Name

### 미리보기 (/preview)

- 씬별 그룹화된 배경 영상 그리드
- 클릭하여 비디오 재생
- 전체 배경 목록 확인

## 🛠 개발 가이드

### VP 패키지 확장

새로운 기능을 추가하려면 `vp_package/` 에 모듈을 추가하고 `__init__.py`에 등록:

```python
from .my_new_module import MyNewClass

__all__ = [
    'EntityFilter',
    'VPSceneAnalyzer',
    'VPCutGenerator',
    'ActionMapper',
    'MyNewClass',  # 신규 모듈
]
```

### API 엔드포인트 추가

`api/main.py`에 라우터 추가:

```python
@app.post("/vp/my-new-endpoint")
async def my_new_endpoint(request: MyRequest):
    # 구현
    return {"result": "success"}
```

### 프론트엔드 페이지 추가

`frontend/src/routes/my-page/+page.svelte` 생성:

```svelte
<script lang="ts">
  // 페이지 로직
</script>

<div>
  <!-- 페이지 내용 -->
</div>
```

## 🐛 트러블슈팅

### WebSocket 연결 실패
```bash
# API 서버 실행 확인
curl http://localhost:8001/health

# CORS 설정 확인 (api/main.py)
# 프록시 설정 확인 (frontend/vite.config.js)
```

### 배경 영상이 로드되지 않음
```bash
# 파일 경로 확인
ls {WORK_DIR}/{ENTITY_SET_NAME}/video/output/

# cut.txt 확인 (action 필드 포함)
cat {WORK_DIR}/{ENTITY_SET_NAME}/story/cut.txt

# API 로그 확인
# 매핑 파일 확인
cat {WORK_DIR}/{ENTITY_SET_NAME}/virtual-production/mappings/action_mapping.json
```

### 센서 연결 실패
```bash
# config.yaml의 WebSocket URL 확인
# 라즈베리파이와 API 서버 간 네트워크 확인
ping <API_SERVER_IP>
```

### Kinect 관련 문제 (Windows)

#### 🔧 빠른 진단
```bash
cd virtual-production\kinect
python check_installation.py  # 자동 진단 스크립트
```

#### ❌ "Failed to start Kinect" 오류

**1단계: 하드웨어 확인**
```bash
test_kinect.bat  # Azure Kinect Viewer 실행
```

- USB 3.0 포트에 연결 확인
- Device Manager에서 "Azure Kinect" 장치 확인
- Kinect 전원 LED 켜짐 확인

**2단계: SDK 설치 확인**
- Visual C++ Redistributable 2015-2019 설치
- Azure Kinect Sensor SDK v1.4.x 설치
- Azure Kinect Body Tracking SDK 설치

**3단계: 환경 변수 설정**

임시 설정 (현재 세션):
```bash
setup_environment.bat
python main.py  # 같은 CMD 창에서 실행
```

영구 설정:
```
시스템 환경 변수 Path에 추가:
C:\Program Files\Azure Kinect SDK v1.4.x\sdk\windows-desktop\amd64\release\bin
C:\Program Files\Azure Kinect SDK v1.4.x\tools
C:\Program Files\Azure Kinect Body Tracking SDK\sdk\windows-desktop\amd64\release\bin
C:\Program Files\Azure Kinect Body Tracking SDK\tools
```

**4단계: Python 패키지**
```bash
pip install -r requirements.txt
```

#### 🐍 DLL 로딩 오류

**오류:** `RuntimeError: Azure Kinect SDK not found`

**해결:**
- `k4a_wrapper.py`가 SDK 버전을 자동 감지 (v1.4.0, v1.4.1, v1.4.2)
- SDK가 기본 경로에 설치되어 있는지 확인
- `test_wrapper.py`로 DLL 로딩 테스트

#### 🌐 네트워크 연결 문제 (Windows → Mac/Linux)

Kinect(Windows)와 VP API 서버(Mac/Linux)가 다른 컴퓨터에 있는 경우:

**1. config.yaml 설정:**
```yaml
api_server:
  host: "192.168.x.x"  # Mac/Linux의 로컬 IP 주소
  ws_port: 8001
```

**2. VP API 서버 시작:**
```bash
# Mac/Linux에서
cd virtual-production/api
uvicorn main:app --host 0.0.0.0 --port 8001  # 0.0.0.0으로 바인딩
```

**3. 방화벽 설정:**
- Mac: 시스템 설정 → 네트워크 → 방화벽에서 8001 포트 허용
- Linux: `sudo ufw allow 8001/tcp`

**4. 연결 테스트:**
```bash
# Windows에서
ping 192.168.x.x
telnet 192.168.x.x 8001
```

#### ⚙️ 자세 감지 조정

**감지가 너무 민감한 경우:**
```yaml
# config.yaml
posture_detection:
  arm_raise_threshold: 0.3  # 높게 (기본값 0.2)
  joint_confidence_threshold: 0.6  # 높게 (기본값 0.5)
```

**자세가 너무 자주 바뀌는 경우:**
```yaml
# config.yaml
kinect:
  debounce_seconds: 2.0  # 2초 이상 유지되어야 전환
```

## 🎥 Kinect 시스템 상세

### ctypes 기반 커스텀 SDK 래퍼

이 시스템은 `pykinect-azure` 패키지를 사용하지 않고, Azure Kinect SDK DLL을 직접 호출하는 완전한 ctypes 구현(`k4a_wrapper.py`)을 사용합니다.

**주요 특징:**
- `pykinect-azure`의 DLL 로딩 문제를 우회
- SDK 버전 자동 감지 (v1.4.0, v1.4.1, v1.4.2)
- Windows PATH 자동 설정
- 32개 관절 추적 지원

**핵심 클래스:**
- `K4ADevice`: 카메라 제어 (open, close, start_cameras, get_capture)
- `K4ABTTracker`: Body Tracking (enqueue_capture, pop_result)
- `K4ABTFrame`: 스켈레톤 데이터 추출
- `JointType`: 32개 관절 Enum

### 시뮬레이션 모드

Kinect 하드웨어 없이 테스트 가능한 두 가지 모드:

#### 1. 자동 모드 (Auto Mode)
```yaml
# config.yaml
simulation:
  enabled: true
  auto_mode: true
  auto_interval: 5.0  # 5초마다 자세 변경
```

자세가 자동으로 순환: standing → sitting → lying → left_arm_up → right_arm_up → (반복)

#### 2. 키보드 모드 (Keyboard Mode)
```yaml
# config.yaml
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

### 진단 도구

**설치 상태 자동 진단:**
```bash
python check_installation.py
```
- SDK 설치 확인
- DLL 파일 확인
- Python 패키지 확인
- 환경 변수 확인

**Kinect Viewer 테스트:**
```bash
test_kinect.bat
```
Azure Kinect Viewer를 실행하여 하드웨어 연결 확인

**ctypes 래퍼 테스트:**
```bash
python test_wrapper.py
```
k4a_wrapper.py의 DLL 로딩 테스트

**환경 변수 임시 설정:**
```bash
setup_environment.bat
```
현재 CMD 세션에만 환경 변수 설정

### 아키텍처

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
         │ 관절 데이터 (32개 관절)
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
│   VP Server     │  ← API 서버 (Port 8001)
│   (main.py)     │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│   Frontend      │  ← 배경 영상 재생 (Port 5173)
│   (SvelteKit)   │
└─────────────────┘
```

### Kinect 설정 파일 (`kinect/config.yaml`)

```yaml
# 시뮬레이션 모드 (Kinect 없이 테스트)
simulation:
  enabled: false           # true: 시뮬레이션, false: 실제 Kinect
  auto_mode: true          # true: 자동 순환, false: 키보드
  auto_interval: 5.0       # 자동 모드 전환 간격 (초)

# API 서버 연결
api_server:
  host: "localhost"        # VP API 서버 호스트 (Mac/Linux IP 주소)
  ws_port: 8001
  http_port: 8000

# Kinect 센서 설정
kinect:
  sensor_id: "kinect_001"  # 센서 식별 ID
  debounce_seconds: 0.0    # 자세 유지 시간 (0 = 즉시 감지)

# 자세 감지 임계값
posture_detection:
  arm_raise_threshold: 0.2           # 팔 들기 감지 민감도
  sitting_threshold: 0.5             # 앉음 감지 임계값
  lying_threshold: 0.3               # 누움 감지 임계값
  joint_confidence_threshold: 0.5    # 관절 신뢰도 최소값

# WebSocket 설정
websocket:
  reconnect_delay: 5.0
  max_reconnect_attempts: 10
  ping_interval: 30.0

# 로깅
logging:
  level: "INFO"
  file: "kinect.log"
  console: true
```

## 📝 To-Do

- [ ] 매핑 편집 UI 페이지 구현
- [ ] 웨어러블 센서 main.py를 WebSocket 클라이언트로 통합
- [ ] 전환 규칙 (transition rules) 적용
- [ ] 다중 카메라 앵글 지원
- [ ] 성능 최적화 (비디오 프리로딩)
- [x] Kinect 자세 감지 시스템 통합
- [x] 프론트엔드에 Kinect 행동 지원 추가

## 📄 라이선스

이 프로젝트는 기존 consistent-ai-video-generator의 라이선스를 따릅니다.

## 🙏 Acknowledgments

- consistentvideo 패키지를 확장하여 구현
- OpenAI API (GPT, Image Generation, Video Generation)
- FastAPI, SvelteKit, Raspberry Pi Sense HAT

---

**Version**: 2.1.0 (Kinect 통합)
**Last Updated**: 2025-01-23

### 변경 이력

#### v2.1.0 (2025-01-23) - Kinect 통합
- **Azure Kinect DK 지원**: ctypes 기반 커스텀 SDK 래퍼 구현
- **5가지 자세 감지**: standing, sitting, lying, left_arm_up, right_arm_up
- **시뮬레이션 모드**: Kinect 하드웨어 없이 테스트 가능
- **프론트엔드 확장**: 13개 센서 액션 지원 (웨어러블 8개 + Kinect 5개)
- **진단 도구 추가**: 설치 상태 자동 진단, DLL 테스트 스크립트
- **네트워크 설정 가이드**: Windows ↔ Mac/Linux 연동

#### v2.0.0 (2025-01-09) - 표준 파이프라인 통합
- **표준 파이프라인 통합**: consistentvideo의 CutImageGenerator + VideoGenerator 직접 사용
- **VPCutGenerator 도입**: 씬-액션 조합을 cut.txt 형식으로 생성
- **Cut ID 기반 매핑**: 씬별 컷 ID로 명확한 매핑 구조
- **디렉토리 구조 표준화**: video/output/ 경로 사용
- **BackgroundGenerator 제거**: 표준 파이프라인으로 대체
