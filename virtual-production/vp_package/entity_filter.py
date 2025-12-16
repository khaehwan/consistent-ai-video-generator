"""
Entity Filter - 버츄얼 프로덕션을 위한 엔티티 필터링

주인공을 제거하고 배경/엑스트라 중심의 프롬프트를 생성합니다.
"""

import json
from typing import List, Tuple, Dict, Any, Optional
from openai import OpenAI


class EntityFilter:
    """주인공을 제거하고 배경 중심의 엔티티 리스트를 생성"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI API 키 (없으면 환경변수 사용)
        """
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()

    def filter_protagonist(
        self,
        entity_list: List[Tuple[str, str, str, str]],
        protagonist_names: List[str]
    ) -> List[Tuple[str, str, str, str]]:
        """
        주인공을 엔티티 리스트에서 제거

        Args:
            entity_list: 엔티티 리스트 [('type', 'name', 'description_json', 'image_path'), ...]
            protagonist_names: 제거할 주인공 이름 리스트

        Returns:
            주인공이 제거된 엔티티 리스트
        """
        filtered = []
        for entity in entity_list:
            entity_type, entity_name, description, image_path = entity

            # 캐릭터 타입이고 주인공 이름에 포함되면 제외
            if entity_type == 'character':
                # 이름이 정확히 일치하거나 부분 일치하는 경우 제외
                is_protagonist = any(
                    pname in entity_name or entity_name in pname
                    for pname in protagonist_names
                )
                if is_protagonist:
                    continue

            filtered.append(entity)

        return filtered

    def identify_protagonist(
        self,
        entity_list: List[Tuple[str, str, str, str]],
        story_text: str,
        model: str = "gpt-4o"
    ) -> List[str]:
        """
        스토리 텍스트를 분석하여 주인공 이름을 자동으로 식별

        Args:
            entity_list: 엔티티 리스트
            story_text: 스토리 텍스트
            model: 사용할 GPT 모델

        Returns:
            주인공으로 식별된 캐릭터 이름 리스트
        """
        # 캐릭터만 추출 (이름만)
        characters = [
            name for typ, name, desc, _ in entity_list
            if typ == 'character'
        ]

        if not characters:
            return []

        # 캐릭터 이름만 나열 (간단하게)
        character_list = ", ".join(characters)

        prompt = f"""다음 스토리의 주인공(protagonist)을 식별해주세요.

스토리:
{story_text[:1500]}

캐릭터 목록:
{character_list}

주인공은 스토리의 중심 인물로, 시점 인물("나", "저")이거나 가장 많이 등장하는 인물입니다.
버츄얼 프로덕션에서는 주인공을 배경에서 제외해야 합니다.

**중요**: 반드시 다음 JSON 형식으로만 응답하세요:
{{"protagonists": ["이름1", "이름2"]}}

주인공이 없거나 시점 인물("나", "저")만 있다면:
{{"protagonists": []}}

응답:"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert in story analysis. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()

            # JSON 파싱 시도
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 간단한 매칭 시도
                print(f"주인공 식별 JSON 파싱 실패, 빈 리스트 반환")
                return []

            protagonist_names = result.get('protagonists', result.get('주인공', []))

            # 리스트인지 확인
            if not isinstance(protagonist_names, list):
                return []

            # 캐릭터 리스트에 있는 이름만 필터링
            valid_protagonists = [
                name for name in protagonist_names
                if name in characters
            ]

            return valid_protagonists

        except Exception as e:
            print(f"주인공 식별 중 오류: {e}")
            return []

    def rewrite_cut_for_background(
        self,
        cut_description: str,
        scene_description: str,
        entity_list: List[Tuple[str, str, str, str]],
        model: str = "gpt-4o"
    ) -> str:
        """
        컷 설명을 배경 중심으로 재작성

        Args:
            cut_description: 원본 컷 설명 (주인공 포함)
            scene_description: 씬 설명
            entity_list: 배경 엔티티 리스트 (주인공 제외됨)
            model: 사용할 GPT 모델

        Returns:
            배경 중심으로 재작성된 컷 설명
        """
        # 엔티티 정보 추출
        locations = [name for typ, name, _, _ in entity_list if typ == 'location']
        objects = [name for typ, name, _, _ in entity_list if typ == 'object']
        extras = [name for typ, name, _, _ in entity_list if typ == 'character']

        entity_info = ""
        if locations:
            entity_info += f"배경: {', '.join(locations)}\n"
        if objects:
            entity_info += f"사물: {', '.join(objects)}\n"
        if extras:
            entity_info += f"엑스트라: {', '.join(extras)}\n"

        prompt = f"""다음 컷 설명을 버츄얼 프로덕션 배경용으로 재작성해주세요.

씬: {scene_description}

원본 컷 설명:
{cut_description}

사용 가능한 엔티티:
{entity_info}

요구사항:
1. 주인공의 행동이나 주인공 자체를 제거하고, 배경과 환경에 집중
2. 엑스트라가 있다면 그들의 자연스러운 행동 포함
3. 카메라 앵글과 분위기는 유지
4. 영상 생성 AI를 위한 영어 프롬프트로 작성
5. 배경이 살아있는 느낌을 주도록 미세한 움직임 포함 (나뭇잎 흔들림, 사람들 움직임 등)

배경 중심 설명 (영어):"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert in virtual production and cinematography."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            background_description = response.choices[0].message.content.strip()
            return background_description

        except Exception as e:
            print(f"배경 설명 재작성 중 오류: {e}")
            # 오류 시 간단한 대체 설명 반환
            return f"Background scene of {scene_description}, without main protagonist, focusing on environment and atmosphere."

    def enhance_for_action(
        self,
        background_description: str,
        action: str,
        model: str = "gpt-4o"
    ) -> str:
        """
        배경 설명에 행동별 특성 추가

        Args:
            background_description: 기본 배경 설명
            action: 센서 행동 (stop, walk, run, fall, turn, shout, dark, bright)
            model: 사용할 GPT 모델

        Returns:
            행동에 맞게 향상된 배경 설명
        """
        action_guidelines = {
            'stop': '정적인 배경, 미세한 환경 움직임만 (나뭇잎, 먼 사람들)',
            'walk': '보통 속도의 배경 움직임, 걷는 속도에 맞는 카메라 트래킹',
            'run': '빠른 배경 움직임, 다이나믹한 카메라 워크',
            'fall': '갑작스런 변화, 낙상 직후의 주변 반응 (엑스트라들의 놀람)',
            'turn': '회전하는 시점, 뒤돌아보는 각도로 배경 표현',
            'shout': '소리에 반응하는 주변 환경 (엑스트라들이 돌아봄)',
            'dark': '어두운 조명, 저조도 분위기',
            'bright': '밝은 조명, 고조도 분위기',
        }

        guideline = action_guidelines.get(action, '')

        if not guideline:
            return background_description

        prompt = f"""다음 배경 설명을 '{action}' 행동에 맞게 조정해주세요.

기본 배경 설명:
{background_description}

행동: {action}
가이드라인: {guideline}

요구사항:
- 기본 배경은 유지하되, {action} 행동에 맞는 카메라 워크나 환경 변화 추가
- 영상 생성 AI가 이해할 수 있도록 구체적으로 설명
- 영어로 작성

조정된 배경 설명:"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert in cinematography and camera work."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            enhanced_description = response.choices[0].message.content.strip()
            return enhanced_description

        except Exception as e:
            print(f"배경 향상 중 오류: {e}")
            # 오류 시 간단히 가이드라인 추가
            return f"{background_description}. {guideline}"


if __name__ == "__main__":
    # 테스트 코드
    import ast

    # 샘플 엔티티 리스트
    entity_list = [
        ('character', '홍길동', '{"나이": "20대", "성별": "남성"}', 'hong.png'),
        ('character', '김철수(엑스트라)', '{"나이": "30대", "성별": "남성"}', 'kim.png'),
        ('location', '버스 내부', '{"설명": "시내버스"}', 'bus.png'),
        ('object', '버스 손잡이', '{"설명": "노란색"}', 'handle.png'),
    ]

    filter = EntityFilter()

    # 주인공 식별 테스트
    story = "홍길동은 버스에 탔다. 김철수가 앉아있다."
    protagonists = filter.identify_protagonist(entity_list, story)
    print(f"식별된 주인공: {protagonists}")

    # 주인공 필터링 테스트
    filtered = filter.filter_protagonist(entity_list, protagonists)
    print(f"필터링된 엔티티: {filtered}")

    # 배경 설명 재작성 테스트
    cut_desc = "홍길동이 버스에서 내린다"
    scene_desc = "버스 정류장"
    bg_desc = filter.rewrite_cut_for_background(cut_desc, scene_desc, filtered)
    print(f"배경 설명: {bg_desc}")

    # 행동별 향상 테스트
    enhanced = filter.enhance_for_action(bg_desc, "walk")
    print(f"향상된 설명 (walk): {enhanced}")
