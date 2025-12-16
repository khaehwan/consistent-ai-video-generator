"""
Virtual Production Package for Consistent AI Video Generator

이 패키지는 consistentvideo를 확장하여 버츄얼 프로덕션 배경 영상 생성 기능을 제공합니다.
- 주인공을 제외한 배경 중심 영상 생성
- 센서 행동 기반 배경 영상 자동 매핑
- 실시간 배경 전환을 위한 웹 인터페이스
"""

from .entity_filter import EntityFilter
from .scene_analyzer import VPSceneAnalyzer
from .vp_cut_generator import VPCutGenerator
from .action_mapper import ActionMapper

__all__ = [
    'EntityFilter',
    'VPSceneAnalyzer',
    'VPCutGenerator',
    'ActionMapper',
]

__version__ = '1.0.0'
