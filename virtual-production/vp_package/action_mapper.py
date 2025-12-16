"""
Action Mapper - 센서 행동과 배경 영상 매핑

LLM을 사용하여 웨어러블 센서의 행동을 배경 영상에 자동으로 매핑합니다.
"""

import json
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI


class ActionMapper:
    """센서 행동 → 배경 영상 자동 매핑"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI API 키 (없으면 환경변수 사용)
        """
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()

    def create_mapping(
        self,
        background_plan: Dict[str, Any],
        generated_videos: Dict[str, str],
        sensor_actions: List[str],
        model: str = "gpt-4o"
    ) -> Dict[str, Any]:
        """
        센서 행동과 배경 영상 자동 매핑 생성 (DEPRECATED: use create_mapping_from_cuts)

        Args:
            background_plan: 배경 생성 계획
            generated_videos: 생성된 비디오 딕셔너리 {action_key: video_path}
            sensor_actions: 센서가 감지할 수 있는 행동 목록
            model: 사용할 GPT 모델

        Returns:
            매핑 정보
            {
                'scene_1': {
                    'stop': 'S0001-action_stop.mp4',
                    'walk': 'S0001-action_walk.mp4',
                    'default': 'S0001-action_stop.mp4'
                },
                ...
            }
        """
        mapping = {}

        for scene_plan in background_plan['scenes']:
            scene_id = scene_plan['scene_id']
            scene_title = scene_plan['title']
            scene_desc = scene_plan['description']
            available_actions = scene_plan['actions']
            backgrounds = scene_plan['backgrounds_to_generate']

            print(f"\n씬 {scene_id} 매핑 생성 중...")

            # 이 씬에서 사용 가능한 배경 영상
            scene_backgrounds = {
                bg['action']: bg['video_filename']
                for bg in backgrounds
            }

            # LLM을 사용한 매핑 생성
            scene_mapping = self._generate_scene_mapping(
                scene_id=scene_id,
                scene_title=scene_title,
                scene_desc=scene_desc,
                sensor_actions=sensor_actions,
                available_backgrounds=scene_backgrounds,
                model=model
            )

            # 기본값 설정 (stop 우선, 없으면 첫 번째)
            if 'default' not in scene_mapping:
                if 'stop' in scene_mapping:
                    scene_mapping['default'] = scene_mapping['stop']
                elif scene_backgrounds:
                    scene_mapping['default'] = list(scene_backgrounds.values())[0]

            mapping[f'scene_{scene_id}'] = scene_mapping
            print(f"  매핑 완료: {scene_mapping}")

        return mapping

    def create_mapping_from_cuts(
        self,
        cuts_by_scene: List[List[Dict]],
        scenes: List[Dict],
        sensor_actions: List[str],
        video_output_path: str,
        model: str = "gpt-4.1"
    ) -> Dict[str, Any]:
        """
        cut.txt 기반 센서 행동 → 배경 영상 자동 매핑 생성

        Args:
            cuts_by_scene: 씬별 컷 리스트 (cut.txt에서 로드)
            scenes: 씬 리스트 (scene.txt에서 로드)
            sensor_actions: 센서가 감지할 수 있는 행동 목록
            video_output_path: 비디오 출력 디렉토리 경로
            model: 사용할 GPT 모델

        Returns:
            매핑 정보
            {
                '1': {
                    '1': {'action': 'stop', 'video_path': '.../S0001-C0001_video.mp4'},
                    '2': {'action': 'walk', 'video_path': '.../S0001-C0002_video.mp4'},
                    ...
                },
                'sensor_mapping': {
                    '1': {
                        'stop': 'S0001-C0001_video.mp4',
                        'walk': 'S0001-C0002_video.mp4',
                        'default': 'S0001-C0001_video.mp4'
                    },
                    ...
                }
            }
        """
        mapping = {}
        sensor_mapping = {}

        for scene_num, scene_cuts in enumerate(cuts_by_scene, 1):
            print(f"\n씬 {scene_num} 매핑 생성 중...")

            # 씬 정보
            scene_title = scenes[scene_num - 1].get('title', f'Scene {scene_num}') if scene_num <= len(scenes) else f'Scene {scene_num}'
            scene_desc = scenes[scene_num - 1].get('description', '') if scene_num <= len(scenes) else ''

            # 씬의 컷 정보 저장 (cut_id → action)
            scene_cut_mapping = {}
            available_backgrounds = {}  # {action: video_filename}

            for cut in scene_cuts:
                cut_id = cut.get('cut_id', 1)
                action = cut.get('action', 'unknown')
                video_filename = f'S{scene_num:04d}-C{cut_id:04d}_video.mp4'
                video_path = os.path.join(video_output_path, video_filename)

                scene_cut_mapping[str(cut_id)] = {
                    'action': action,
                    'video_path': video_path
                }

                # action → video_filename 매핑
                if action not in available_backgrounds:
                    available_backgrounds[action] = video_filename

            mapping[str(scene_num)] = scene_cut_mapping

            # LLM을 사용한 센서 매핑 생성
            scene_sensor_mapping = self._generate_scene_mapping(
                scene_id=scene_num,
                scene_title=scene_title,
                scene_desc=scene_desc,
                sensor_actions=sensor_actions,
                available_backgrounds=available_backgrounds,
                model=model
            )

            # 기본값 설정 (stop 우선, 없으면 첫 번째)
            if 'default' not in scene_sensor_mapping:
                if 'stop' in scene_sensor_mapping:
                    scene_sensor_mapping['default'] = scene_sensor_mapping['stop']
                elif available_backgrounds:
                    scene_sensor_mapping['default'] = list(available_backgrounds.values())[0]

            sensor_mapping[str(scene_num)] = scene_sensor_mapping
            print(f"  컷 매핑: {scene_cut_mapping}")
            print(f"  센서 매핑: {scene_sensor_mapping}")

        # 전체 매핑 구조
        full_mapping = {
            **mapping,  # 씬별 cut_id → action, video_path
            'sensor_mapping': sensor_mapping  # 씬별 sensor_action → video_filename
        }

        return full_mapping

    def _generate_scene_mapping(
        self,
        scene_id: int,
        scene_title: str,
        scene_desc: str,
        sensor_actions: List[str],
        available_backgrounds: Dict[str, str],
        model: str
    ) -> Dict[str, str]:
        """
        특정 씬의 센서 행동 → 배경 영상 매핑 생성

        Args:
            scene_id: 씬 ID
            scene_title: 씬 제목
            scene_desc: 씬 설명
            sensor_actions: 센서 행동 목록
            available_backgrounds: 사용 가능한 배경 {action: video_filename}
            model: GPT 모델

        Returns:
            매핑 딕셔너리 {sensor_action: video_filename}
        """
        backgrounds_info = json.dumps(available_backgrounds, ensure_ascii=False, indent=2)
        sensor_actions_info = json.dumps(sensor_actions, ensure_ascii=False, indent=2)

        prompt = f"""다음 씬에서 센서 행동과 배경 영상을 매핑해주세요.

씬 {scene_id}: {scene_title}
설명: {scene_desc}

웨어러블 센서가 감지할 수 있는 행동:
{sensor_actions_info}

각 행동의 의미:
- stop: 정지 상태
- walk: 걷기
- run: 달리기
- fall: 넘어짐
- turn: 뒤돌아보기
- shout: 소리지름
- dark: 어두운 환경
- bright: 밝은 환경

이 씬에서 사용 가능한 배경 영상:
{backgrounds_info}

요구사항:
1. 각 센서 행동을 가장 적절한 배경 영상에 매핑
2. 사용 가능한 배경이 없는 센서 행동은 가장 유사한 배경으로 매핑
3. 예: 'run' 배경이 없으면 'walk' 배경 사용
4. 'stop'은 기본 배경으로 사용

JSON 형식으로 응답:
{{
  "stop": "S####-action_stop.mp4",
  "walk": "S####-action_walk.mp4",
  ...
}}

모든 센서 행동을 매핑하되, 사용 가능한 배경 파일명만 사용하세요.
"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert in virtual production scene mapping."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            mapping = json.loads(response.choices[0].message.content)

            # 유효성 검사: 매핑된 파일이 실제 존재하는지 확인
            validated_mapping = {}
            available_files = set(available_backgrounds.values())

            for action, video_file in mapping.items():
                if video_file in available_files:
                    validated_mapping[action] = video_file
                else:
                    # 유효하지 않은 파일이면 기본값 사용
                    if available_backgrounds:
                        validated_mapping[action] = list(available_backgrounds.values())[0]

            return validated_mapping

        except Exception as e:
            print(f"씬 {scene_id} 매핑 생성 중 오류: {e}")
            # 오류 시 1:1 매핑 시도
            simple_mapping = {}
            for action in sensor_actions:
                if action in available_backgrounds:
                    simple_mapping[action] = available_backgrounds[action]
                elif available_backgrounds:
                    # 가장 첫 배경 사용
                    simple_mapping[action] = list(available_backgrounds.values())[0]

            return simple_mapping

    def save_mapping(
        self,
        mapping: Dict[str, Any],
        output_path: str
    ):
        """
        매핑 정보를 JSON 파일로 저장

        Args:
            mapping: 매핑 정보
            output_path: 출력 파일 경로
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        print(f"\n매핑 정보 저장 완료: {output_path}")

    def load_mapping(
        self,
        mapping_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        매핑 정보 불러오기

        Args:
            mapping_path: 매핑 파일 경로

        Returns:
            매핑 정보 또는 None
        """
        if not os.path.exists(mapping_path):
            return None

        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            return mapping
        except Exception as e:
            print(f"매핑 로드 중 오류: {e}")
            return None

    def update_mapping(
        self,
        mapping: Dict[str, Any],
        scene_id: int,
        action: str,
        video_filename: str
    ) -> Dict[str, Any]:
        """
        매핑 수동 업데이트

        Args:
            mapping: 기존 매핑
            scene_id: 씬 ID
            action: 센서 행동
            video_filename: 변경할 비디오 파일명

        Returns:
            업데이트된 매핑
        """
        scene_key = f'scene_{scene_id}'

        if scene_key not in mapping:
            mapping[scene_key] = {}

        mapping[scene_key][action] = video_filename

        return mapping

    def get_background_for_action(
        self,
        mapping: Dict[str, Any],
        scene_id: int,
        action: str
    ) -> Optional[str]:
        """
        특정 씬과 행동에 대한 배경 영상 파일명 반환

        Args:
            mapping: 매핑 정보
            scene_id: 씬 ID
            action: 센서 행동

        Returns:
            배경 영상 파일명 또는 None
        """
        # cut.txt 기반 매핑 구조: sensor_mapping 사용
        if 'sensor_mapping' in mapping:
            scene_key = str(scene_id)
            if scene_key not in mapping['sensor_mapping']:
                print(f"[ActionMapper] 경고: 씬 {scene_id}가 sensor_mapping에 없음")
                return None

            scene_mapping = mapping['sensor_mapping'][scene_key]

            # 정확한 행동 매핑이 있으면 반환
            if action in scene_mapping:
                print(f"[ActionMapper] 씬 {scene_id}, 행동 '{action}' → {scene_mapping[action]}")
                return scene_mapping[action]

            # 없으면 기본값 반환
            default_video = scene_mapping.get('default')
            print(f"[ActionMapper] 씬 {scene_id}, 행동 '{action}' 없음. 기본값 사용 → {default_video}")
            return default_video

        # 레거시 구조: scene_X 형식 (하위 호환성)
        scene_key = f'scene_{scene_id}'

        if scene_key not in mapping:
            print(f"[ActionMapper] 경고: {scene_key}가 매핑에 없음")
            return None

        scene_mapping = mapping[scene_key]

        # 정확한 행동 매핑이 있으면 반환
        if action in scene_mapping:
            return scene_mapping[action]

        # 없으면 기본값 반환
        return scene_mapping.get('default')

    def create_transition_rules(
        self,
        mapping: Dict[str, Any],
        model: str = "gpt-4o"
    ) -> Dict[str, Any]:
        """
        배경 전환 규칙 생성 (선택적)

        예: walk -> run은 즉시 전환 가능, stop -> run은 walk 거쳐야 함 등

        Args:
            mapping: 매핑 정보
            model: GPT 모델

        Returns:
            전환 규칙
        """
        # 간단한 기본 규칙
        transition_rules = {
            'direct_transitions': [
                ['stop', 'walk'],
                ['walk', 'run'],
                ['run', 'walk'],
                ['walk', 'stop'],
                ['stop', 'fall'],
                ['walk', 'fall'],
                ['run', 'fall']
            ],
            'forbidden_transitions': [
                ['stop', 'run'],  # stop에서 run으로 직접 불가 (walk 거쳐야 함)
            ],
            'transition_duration': 1.0  # 크로스디졸브 시간 (초)
        }

        return transition_rules


if __name__ == "__main__":
    # 테스트 코드
    mapper = ActionMapper()

    # 샘플 배경 계획
    background_plan = {
        'scenes': [
            {
                'scene_id': 1,
                'title': '버스 정류장',
                'description': '주인공이 버스를 기다린다',
                'actions': ['stop', 'walk'],
                'backgrounds_to_generate': [
                    {'action': 'stop', 'video_filename': 'S0001-action_stop.mp4'},
                    {'action': 'walk', 'video_filename': 'S0001-action_walk.mp4'},
                ]
            }
        ]
    }

    generated_videos = {
        'S0001-stop': '/path/to/S0001-action_stop.mp4',
        'S0001-walk': '/path/to/S0001-action_walk.mp4',
    }

    sensor_actions = ['stop', 'walk', 'run', 'fall', 'turn', 'shout', 'dark', 'bright']

    # 매핑 생성
    mapping = mapper.create_mapping(
        background_plan, generated_videos, sensor_actions
    )

    print(f"\n생성된 매핑:\n{json.dumps(mapping, ensure_ascii=False, indent=2)}")

    # 특정 행동에 대한 배경 조회
    bg = mapper.get_background_for_action(mapping, 1, 'walk')
    print(f"\n씬 1, 행동 'walk': {bg}")

    # 전환 규칙 생성
    rules = mapper.create_transition_rules(mapping)
    print(f"\n전환 규칙:\n{json.dumps(rules, ensure_ascii=False, indent=2)}")
