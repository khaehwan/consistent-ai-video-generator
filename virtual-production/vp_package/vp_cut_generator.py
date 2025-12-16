"""
VP Cut Generator - VP 배경 영상을 위한 컷 생성기

story/cut.txt를 VP 형식으로 생성:
- 각 씬별로 필요한 액션들을 분석
- 각 씬-액션 조합마다 배경 중심 컷 생성
- cut_id는 씬별로 1부터 시작
- action 필드 추가
"""

import os
import json
import ast
from typing import List, Dict, Tuple, Any

from .scene_analyzer import VPSceneAnalyzer
from .entity_filter import EntityFilter


class VPCutGenerator:
    """VP 배경용 컷 생성기"""

    def __init__(self, work_dir: str, entity_set_name: str):
        """
        Args:
            work_dir: 작업 디렉토리 경로
            entity_set_name: 엔티티 세트 이름
        """
        self.work_dir = work_dir
        self.entity_set_name = entity_set_name
        self.base_path = os.path.join(work_dir, entity_set_name)

        # 경로 설정
        self.story_path = os.path.join(self.base_path, 'story')

        # 컴포넌트 초기화
        self.scene_analyzer = VPSceneAnalyzer()
        self.entity_filter = EntityFilter()

    def generate_vp_cuts(
        self,
        scenes: List[Dict],
        story_text: str,
        entity_list: List[Tuple[str, str, str, str]],
        model: str = "gpt-4.1"
    ) -> List[List[Dict]]:
        """
        VP 배경용 컷 생성

        Args:
            scenes: 씬 리스트
            story_text: 전체 스토리 텍스트
            entity_list: 엔티티 리스트
            model: LLM 모델명

        Returns:
            List[List[Dict]]: 씬별 컷 리스트
        """
        print(f"\n[VPCutGenerator] VP 컷 생성 시작")
        print(f"[VPCutGenerator] 씬 개수: {len(scenes)}")

        all_cuts = []

        # 1. 씬별 액션 분석
        print(f"\n[VPCutGenerator] 1단계: 씬별 액션 분석 중...")
        scene_actions = self.scene_analyzer.analyze_all_scenes(
            scenes, story_text, model
        )
        print(f"[VPCutGenerator] 액션 분석 완료: {len(scene_actions)}개 씬")

        # 2. 주인공 식별
        print(f"\n[VPCutGenerator] 2단계: 주인공 식별 중...")
        protagonist_names = self._identify_protagonist(
            scenes, story_text, entity_list, model
        )
        print(f"[VPCutGenerator] 식별된 주인공: {protagonist_names}")

        # 3. 씬별로 VP 컷 생성
        print(f"\n[VPCutGenerator] 3단계: 씬별 VP 컷 생성 중...")
        for i, scene in enumerate(scenes, 1):
            scene_id = scene.get('scene_id', i)
            actions = scene_actions.get(scene_id, [])

            if not actions:
                print(f"[VPCutGenerator] 씬 {scene_id}: 액션 없음, 스킵")
                continue

            print(f"\n[VPCutGenerator] 씬 {scene_id} 처리 중...")
            print(f"[VPCutGenerator]   액션 목록: {actions}")

            scene_cuts = []
            cut_id = 1

            for action in actions:
                print(f"[VPCutGenerator]   컷 {cut_id} ({action}) 생성 중...")

                # 배경 중심 컷 생성
                cut = self._create_background_cut(
                    scene=scene,
                    action=action,
                    cut_id=cut_id,
                    story_text=story_text,
                    entity_list=entity_list,
                    protagonist_names=protagonist_names,
                    model=model
                )

                scene_cuts.append(cut)
                cut_id += 1

            print(f"[VPCutGenerator] 씬 {scene_id}: {len(scene_cuts)}개 컷 생성 완료")
            all_cuts.append(scene_cuts)

        print(f"\n[VPCutGenerator] ✅ 전체 컷 생성 완료: {len(all_cuts)}개 씬")
        return all_cuts

    def _identify_protagonist(
        self,
        scenes: List[Dict],
        story_text: str,
        entity_list: List[Tuple[str, str, str, str]],
        model: str
    ) -> List[str]:
        """
        주인공 캐릭터 식별

        Returns:
            주인공 이름 리스트
        """
        # EntityFilter의 identify_protagonist 사용
        return self.entity_filter.identify_protagonist(
            entity_list, story_text, model
        )

    def _create_background_cut(
        self,
        scene: Dict,
        action: str,
        cut_id: int,
        story_text: str,
        entity_list: List[Tuple[str, str, str, str]],
        protagonist_names: List[str],
        model: str
    ) -> Dict:
        """
        배경 중심 컷 생성

        Returns:
            컷 딕셔너리 (action 필드 포함)
        """
        # 1. 주인공 제거된 엔티티 리스트
        filtered_entities = self.entity_filter.filter_protagonist(
            entity_list, protagonist_names
        )

        # 2. 씬 설명
        scene_desc = scene.get('description', scene.get('title', ''))

        # 3. 배경 중심 프롬프트 생성
        bg_description = self.entity_filter.rewrite_cut_for_background(
            cut_description=scene_desc,
            scene_description=scene_desc,
            entity_list=filtered_entities
        )

        # 4. 액션에 맞게 프롬프트 향상
        enhanced_description = self.entity_filter.enhance_for_action(
            bg_description, action
        )

        # 5. 엔티티 매칭 (location, object만)
        location_names = []
        object_names = []

        for ent_type, name, attrs, img_path in filtered_entities:
            if ent_type == 'location':
                # 씬에 해당 로케이션이 있는지 확인
                if any(name.lower() in str(v).lower() for v in scene.values()):
                    location_names.append(name)
            elif ent_type == 'object':
                # 씬에 해당 오브젝트가 있는지 확인
                if any(name.lower() in str(v).lower() for v in scene.values()):
                    object_names.append(name)

        # 6. 컷 딕셔너리 생성
        cut = {
            "cut_id": cut_id,
            "action": action,
            "description": enhanced_description,
            "character": [],  # VP 배경은 주인공 제외
            "location": location_names,
            "object": object_names
        }

        return cut

    def save_cuts(self, all_cuts: List[List[Dict]]):
        """
        cut.txt 저장 (표준 형식)

        Args:
            all_cuts: 씬별 컷 리스트
        """
        cut_file_path = os.path.join(self.story_path, 'cut.txt')

        print(f"\n[VPCutGenerator] cut.txt 저장 중: {cut_file_path}")

        os.makedirs(self.story_path, exist_ok=True)

        with open(cut_file_path, 'w', encoding='utf-8') as f:
            for scene_cuts in all_cuts:
                # 씬별로 한 줄에 저장
                line = json.dumps(scene_cuts, ensure_ascii=False)
                f.write(line + '\n')

        print(f"[VPCutGenerator] ✅ cut.txt 저장 완료")
        print(f"[VPCutGenerator] 총 {len(all_cuts)}개 씬, {sum(len(cuts) for cuts in all_cuts)}개 컷")

    def load_cuts(self) -> List[List[Dict]]:
        """
        cut.txt 로드

        Returns:
            씬별 컷 리스트
        """
        cut_file_path = os.path.join(self.story_path, 'cut.txt')

        if not os.path.exists(cut_file_path):
            return []

        all_cuts = []

        with open(cut_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    # JSON 파싱 시도
                    scene_cuts = json.loads(line)
                except json.JSONDecodeError:
                    # 실패시 ast.literal_eval 시도
                    scene_cuts = ast.literal_eval(line)

                all_cuts.append(scene_cuts)

        return all_cuts


if __name__ == "__main__":
    # 테스트 코드
    work_dir = "/Users/khh/Projects/cavg-demo"
    entity_set_name = "test_vp"

    generator = VPCutGenerator(work_dir, entity_set_name)

    # 샘플 데이터
    scenes = [
        {
            "scene_id": 1,
            "title": "버스 정류장",
            "description": "주인공이 버스 정류장에서 버스를 기다린다"
        }
    ]

    story_text = "주인공은 아침에 버스 정류장에 도착했다. 버스를 기다리며 벤치에 앉았다."

    entity_list = [
        ('character', '주인공', '{"나이": "20대"}', 'hero.png'),
        ('location', '버스 정류장', '{"설명": "도시"}', 'bus_stop.png'),
        ('object', '버스', '{"색상": "파란색"}', 'bus.png'),
        ('object', '벤치', '{"재질": "나무"}', 'bench.png'),
    ]

    # VP 컷 생성 (실제 테스트시 주석 해제)
    # cuts = generator.generate_vp_cuts(scenes, story_text, entity_list)
    # generator.save_cuts(cuts)
    # print(f"생성된 컷: {cuts}")
