"""
Pydantic Models for Virtual Production API
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class AnalyzeScenesRequest(BaseModel):
    """씬 분석 요청 (DEPRECATED: use GenerateVPCutsRequest)"""
    work_dir: str
    entity_set_name: str
    story_text: str
    model: str = "gpt-4o"


class AnalyzeScenesResponse(BaseModel):
    """씬 분석 응답 (DEPRECATED: use GenerateVPCutsResponse)"""
    scene_actions: Dict[int, List[str]]
    background_plan: Dict[str, Any]


class GenerateVPCutsRequest(BaseModel):
    """VP 컷 생성 요청"""
    work_dir: str
    entity_set_name: str
    story_text: str
    model: str = "gpt-4.1"


class GenerateVPCutsResponse(BaseModel):
    """VP 컷 생성 응답"""
    cuts_generated: int  # 생성된 컷 개수
    scenes_processed: int  # 처리된 씬 개수
    message: str


class GenerateBackgroundsRequest(BaseModel):
    """배경 생성 요청 (DEPRECATED: use GenerateVPVideosRequest)"""
    work_dir: str
    entity_set_name: str
    image_model: str = "gpt-image-1"
    video_model: str = "veo-3.0-fast-generate-preview"
    style: str = "realistic"
    quality: str = "medium"
    size: str = "1024x1024"


class GenerateBackgroundsResponse(BaseModel):
    """배경 생성 응답 (DEPRECATED: use GenerateVPVideosResponse)"""
    generated_videos: Dict[str, str]
    message: str


class GenerateVPVideosRequest(BaseModel):
    """VP 비디오 생성 요청"""
    work_dir: str
    entity_set_name: str
    image_model: str = "gpt-image-1"
    video_model: str = "veo-3.0-fast-generate-preview"
    style: str = "realistic"
    quality: str = "medium"
    size: str = "1024x1024"


class GenerateVPVideosResponse(BaseModel):
    """VP 비디오 생성 응답"""
    videos_generated: int  # 생성된 비디오 개수
    images_generated: int  # 생성된 이미지 개수
    message: str


class GenerateMappingRequest(BaseModel):
    """매핑 생성 요청"""
    work_dir: str
    entity_set_name: str
    model: str = "gpt-4o"


class GenerateMappingResponse(BaseModel):
    """매핑 생성 응답"""
    mapping: Dict[str, Any]
    message: str


class UpdateMappingRequest(BaseModel):
    """매핑 수정 요청"""
    work_dir: str
    entity_set_name: str
    scene_id: int
    action: str
    video_filename: str


class LoadMappingResponse(BaseModel):
    """매핑 로드 응답"""
    mapping: Optional[Dict[str, Any]]


class ChangeSceneRequest(BaseModel):
    """씬 변경 요청"""
    scene_id: int


class SimulateActionRequest(BaseModel):
    """행동 시뮬레이션 요청"""
    action: str
    metadata: Optional[Dict[str, Any]] = None


class SensorEvent(BaseModel):
    """센서 이벤트"""
    timestamp: str
    sensor_id: str
    behavior: str
    metadata: Optional[Dict[str, Any]] = None


class BackgroundInfo(BaseModel):
    """배경 정보"""
    scene_id: int
    action: str
    video_filename: str
    video_url: str


class PreviewItem(BaseModel):
    """미리보기 아이템"""
    scene_id: int
    action: str
    video_filename: str
    video_url: str
    thumbnail_url: Optional[str] = None
