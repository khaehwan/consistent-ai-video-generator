"""
VP Scene Analyzer - 버츄얼 프로덕션을 위한 씬 분석

각 씬에서 필요한 배우 행동을 분석하고, 필요한 배경 영상 목록을 생성합니다.
"""

import json
from typing import List, Dict, Any, Optional
from openai import OpenAI


class VPSceneAnalyzer:
    """버츄얼 프로덕션을 위한 씬 분석기"""

    # 웨어러블 센서 및 Kinect에서 감지 가능한 행동 목록
    AVAILABLE_SENSOR_ACTIONS = [
        # Wearable sensor actions
        'stop',      # 정지 상태
        'walk',      # 걷기
        'run',       # 달리기
        'fall',      # 낙상
        'turn',      # 뒤돌아보기
        'shout',     # 소리지르기
        'dark',      # 어두워짐
        'bright',    # 밝아짐
        # Kinect posture actions
        'standing',      # 서있음
        'sitting',       # 앉음
        'lying',         # 누움
        'left_arm_up',   # 왼팔 들기
        'right_arm_up',  # 오른팔 들기
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI API 키 (없으면 환경변수 사용)
        """
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()

    def analyze_scene_actions(
        self,
        scene: Dict[str, Any],
        story_text: str,
        model: str = "gpt-4o"
    ) -> List[str]:
        """
        씬에서 필요한 배우 행동 분석

        Args:
            scene: 씬 정보 {'scene_id': 1, 'title': '...', 'description': '...'}
            story_text: 전체 스토리 텍스트
            model: 사용할 GPT 모델

        Returns:
            필요한 행동 목록 (예: ['stop', 'walk', 'run'])
        """
        scene_id = scene.get('scene_id', 0)
        scene_title = scene.get('title', '')
        scene_desc = scene.get('description', '')

        # 스토리에서 해당 씬 부분 추출 (간단한 휴리스틱)
        scene_story_part = self._extract_scene_story(story_text, scene_id, scene_title)

        prompt = f"""다음 씬에서 주인공이 취할 수 있는 행동을 분석해주세요.

씬 {scene_id}: {scene_title}
설명: {scene_desc}

스토리 부분:
{scene_story_part}

센서(웨어러블/Kinect)가 감지할 수 있는 행동:
{json.dumps(self.AVAILABLE_SENSOR_ACTIONS, ensure_ascii=False, indent=2)}

각 행동의 의미:
[웨어러블 센서]
- stop: 정지해 있음
- walk: 걷기
- run: 달리기
- fall: 넘어짐
- turn: 뒤돌아보기
- shout: 소리지름
- dark: 어두운 환경으로 변화
- bright: 밝은 환경으로 변화

[Kinect 자세]
- standing: 서있음
- sitting: 앉아있음
- lying: 누워있음
- left_arm_up: 왼팔을 들어올림
- right_arm_up: 오른팔을 들어올림

요구사항:
1. 이 씬에서 주인공이 할 가능성이 있는 모든 행동을 선택
2. 기본적으로 'standing' 또는 'stop'은 항상 포함 (기본 상태)
3. 환경 변화(dark/bright)도 씬 설명에 있으면 포함
4. 버츄얼 프로덕션을 위해 필요한 최소한의 행동만 선택

JSON 형식으로 응답:
{{"actions": ["stop", "walk", ...]}}
"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert in virtual production and cinematography."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            actions = result.get('actions', ['stop'])

            # 유효한 행동만 필터링
            valid_actions = [
                action for action in actions
                if action in self.AVAILABLE_SENSOR_ACTIONS
            ]

            # stop은 항상 포함
            if 'stop' not in valid_actions:
                valid_actions.insert(0, 'stop')

            return valid_actions

        except Exception as e:
            print(f"씬 행동 분석 중 오류: {e}")
            # 기본값: stop만 포함
            return ['stop']

    def analyze_all_scenes(
        self,
        scenes: List[Dict[str, Any]],
        story_text: str,
        model: str = "gpt-4o"
    ) -> Dict[int, List[str]]:
        """
        모든 씬의 행동 분석

        Args:
            scenes: 씬 목록
            story_text: 전체 스토리 텍스트
            model: 사용할 GPT 모델

        Returns:
            씬 ID별 행동 목록 {1: ['stop', 'walk'], 2: ['stop', 'run'], ...}
        """
        scene_actions = {}

        for scene in scenes:
            scene_id = scene.get('scene_id', 0)
            actions = self.analyze_scene_actions(scene, story_text, model)
            scene_actions[scene_id] = actions
            print(f"씬 {scene_id}: {actions}")

        return scene_actions

    def _extract_scene_story(
        self,
        story_text: str,
        scene_id: int,
        scene_title: str
    ) -> str:
        """
        스토리에서 해당 씬에 해당하는 부분을 추출

        간단한 휴리스틱: 스토리를 문단으로 나눠서 scene_id에 해당하는 부분 반환

        Args:
            story_text: 전체 스토리
            scene_id: 씬 ID
            scene_title: 씬 제목

        Returns:
            씬에 해당하는 스토리 부분
        """
        # 문단으로 분리
        paragraphs = [p.strip() for p in story_text.split('\n\n') if p.strip()]

        if not paragraphs:
            return story_text[:500]

        # scene_id에 해당하는 문단 선택 (간단히 인덱스 사용)
        idx = min(scene_id - 1, len(paragraphs) - 1)

        # 해당 문단과 앞뒤 문단 일부 포함
        start_idx = max(0, idx - 1)
        end_idx = min(len(paragraphs), idx + 2)

        scene_part = '\n\n'.join(paragraphs[start_idx:end_idx])

        # 너무 길면 잘라내기
        if len(scene_part) > 1000:
            scene_part = scene_part[:1000] + "..."

        return scene_part

    def create_background_plan(
        self,
        scenes: List[Dict[str, Any]],
        scene_actions: Dict[int, List[str]],
        cuts_by_scene: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        배경 영상 생성 계획 작성

        Args:
            scenes: 씬 목록
            scene_actions: 씬별 행동 목록
            cuts_by_scene: 씬별 컷 목록

        Returns:
            배경 생성 계획
            {
                'scenes': [
                    {
                        'scene_id': 1,
                        'title': '...',
                        'actions': ['stop', 'walk'],
                        'backgrounds_to_generate': [
                            {'action': 'stop', 'filename': 'S0001-action_stop'},
                            {'action': 'walk', 'filename': 'S0001-action_walk'}
                        ]
                    },
                    ...
                ]
            }
        """
        plan = {'scenes': []}

        for scene in scenes:
            scene_id = scene.get('scene_id', 0)
            scene_title = scene.get('title', '')
            actions = scene_actions.get(scene_id, ['stop'])

            # 각 행동별 배경 파일명 생성
            backgrounds = []
            for action in actions:
                backgrounds.append({
                    'action': action,
                    'filename': f'S{scene_id:04d}-action_{action}',
                    'video_filename': f'S{scene_id:04d}-action_{action}.mp4'
                })

            scene_plan = {
                'scene_id': scene_id,
                'title': scene_title,
                'description': scene.get('description', ''),
                'actions': actions,
                'backgrounds_to_generate': backgrounds
            }

            # 해당 씬의 컷 정보 추가 (첫 번째 컷을 기준으로 사용)
            if scene_id - 1 < len(cuts_by_scene) and cuts_by_scene[scene_id - 1]:
                first_cut = cuts_by_scene[scene_id - 1][0]
                scene_plan['base_cut'] = first_cut

            plan['scenes'].append(scene_plan)

        return plan

    def get_sensor_actions(self) -> List[str]:
        """
        웨어러블 센서가 감지할 수 있는 행동 목록 반환

        Returns:
            센서 행동 목록
        """
        return self.AVAILABLE_SENSOR_ACTIONS.copy()


if __name__ == "__main__":
    # 테스트 코드
    analyzer = VPSceneAnalyzer()

    # 샘플 씬
    scenes = [
        {
            'scene_id': 1,
            'title': '버스 정류장',
            'description': '주인공이 버스를 기다린다'
        },
        {
            'scene_id': 2,
            'title': '달리기',
            'description': '주인공이 늦어서 버스를 향해 달린다'
        }
    ]

    story = """
    주인공은 버스 정류장에서 버스를 기다렸다.

    버스가 멀리서 보이자 주인공은 달려갔다.
    """

    # 씬별 행동 분석
    scene_actions = analyzer.analyze_all_scenes(scenes, story)
    print(f"씬별 행동: {scene_actions}")

    # 배경 생성 계획
    cuts_by_scene = [
        [{'cut_id': 1, 'description': '버스 정류장 풍경'}],
        [{'cut_id': 1, 'description': '버스가 다가오는 거리'}]
    ]
    plan = analyzer.create_background_plan(scenes, scene_actions, cuts_by_scene)
    print(f"배경 생성 계획: {json.dumps(plan, ensure_ascii=False, indent=2)}")
