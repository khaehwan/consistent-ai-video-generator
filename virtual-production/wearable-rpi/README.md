# Raspberry Pi Wearable Sensor System for Virtual Production

AIoT 기반 버츄얼 프로덕션 영상 자동생성을 위한 라즈베리파이 웨어러블 센서 시스템

## 개요

이 프로젝트는 라즈베리파이 4를 기반으로 배우의 행동을 실시간으로 감지하고 버츄얼 프로덕션 시스템과 연동하는 웨어러블 센서 시스템입니다.

### 주요 기능

- **행동 인식**
  - 정지 상태 감지
  - 움직임 감지 (걷기/달리기)
  - 낙상 감지
  - 뒤돌아보기 감지 (방향 독립적 - 센서 방향 무관)
  - 소리지르기 감지 (USB 마이크)
  - 밝기 변화 감지 (어두어짐/밝아짐)
  - 나침반 방향 감지 (연속 각도 0-360°, LED 테두리에 북쪽 방향 표시)

- **자동 센서 캘리브레이션**
  - 시작 시 중력 방향 자동 감지
  - 센서를 수평/수직 어느 방향으로 놓아도 정확한 회전 감지
  - 방향 독립적 알고리즘으로 안정적인 동작
  - 🔘 조이스틱 가운데 버튼으로 언제든 재캘리브레이션 가능
  - 센서 방향 변경 시 즉시 적용

- **실시간 피드백**
  - Sense HAT LED 매트릭스에 인식된 행동 표시
  - 각 행동별 고유 아이콘 및 색상 표시

- **API 연동**
  - 버츄얼 프로덕션 서버로 실시간 행동 데이터 전송
  - 오프라인 모드 지원 (네트워크 연결이 없을 때 데이터 저장)

## 하드웨어 요구사항

- Raspberry Pi 4 Model B (4GB 이상 권장)
- Sense HAT v2
- Raspberry Pi NoIR Camera v2
- USB 마이크
- MicroSD 카드 (32GB 이상)
- 전원 공급 장치 (5V 3A)

## 소프트웨어 요구사항

- Raspberry Pi OS (Bullseye 이상)
- Python 3.8 이상

## 설치 방법

### 1. 시스템 업데이트

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. 필수 시스템 패키지 설치

```bash
# 카메라 지원
sudo apt install -y python3-picamera2 libcamera-apps

# 오디오 지원
sudo apt install -y portaudio19-dev python3-pyaudio

# OpenCV 의존성
sudo apt install -y python3-opencv libatlas-base-dev

# Sense HAT 지원
sudo apt install -y sense-hat
```

### 3. 프로젝트 클론 또는 복사

```bash
cd ~
git clone [프로젝트 URL] cavg-rpi
cd cavg-rpi
```

### 4. Python 가상환경 설정 (권장)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 6. 하드웨어 활성화

```bash
# 카메라 활성화
sudo raspi-config
# Interface Options -> Camera -> Enable

# I2C 활성화 (Sense HAT용)
# Interface Options -> I2C -> Enable

# 재부팅
sudo reboot
```

## 설정

`config.yaml` 파일을 수정하여 시스템을 구성할 수 있습니다:

### API 서버 설정

```yaml
api:
  base_url: "http://your-server-address:port"  # 버츄얼 프로덕션 서버 주소
  endpoints:
    behavior: "/api/behavior"  # 행동 전송 엔드포인트
```

### 행동 감지 임계값 조정

```yaml
behaviors:
  movement:
    threshold_walking: 0.5  # 걷기 감지 임계값
    threshold_running: 1.5  # 달리기 감지 임계값

  fall:
    acceleration_threshold: 2.0  # 낙상 감지 가속도 임계값
    angle_threshold: 45  # 낙상 감지 각도 변화 임계값

  shout:
    volume_threshold: 70  # 소리지르기 음량 임계값 (dB)

  brightness:
    dark_threshold: 50  # 어두움 판단 임계값
    bright_threshold: 200  # 밝음 판단 임계값
```

## 실행 방법

### 기본 실행

```bash
python3 main.py
```

### 옵션과 함께 실행

```bash
# 디버그 모드
python3 main.py --debug

# 센서 보정 후 실행
python3 main.py --calibrate

# 오프라인 모드 (API 연결 없이)
python3 main.py --offline

# 테스트 모드
python3 main.py --test

# 사용자 정의 설정 파일 사용
python3 main.py -c my_config.yaml
```

### 서비스로 실행 (자동 시작)

1. 서비스 파일 생성:

```bash
sudo nano /etc/systemd/system/wearable-sensor.service
```

2. 다음 내용 입력:

```ini
[Unit]
Description=Raspberry Pi Wearable Sensor System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/cavg-rpi
ExecStart=/home/pi/cavg-rpi/venv/bin/python /home/pi/cavg-rpi/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. 서비스 활성화:

```bash
sudo systemctl enable wearable-sensor.service
sudo systemctl start wearable-sensor.service
```

4. 서비스 상태 확인:

```bash
sudo systemctl status wearable-sensor.service
```

## API 인터페이스

### 행동 이벤트 전송 형식

```json
{
    "timestamp": "2024-11-09T10:30:45.123Z",
    "sensor_id": "rpi_wearable_001",
    "behavior": "fall",
    "metadata": {
        "acceleration": 2.5,
        "orientation_change": 45.2
    }
}
```

### 지원되는 행동 타입

- `stop` - 정지
- `walk` - 걷기
- `run` - 달리기
- `fall` - 넘어짐
- `turn` - 뒤돌아보기
- `shout` - 소리지르기
- `dark` - 어두어짐
- `bright` - 밝아짐

## LED 매트릭스 표시

8x8 LED 매트릭스를 4개 영역으로 분할하여 모든 센서 상태를 한눈에 표시합니다.

### 레이아웃

```text
  0 1 2 3 4 5 6 7
0 C C C C C C C C  ← 나침반 테두리 (북쪽 방향 표시)
1 C M M M T T T C
2 C M M M T T T C  M: 움직임 (3×3)
3 C M M M T T T C  T: 낙상/회전 (3×3)
4 C S S S B B B C  S: 소리 (3×3)
5 C S S S B B B C  B: 밝기 그래프 (3×3)
6 C S S S B B B C
7 C C C C C C C C  ← 나침반 테두리

테두리(C): 나침반 - 파란색 점이 북쪽 방향 추적
```

### 영역별 설명

#### 1️⃣ 움직임 (좌상단 3×3) - Movement

아이콘 형태로 현재 움직임 상태 표시:

- 🟢 **녹색 원형**: 정지 (STOP)
- 🟡 **노란색 화살표**: 걷기 (WALK)
- 🟠 **주황색 이중 화살표**: 달리기 (RUN)

#### 2️⃣ 낙상/회전 (우상단 3×3) - Fall/Turn

두 가지 상태를 하나의 영역에 표시:

- **상단 2행**: 낙상 상태
  - 🔴 빨간색 X: 낙상 감지
  - 🟢 어두운 녹색: 정상
- **하단 1행**: 회전 상태 (방향 표시)
  - 🟠 주황색 화살표 (←): 왼쪽으로 회전
  - 🔵 청록색 화살표 (→): 오른쪽으로 회전
  - ⚫ 어두운 파란색: 정상

#### 3️⃣ 소리 (좌하단 3×3) - Shout

물결 패턴으로 소리 감지 표시:

- 🟣 **자홍색 물결**: 소리 감지
- ⚫ **어두운 보라색**: 조용함

#### 4️⃣ 밝기 (우하단 3×3) - Brightness

3개의 세로 막대 그래프로 밝기 레벨 표시:

- **어두움**: 🔵 파란색 막대 1개
- **보통**: 🔵 파란색 + 🟢 녹색 막대 2개
- **밝음**: 🔵 파란색 + 🟢 녹색 + 🟡 노란색 막대 3개

#### 🧭 나침반 (테두리) - Compass

LED 매트릭스 테두리(28개 픽셀)에 북쪽 방향을 파란색 점으로 표시:

- 🔵 **파란색 점**: 현재 북쪽 방향
- 연속적으로 회전하여 실시간 방위각(0-360°) 추적

### 시작 화면

시스템 시작 시 자동으로 표시:

1. **시작 애니메이션**: 각 영역을 순차적으로 점등하여 LED 테스트
2. **READY 메시지**: 청록색 텍스트로 "READY" 스크롤 표시

### 조이스틱 재캘리브레이션 피드백

조이스틱 가운데 버튼(🔘) 누를 때:

1. **노란색 플래시** (2회): 캘리브레이션 중
2. **초록색 체크마크** (✓): 완료
3. **페이드아웃**: 부드럽게 사라짐
4. **원래 화면 복귀**: 정상 모니터링 재개

### 특징

- **실시간 업데이트**: 20Hz (0.05초 간격)로 부드러운 상태 변화 표시
- **동시 표시**: 모든 센서 상태를 4개 영역에 동시 표시
- **이벤트 플래시**: 낙상/회전/소리 이벤트는 감지 시 일정 시간 표시
- **직관적 아이콘**: 각 상태별 고유 아이콘과 색상으로 한눈에 파악
- **그래프 표시**: 밝기는 3단계 막대 그래프로 시각화
- **나침반 통합**: 테두리를 활용한 연속 방위각 표시

## 문제 해결

### 카메라가 작동하지 않을 때

```bash
# 카메라 연결 확인
vcgencmd get_camera

# 카메라 테스트
libcamera-hello
```

### 마이크가 인식되지 않을 때

```bash
# USB 장치 확인
lsusb

# 오디오 장치 목록
arecord -l
```

### Sense HAT가 인식되지 않을 때

```bash
# I2C 장치 확인
i2cdetect -y 1
```

## 로그 파일

로그는 다음 위치에 저장됩니다:

- 시스템 로그: `logs/wearable_sensor.log`
- 이벤트 로그: `logs/events.log`
- 오프라인 이벤트: `data/offline_events.json`

## 성능 최적화

### CPU 사용률 낮추기

```yaml
system:
  main_loop_delay: 0.2  # 메인 루프 지연 증가
  sensor_polling_rate: 20  # 센서 폴링 속도 감소
```

### 메모리 사용 최적화

```yaml
behaviors:
  movement:
    sample_window: 5  # 샘플 윈도우 크기 감소
```

## 개발 및 확장

### 새로운 행동 추가하기

1. `behaviors/` 디렉토리에 새 감지기 모듈 생성
2. `behaviors/detector.py`에 감지기 통합
3. `config.yaml`에 설정 추가
4. API 페이로드 형식 정의

### API 엔드포인트 커스터마이징

`api/client.py`의 `send_behavior_event` 메서드를 수정하여 원하는 형식으로 데이터를 전송할 수 있습니다.

## 라이선스

이 프로젝트는 연구 및 교육 목적으로 개발되었습니다.

## 문의 및 지원

프로젝트 관련 문의사항이나 버그 리포트는 이슈 트래커를 통해 제출해주세요.
