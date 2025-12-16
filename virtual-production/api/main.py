"""
Virtual Production FastAPI Server

버츄얼 프로덕션 배경 생성 및 실시간 배경 전환을 위한 API 서버
"""

import os
import sys
import json
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
from datetime import datetime

# VP 패키지 import
# virtual-production 폴더를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from vp_package.scene_analyzer import VPSceneAnalyzer
from vp_package.action_mapper import ActionMapper
from vp_package.entity_filter import EntityFilter
from vp_package.vp_cut_generator import VPCutGenerator

# consistentvideo 패키지 import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from consistentvideo.video.cut_image_generator import CutImageGenerator
from consistentvideo.video.video_generator import VideoGenerator

# Pydantic 모델
from models import (
    AnalyzeScenesRequest, AnalyzeScenesResponse,
    GenerateBackgroundsRequest, GenerateBackgroundsResponse,
    GenerateVPCutsRequest, GenerateVPCutsResponse,
    GenerateVPVideosRequest, GenerateVPVideosResponse,
    GenerateMappingRequest, GenerateMappingResponse,
    UpdateMappingRequest, LoadMappingResponse,
    ChangeSceneRequest, SimulateActionRequest,
    SensorEvent, BackgroundInfo, PreviewItem
)

# FastAPI 앱 생성
app = FastAPI(
    title="Virtual Production API",
    description="버츄얼 프로덕션 배경 생성 및 실시간 배경 전환 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 상태
class VPState:
    def __init__(self):
        self.current_scene_id = 1
        self.current_action = "stop"
        self.current_background = None
        self.mapping = None
        self.work_dir = None
        self.entity_set_name = None
        self.websocket_clients: List[WebSocket] = []

vp_state = VPState()


# ============= 유틸리티 함수 =============

def load_entity_list(work_dir: str, entity_set_name: str) -> List[tuple]:
    """엔티티 리스트 로드"""
    entity_list_path = os.path.join(
        work_dir, entity_set_name, 'reference', 'entity_list.txt'
    )

    if not os.path.exists(entity_list_path):
        raise HTTPException(status_code=404, detail="Entity list not found")

    entities = []
    with open(entity_list_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    entities.append(ast.literal_eval(line.strip()))
                except:
                    continue

    return entities


def load_scenes(work_dir: str, entity_set_name: str) -> List[Dict]:
    """씬 로드"""
    scene_path = os.path.join(work_dir, entity_set_name, 'story', 'scene.txt')

    if not os.path.exists(scene_path):
        raise HTTPException(status_code=404, detail="Scenes not found")

    scenes = []
    with open(scene_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    scenes.append(ast.literal_eval(line.strip()))
                except:
                    continue

    return scenes


def load_cuts(work_dir: str, entity_set_name: str) -> List[List[Dict]]:
    """컷 로드"""
    cut_path = os.path.join(work_dir, entity_set_name, 'story', 'cut.txt')

    if not os.path.exists(cut_path):
        raise HTTPException(status_code=404, detail="Cuts not found")

    cuts_by_scene = []
    with open(cut_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    cuts_by_scene.append(ast.literal_eval(line.strip()))
                except:
                    continue

    return cuts_by_scene


def load_story_text(work_dir: str, entity_set_name: str) -> str:
    """스토리 텍스트 로드"""
    story_path = os.path.join(work_dir, entity_set_name, 'story', 'story_text.txt')

    if not os.path.exists(story_path):
        raise HTTPException(status_code=404, detail="Story text not found")

    with open(story_path, 'r', encoding='utf-8') as f:
        return f.read()


async def broadcast_to_clients(message: Dict[str, Any]):
    """모든 WebSocket 클라이언트에 메시지 브로드캐스트"""
    print(f"[Broadcast] {len(vp_state.websocket_clients)}개 클라이언트에게 메시지 전송")
    disconnected = []
    for client in vp_state.websocket_clients:
        try:
            await client.send_json(message)
            print(f"[Broadcast] 클라이언트에게 전송 성공")
        except Exception as e:
            print(f"[Broadcast] 클라이언트 전송 실패: {e}")
            disconnected.append(client)

    # 연결 끊긴 클라이언트 제거
    for client in disconnected:
        vp_state.websocket_clients.remove(client)


# ============= VP 생성 엔드포인트 =============

@app.post("/vp/analyze-scenes", response_model=AnalyzeScenesResponse)
async def analyze_scenes(request: AnalyzeScenesRequest):
    """씬별 필요 행동 분석"""
    try:
        print(f"\n{'='*60}")
        print(f"[VP Analyze] 씬 분석 시작")
        print(f"{'='*60}")
        print(f"[VP Analyze] Work Directory: {request.work_dir}")
        print(f"[VP Analyze] Entity Set Name: {request.entity_set_name}")

        # 필요한 파일 경로 정의
        entity_list_path = os.path.join(request.work_dir, request.entity_set_name, 'reference', 'entity_list.txt')
        scene_path = os.path.join(request.work_dir, request.entity_set_name, 'story', 'scene.txt')
        cut_path = os.path.join(request.work_dir, request.entity_set_name, 'story', 'cut.txt')

        # 파일 존재 여부 확인 및 출력
        print(f"\n[VP Analyze] 필수 파일 확인:")
        print(f"  1. Entity List:")
        print(f"     경로: {entity_list_path}")
        print(f"     존재: {os.path.exists(entity_list_path)}")

        print(f"  2. Scene File:")
        print(f"     경로: {scene_path}")
        print(f"     존재: {os.path.exists(scene_path)}")

        print(f"  3. Cut File:")
        print(f"     경로: {cut_path}")
        print(f"     존재: {os.path.exists(cut_path)}")

        # 누락된 파일 목록
        missing_files = []
        if not os.path.exists(entity_list_path):
            missing_files.append(f"entity_list.txt ({entity_list_path})")
        if not os.path.exists(scene_path):
            missing_files.append(f"scene.txt ({scene_path})")
        if not os.path.exists(cut_path):
            missing_files.append(f"cut.txt ({cut_path})")

        if missing_files:
            print(f"\n[VP Analyze] ❌ 오류: 필수 파일이 누락되었습니다:")
            for i, file in enumerate(missing_files, 1):
                print(f"     {i}. {file}")
            print(f"\n[VP Analyze] 힌트: consistentvideo 패키지를 사용하여 먼저 다음 작업을 수행하세요:")
            print(f"     1. SynopsisAnalyzer로 시놉시스 분석 → entity_list.txt 생성")
            print(f"     2. SceneGenerator로 씬 생성 → scene.txt 생성")
            print(f"     3. CutGenerator로 컷 생성 → cut.txt 생성")
            raise HTTPException(
                status_code=404,
                detail=f"필수 파일이 누락되었습니다: {', '.join([f.split(' (')[0] for f in missing_files])}"
            )

        print(f"\n[VP Analyze] ✅ 모든 필수 파일이 존재합니다. 로드를 시작합니다...\n")

        # 씬과 컷 로드
        scenes = load_scenes(request.work_dir, request.entity_set_name)
        cuts_by_scene = load_cuts(request.work_dir, request.entity_set_name)

        # 씬 분석
        analyzer = VPSceneAnalyzer()
        scene_actions = analyzer.analyze_all_scenes(
            scenes, request.story_text, request.model
        )

        # 배경 생성 계획
        background_plan = analyzer.create_background_plan(
            scenes, scene_actions, cuts_by_scene
        )

        # 계획 저장
        vp_path = os.path.join(request.work_dir, request.entity_set_name, 'virtual-production', 'mappings')
        os.makedirs(vp_path, exist_ok=True)
        plan_path = os.path.join(vp_path, 'background_plan.json')

        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(background_plan, f, ensure_ascii=False, indent=2)

        # 응답 데이터 로그 출력
        print(f"\n[VP Analyze] ✅ 씬 분석 완료!")
        print(f"[VP Analyze] scene_actions 타입: {type(scene_actions)}")
        print(f"[VP Analyze] scene_actions 키: {list(scene_actions.keys()) if isinstance(scene_actions, dict) else 'N/A'}")
        print(f"[VP Analyze] background_plan 타입: {type(background_plan)}")
        print(f"[VP Analyze] background_plan 키: {list(background_plan.keys()) if isinstance(background_plan, dict) else 'N/A'}")
        if isinstance(background_plan, dict) and 'backgrounds_to_generate' in background_plan:
            print(f"[VP Analyze] 생성할 배경 개수: {len(background_plan['backgrounds_to_generate'])}")
        print(f"[VP Analyze] background_plan.json 저장: {plan_path}")
        print(f"{'='*60}\n")

        return AnalyzeScenesResponse(
            scene_actions=scene_actions,
            background_plan=background_plan
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[VP Analyze] ❌ 오류 발생: {str(e)}")
        print(f"[VP Analyze] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[VP Analyze] 스택 트레이스:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vp/generate-backgrounds", response_model=GenerateBackgroundsResponse)
async def generate_backgrounds(request: GenerateBackgroundsRequest):
    """배경 영상 생성"""
    try:
        print(f"\n{'='*60}")
        print(f"[VP Generate] 배경 영상 생성 시작")
        print(f"{'='*60}")
        print(f"[VP Generate] Work Directory: {request.work_dir}")
        print(f"[VP Generate] Entity Set Name: {request.entity_set_name}")
        print(f"[VP Generate] Image Model: {request.image_model}")
        print(f"[VP Generate] Video Model: {request.video_model}")
        print(f"[VP Generate] Style: {request.style}")
        print(f"[VP Generate] Quality: {request.quality}")
        print(f"[VP Generate] Size: {request.size}")

        # 필요한 파일 경로 정의
        plan_path = os.path.join(
            request.work_dir, request.entity_set_name,
            'virtual-production', 'mappings', 'background_plan.json'
        )
        entity_list_path = os.path.join(
            request.work_dir, request.entity_set_name,
            'reference', 'entity_list.txt'
        )

        # 파일 존재 여부 확인
        print(f"\n[VP Generate] 필수 파일 확인:")
        print(f"  1. Background Plan:")
        print(f"     경로: {plan_path}")
        print(f"     존재: {os.path.exists(plan_path)}")

        print(f"  2. Entity List:")
        print(f"     경로: {entity_list_path}")
        print(f"     존재: {os.path.exists(entity_list_path)}")

        if not os.path.exists(plan_path):
            print(f"\n[VP Generate] ❌ 오류: background_plan.json 파일이 없습니다.")
            raise HTTPException(status_code=404, detail="Background plan not found. Run analyze-scenes first.")

        print(f"\n[VP Generate] ✅ 필수 파일 확인 완료")

        # 배경 계획 로드
        print(f"[VP Generate] background_plan.json 로드 중...")
        with open(plan_path, 'r', encoding='utf-8') as f:
            background_plan = json.load(f)
        print(f"[VP Generate] 생성할 배경 개수: {len(background_plan.get('backgrounds_to_generate', []))}")

        # 엔티티 로드
        print(f"[VP Generate] entity_list.txt 로드 중...")
        entity_list = load_entity_list(request.work_dir, request.entity_set_name)
        print(f"[VP Generate] 엔티티 개수: {len(entity_list)}")

        # 배경 생성기
        print(f"\n[VP Generate] BackgroundGenerator 초기화 중...")
        generator = BackgroundGenerator(request.work_dir, request.entity_set_name)

        print(f"[VP Generate] 배경 영상 생성 시작...")
        print(f"[VP Generate] (이 과정은 시간이 오래 걸릴 수 있습니다)")
        generated_videos = generator.generate_background_videos(
            background_plan=background_plan,
            entity_list=entity_list,
            image_model=request.image_model,
            video_model=request.video_model,
            style=request.style,
            quality=request.quality,
            size=request.size
        )

        print(f"\n[VP Generate] ✅ 배경 영상 생성 완료!")
        print(f"[VP Generate] 생성된 영상 개수: {len(generated_videos)}")
        print(f"{'='*60}\n")

        return GenerateBackgroundsResponse(
            generated_videos=generated_videos,
            message=f"{len(generated_videos)} 배경 영상 생성 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[VP Generate] ❌ 오류 발생: {str(e)}")
        print(f"[VP Generate] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[VP Generate] 스택 트레이스:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vp/generate-mapping", response_model=GenerateMappingResponse)
async def generate_mapping(request: GenerateMappingRequest):
    """센서 행동 → 배경 영상 자동 매핑 (cut.txt 기반)"""
    try:
        print(f"\n{'='*60}")
        print(f"[VP Mapping] 센서-배경 매핑 생성 시작")
        print(f"{'='*60}")
        print(f"[VP Mapping] Work Directory: {request.work_dir}")
        print(f"[VP Mapping] Entity Set Name: {request.entity_set_name}")
        print(f"[VP Mapping] Model: {request.model}")

        # 필수 파일 경로
        cut_path = os.path.join(request.work_dir, request.entity_set_name, 'story', 'cut.txt')
        scene_path = os.path.join(request.work_dir, request.entity_set_name, 'story', 'scene.txt')
        video_output_path = os.path.join(request.work_dir, request.entity_set_name, 'video', 'output')

        # 파일 존재 여부 확인
        print(f"\n[VP Mapping] 필수 파일 확인:")
        print(f"  1. Cut File:")
        print(f"     경로: {cut_path}")
        print(f"     존재: {os.path.exists(cut_path)}")

        print(f"  2. Scene File:")
        print(f"     경로: {scene_path}")
        print(f"     존재: {os.path.exists(scene_path)}")

        print(f"  3. Video Output:")
        print(f"     경로: {video_output_path}")
        print(f"     존재: {os.path.exists(video_output_path)}")

        if not os.path.exists(cut_path):
            print(f"\n[VP Mapping] ❌ 오류: cut.txt 파일이 없습니다.")
            raise HTTPException(status_code=404, detail="cut.txt not found. Run /vp/generate-vp-cuts first.")

        if not os.path.exists(scene_path):
            print(f"\n[VP Mapping] ❌ 오류: scene.txt 파일이 없습니다.")
            raise HTTPException(status_code=404, detail="scene.txt not found.")

        if not os.path.exists(video_output_path):
            print(f"\n[VP Mapping] ❌ 오류: 비디오 출력 폴더가 없습니다.")
            print(f"[VP Mapping] 힌트: 먼저 /vp/generate-vp-videos를 실행하여 배경 영상을 생성하세요.")
            raise HTTPException(status_code=404, detail="Videos not found. Run /vp/generate-vp-videos first.")

        print(f"\n[VP Mapping] ✅ 필수 파일 확인 완료")

        # 데이터 로드
        print(f"[VP Mapping] cut.txt 로드 중...")
        cuts_by_scene = load_cuts(request.work_dir, request.entity_set_name)
        print(f"[VP Mapping] {len(cuts_by_scene)}개 씬 로드 완료")

        print(f"[VP Mapping] scene.txt 로드 중...")
        scenes = load_scenes(request.work_dir, request.entity_set_name)
        print(f"[VP Mapping] {len(scenes)}개 씬 로드 완료")

        # 매핑 생성
        print(f"\n[VP Mapping] ActionMapper 초기화 중...")
        mapper = ActionMapper()

        print(f"[VP Mapping] 센서 액션 목록 가져오는 중...")
        analyzer = VPSceneAnalyzer()
        sensor_actions = analyzer.get_sensor_actions()
        print(f"[VP Mapping] 센서 액션: {sensor_actions}")

        print(f"[VP Mapping] AI 모델을 사용하여 매핑 생성 중...")
        print(f"[VP Mapping] (LLM이 배경과 센서 행동을 자동 매칭합니다)")
        mapping = mapper.create_mapping_from_cuts(
            cuts_by_scene=cuts_by_scene,
            scenes=scenes,
            sensor_actions=sensor_actions,
            video_output_path=video_output_path,
            model=request.model
        )

        # 매핑 저장
        mappings_path = os.path.join(request.work_dir, request.entity_set_name, 'virtual-production', 'mappings')
        os.makedirs(mappings_path, exist_ok=True)
        mapping_path = os.path.join(mappings_path, 'action_mapping.json')

        print(f"\n[VP Mapping] 매핑 저장 중: {mapping_path}")
        mapper.save_mapping(mapping, mapping_path)

        # 전역 상태 업데이트 (sensor_mapping 부분만 사용)
        vp_state.mapping = mapping.get('sensor_mapping', {})
        vp_state.work_dir = request.work_dir
        vp_state.entity_set_name = request.entity_set_name

        # 씬 개수 계산 (sensor_mapping 제외)
        scene_count = len([k for k in mapping.keys() if k != 'sensor_mapping'])

        print(f"\n[VP Mapping] ✅ 매핑 생성 완료!")
        print(f"[VP Mapping] 씬 개수: {scene_count}")
        print(f"{'='*60}\n")

        return GenerateMappingResponse(
            mapping=mapping,
            message=f"{scene_count}개 씬 매핑 생성 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[VP Mapping] ❌ 오류 발생: {str(e)}")
        print(f"[VP Mapping] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[VP Mapping] 스택 트레이스:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vp/generate-vp-cuts", response_model=GenerateVPCutsResponse)
async def generate_vp_cuts(request: GenerateVPCutsRequest):
    """VP 배경용 컷 생성 (story/cut.txt)"""
    try:
        print(f"\n{'='*60}")
        print(f"[VP Cuts] VP 컷 생성 시작")
        print(f"{'='*60}")
        print(f"[VP Cuts] Work Directory: {request.work_dir}")
        print(f"[VP Cuts] Entity Set Name: {request.entity_set_name}")
        print(f"[VP Cuts] Model: {request.model}")

        # 필수 파일 확인
        entity_list_path = os.path.join(request.work_dir, request.entity_set_name, 'reference', 'entity_list.txt')
        scene_path = os.path.join(request.work_dir, request.entity_set_name, 'story', 'scene.txt')

        print(f"\n[VP Cuts] 필수 파일 확인:")
        print(f"  1. Entity List: {entity_list_path}")
        print(f"     존재: {os.path.exists(entity_list_path)}")
        print(f"  2. Scene File: {scene_path}")
        print(f"     존재: {os.path.exists(scene_path)}")

        if not os.path.exists(entity_list_path):
            raise HTTPException(status_code=404, detail="entity_list.txt not found")
        if not os.path.exists(scene_path):
            raise HTTPException(status_code=404, detail="scene.txt not found")

        # 데이터 로드
        print(f"\n[VP Cuts] 데이터 로드 중...")
        scenes = load_scenes(request.work_dir, request.entity_set_name)
        entity_list = load_entity_list(request.work_dir, request.entity_set_name)
        print(f"[VP Cuts] 씬 {len(scenes)}개, 엔티티 {len(entity_list)}개 로드 완료")

        # VP Cut Generator 초기화
        print(f"\n[VP Cuts] VPCutGenerator 초기화...")
        generator = VPCutGenerator(request.work_dir, request.entity_set_name)

        # VP 컷 생성
        print(f"[VP Cuts] VP 컷 생성 시작...")
        all_cuts = generator.generate_vp_cuts(
            scenes=scenes,
            story_text=request.story_text,
            entity_list=entity_list,
            model=request.model
        )

        # cut.txt 저장
        generator.save_cuts(all_cuts)

        cuts_count = sum(len(scene_cuts) for scene_cuts in all_cuts)

        print(f"\n[VP Cuts] ✅ VP 컷 생성 완료!")
        print(f"[VP Cuts] 씬: {len(all_cuts)}개, 컷: {cuts_count}개")
        print(f"{'='*60}\n")

        return GenerateVPCutsResponse(
            cuts_generated=cuts_count,
            scenes_processed=len(all_cuts),
            message=f"{len(all_cuts)}개 씬, {cuts_count}개 컷 생성 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[VP Cuts] ❌ 오류 발생: {str(e)}")
        print(f"[VP Cuts] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[VP Cuts] 스택 트레이스:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vp/generate-vp-videos", response_model=GenerateVPVideosResponse)
async def generate_vp_videos(request: GenerateVPVideosRequest):
    """VP 배경 영상 생성 (표준 파이프라인 사용)"""
    try:
        print(f"\n{'='*60}")
        print(f"[VP Videos] VP 영상 생성 시작")
        print(f"{'='*60}")
        print(f"[VP Videos] Work Directory: {request.work_dir}")
        print(f"[VP Videos] Entity Set Name: {request.entity_set_name}")
        print(f"[VP Videos] Image Model: {request.image_model}")
        print(f"[VP Videos] Video Model: {request.video_model}")

        # 필수 파일 확인
        cut_path = os.path.join(request.work_dir, request.entity_set_name, 'story', 'cut.txt')
        entity_list_path = os.path.join(request.work_dir, request.entity_set_name, 'reference', 'entity_list.txt')
        entity_image_path = os.path.join(request.work_dir, request.entity_set_name, 'reference', 'images')

        print(f"\n[VP Videos] 필수 파일 확인:")
        print(f"  1. Cut File: {cut_path}")
        print(f"     존재: {os.path.exists(cut_path)}")
        print(f"  2. Entity List: {entity_list_path}")
        print(f"     존재: {os.path.exists(entity_list_path)}")
        print(f"  3. Entity Images: {entity_image_path}")
        print(f"     존재: {os.path.exists(entity_image_path)}")

        if not os.path.exists(cut_path):
            raise HTTPException(status_code=404, detail="cut.txt not found. Run /vp/generate-vp-cuts first.")

        # 데이터 로드
        print(f"\n[VP Videos] 데이터 로드 중...")
        cuts_by_scene = load_cuts(request.work_dir, request.entity_set_name)
        entity_list = load_entity_list(request.work_dir, request.entity_set_name)
        print(f"[VP Videos] 씬 {len(cuts_by_scene)}개, 엔티티 {len(entity_list)}개 로드 완료")

        # 출력 디렉토리 설정
        output_base = os.path.join(request.work_dir, request.entity_set_name, 'video')
        image_output_path = os.path.join(output_base, 'cut-images')
        video_output_path = os.path.join(output_base, 'output')

        os.makedirs(image_output_path, exist_ok=True)
        os.makedirs(video_output_path, exist_ok=True)

        images_generated = 0
        videos_generated = 0

        # 씬별로 이미지 및 비디오 생성
        for scene_num, scene_cuts in enumerate(cuts_by_scene, 1):
            print(f"\n[VP Videos] 씬 {scene_num} 처리 중 ({len(scene_cuts)}개 컷)...")

            for cut in scene_cuts:
                cut_id = cut.get('cut_id', 1)
                action = cut.get('action', 'unknown')

                print(f"[VP Videos]   컷 {cut_id} (action: {action}) - 이미지 생성 중...")

                # 1. CutImageGenerator로 이미지 생성
                try:
                    cut_image_gen = CutImageGenerator(
                        scene_num=scene_num,
                        cut=cut,
                        output_path=image_output_path,
                        entity_image_path=entity_image_path,
                        entity=entity_list,
                        ai_model=request.image_model,
                        style=request.style,
                        quality=request.quality,
                        size=request.size
                    )

                    image_path = cut_image_gen.execute()
                    images_generated += 1
                    print(f"[VP Videos]     이미지 생성 완료: {image_path}")

                except Exception as e:
                    print(f"[VP Videos]     이미지 생성 실패: {e}")
                    continue

            # 2. VideoGenerator로 비디오 생성 (씬 단위)
            print(f"\n[VP Videos] 씬 {scene_num} 비디오 생성 중...")

            # cut_image_list 생성
            cut_image_list = []
            for cut in scene_cuts:
                cut_id = cut.get('cut_id', 1)
                image_filename = f'S{scene_num:04d}-C{cut_id:04d}.png'
                image_path = os.path.join(image_output_path, image_filename)

                if os.path.exists(image_path):
                    cut_image_list.append({
                        'scene_num': scene_num,
                        'cut_id': cut_id,
                        'image_path': image_path
                    })

            if cut_image_list:
                try:
                    video_gen = VideoGenerator(
                        cut_list=[scene_cuts],  # 씬별 컷 리스트
                        output_path=video_output_path,
                        cut_image_list=cut_image_list,
                        ai_model=request.video_model
                    )

                    video_gen.execute()
                    videos_generated += len(cut_image_list)
                    print(f"[VP Videos]   비디오 생성 완료: {len(cut_image_list)}개")

                except Exception as e:
                    print(f"[VP Videos]   비디오 생성 실패: {e}")

        print(f"\n[VP Videos] ✅ VP 영상 생성 완료!")
        print(f"[VP Videos] 이미지: {images_generated}개, 비디오: {videos_generated}개")
        print(f"{'='*60}\n")

        return GenerateVPVideosResponse(
            images_generated=images_generated,
            videos_generated=videos_generated,
            message=f"이미지 {images_generated}개, 비디오 {videos_generated}개 생성 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[VP Videos] ❌ 오류 발생: {str(e)}")
        print(f"[VP Videos] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[VP Videos] 스택 트레이스:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/vp/update-mapping")
async def update_mapping(request: UpdateMappingRequest):
    """매핑 수동 수정"""
    try:
        mapper = ActionMapper()
        mapping_path = os.path.join(
            request.work_dir, request.entity_set_name,
            'virtual-production', 'mappings', 'action_mapping.json'
        )

        # 기존 매핑 로드
        mapping = mapper.load_mapping(mapping_path)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        # 매핑 업데이트
        mapping = mapper.update_mapping(
            mapping, request.scene_id, request.action, request.video_filename
        )

        # 저장
        mapper.save_mapping(mapping, mapping_path)

        # 전역 상태 업데이트
        vp_state.mapping = mapping

        return {"message": "매핑 업데이트 완료", "mapping": mapping}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vp/load-mapping", response_model=LoadMappingResponse)
async def load_mapping(work_dir: str, entity_set_name: str):
    """매핑 로드"""
    try:
        mapper = ActionMapper()
        mapping_path = os.path.join(
            work_dir, entity_set_name,
            'virtual-production', 'mappings', 'action_mapping.json'
        )

        mapping = mapper.load_mapping(mapping_path)

        # 전역 상태 업데이트
        if mapping:
            vp_state.mapping = mapping
            vp_state.work_dir = work_dir
            vp_state.entity_set_name = entity_set_name

        return LoadMappingResponse(mapping=mapping)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 실시간 재생 엔드포인트 =============

@app.get("/vp/current-background")
async def get_current_background():
    """현재 재생 중인 배경 정보"""
    print(f"[VP API] 📺 Get current background request")
    print(f"[VP API] Current scene: {vp_state.current_scene_id}")
    print(f"[VP API] Current action: {vp_state.current_action}")

    if not vp_state.mapping:
        print(f"[VP API] ❌ No mapping loaded")
        raise HTTPException(status_code=404, detail="No mapping loaded")

    print(f"[VP API] Mapping keys: {list(vp_state.mapping.keys())}")

    # sensor_mapping에서 직접 조회
    scene_key = str(vp_state.current_scene_id)
    if 'sensor_mapping' in vp_state.mapping:
        sensor_mapping = vp_state.mapping['sensor_mapping']
        print(f"[VP API] Sensor mapping available for scenes: {list(sensor_mapping.keys())}")

        if scene_key in sensor_mapping:
            scene_sensor_map = sensor_mapping[scene_key]
            print(f"[VP API] Scene {scene_key} sensor mapping: {scene_sensor_map}")

            # 액션에 맞는 비디오 파일명 찾기
            video_filename = scene_sensor_map.get(
                vp_state.current_action,
                scene_sensor_map.get('default')
            )

            if video_filename:
                video_url = f"/vp/backgrounds/{video_filename}"
                print(f"[VP API] ✅ Found video: {video_filename}")
                print(f"[VP API] Video URL: {video_url}")

                return BackgroundInfo(
                    scene_id=vp_state.current_scene_id,
                    action=vp_state.current_action,
                    video_filename=video_filename,
                    video_url=video_url
                )
            else:
                print(f"[VP API] ⚠️ No video for action '{vp_state.current_action}'")
        else:
            print(f"[VP API] ⚠️ Scene {scene_key} not in sensor mapping")
    else:
        print(f"[VP API] ❌ No sensor_mapping in mapping")

    print(f"[VP API] ⚠️ No background found, returning empty")
    return {"message": "No background found"}


@app.post("/vp/change-scene")
async def change_scene(request: ChangeSceneRequest):
    """씬 수동 변경"""
    vp_state.current_scene_id = request.scene_id
    vp_state.current_action = "stop"  # 씬 변경 시 기본 행동으로 리셋

    # 새 배경 정보
    mapper = ActionMapper()
    video_filename = mapper.get_background_for_action(
        vp_state.mapping,
        vp_state.current_scene_id,
        vp_state.current_action
    )

    # 클라이언트에 브로드캐스트
    await broadcast_to_clients({
        "type": "scene_change",
        "scene_id": vp_state.current_scene_id,
        "action": vp_state.current_action,
        "new_background": video_filename
    })

    return {"message": f"씬 {request.scene_id}로 변경", "background": video_filename}


@app.post("/vp/simulate-action")
async def simulate_action(request: SimulateActionRequest):
    """센서 행동 시뮬레이션"""
    # 센서 이벤트 생성
    event = SensorEvent(
        timestamp=datetime.now().isoformat(),
        sensor_id="simulator",
        behavior=request.action,
        metadata=request.metadata or {}
    )

    # WebSocket으로 전파
    await handle_sensor_event(event)

    return {"message": f"행동 '{request.action}' 시뮬레이션 완료"}


async def handle_sensor_event(event: SensorEvent):
    """센서 이벤트 처리"""
    print(f"\n[Event Handler] ========================================")
    print(f"[Event Handler] 🎯 이벤트 처리 시작")
    print(f"[Event Handler] Sensor ID: {event.sensor_id}")
    print(f"[Event Handler] Behavior: {event.behavior}")
    print(f"[Event Handler] Current Scene: {vp_state.current_scene_id}")

    if not vp_state.mapping:
        print(f"[Event Handler] ❌ 경고: 매핑이 로드되지 않음")
        return

    vp_state.current_action = event.behavior

    print(f"[Event Handler] 📋 매핑 구조 확인:")
    print(f"[Event Handler]   - 매핑 키: {list(vp_state.mapping.keys())}")
    if 'sensor_mapping' in vp_state.mapping:
        print(f"[Event Handler]   - Sensor mapping 씬들: {list(vp_state.mapping['sensor_mapping'].keys())}")

    mapper = ActionMapper()
    video_filename = mapper.get_background_for_action(
        vp_state.mapping,
        vp_state.current_scene_id,
        event.behavior
    )

    print(f"[Event Handler] 📹 배경 매핑 결과:")
    print(f"[Event Handler]   - Scene: {vp_state.current_scene_id}")
    print(f"[Event Handler]   - Action: {event.behavior}")
    print(f"[Event Handler]   - Video: {video_filename}")

    if video_filename:
        print(f"[Event Handler] ✅ 비디오 파일 찾음: {video_filename}")
    else:
        print(f"[Event Handler] ⚠️ 비디오 파일을 찾지 못함!")

    # 클라이언트에 브로드캐스트
    message = {
        "type": "action_change",
        "scene_id": vp_state.current_scene_id,
        "action": event.behavior,
        "new_background": video_filename,
        "sensor_event": event.dict()
    }
    print(f"[Event Handler] 📡 브로드캐스트 메시지 전송:")
    print(f"[Event Handler]   {message}")
    print(f"[Event Handler] 🔔 클라이언트 수: {len(vp_state.websocket_clients)}")
    await broadcast_to_clients(message)
    print(f"[Event Handler] ========================================\n")


# ============= WebSocket 엔드포인트 =============

@app.websocket("/vp/sensor-events")
async def websocket_sensor_events(websocket: WebSocket):
    """센서 이벤트 WebSocket (센서 → 서버)"""
    await websocket.accept()
    print(f"[WebSocket/Sensor] 센서 연결됨")

    try:
        while True:
            # 센서로부터 이벤트 수신
            data = await websocket.receive_json()
            print(f"[WebSocket/Sensor] 센서 이벤트 수신: {data}")

            # SensorEvent로 변환
            event = SensorEvent(**data)
            print(f"[WebSocket/Sensor] 이벤트 파싱 완료: behavior={event.behavior}, sensor_id={event.sensor_id}")

            # 이벤트 처리 및 프론트엔드에 브로드캐스트
            await handle_sensor_event(event)
            print(f"[WebSocket/Sensor] 이벤트 처리 완료")

    except WebSocketDisconnect:
        print(f"[WebSocket/Sensor] 센서 연결 해제됨")


@app.websocket("/vp/player-events")
async def websocket_player_events(websocket: WebSocket):
    """플레이어 이벤트 WebSocket (서버 → 프론트엔드)"""
    await websocket.accept()
    vp_state.websocket_clients.append(websocket)
    print(f"[WebSocket/Player] 프론트엔드 연결됨. 총 {len(vp_state.websocket_clients)}개 연결")

    try:
        # 프론트엔드는 서버로부터 메시지만 받음
        # 연결 유지를 위해 대기
        while True:
            # 연결 상태 확인용 (클라이언트로부터의 핑 메시지 등)
            try:
                await websocket.receive_text()
            except:
                break
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in vp_state.websocket_clients:
            vp_state.websocket_clients.remove(websocket)
        print(f"[WebSocket/Player] 프론트엔드 연결 해제됨. 남은 연결: {len(vp_state.websocket_clients)}개")


# ============= 파일 스트리밍 엔드포인트 =============

@app.get("/vp/backgrounds/{filename}")
async def stream_background_video(filename: str):
    """배경 영상 스트리밍"""
    print(f"[VP API] 🎬 Streaming video request: {filename}")

    if not vp_state.work_dir or not vp_state.entity_set_name:
        print(f"[VP API] ❌ No project loaded")
        raise HTTPException(status_code=404, detail="No project loaded")

    # 표준 video/output/ 경로 사용
    video_path = os.path.join(
        vp_state.work_dir, vp_state.entity_set_name,
        'video', 'output', filename
    )

    print(f"[VP API] 📂 Looking for video at: {video_path}")
    print(f"[VP API] Work dir: {vp_state.work_dir}")
    print(f"[VP API] Entity set: {vp_state.entity_set_name}")

    if not os.path.exists(video_path):
        print(f"[VP API] ❌ Video not found at: {video_path}")

        # 디렉토리 내용 확인
        video_dir = os.path.dirname(video_path)
        if os.path.exists(video_dir):
            files = os.listdir(video_dir)
            print(f"[VP API] 📁 Files in {video_dir}:")
            for f in files[:10]:  # 최대 10개만 출력
                print(f"[VP API]   - {f}")
        else:
            print(f"[VP API] ❌ Directory does not exist: {video_dir}")

        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")

    print(f"[VP API] ✅ Video found, serving: {video_path}")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/vp/preview")
async def get_preview_list(work_dir: str, entity_set_name: str):
    """모든 배경 영상 미리보기 목록"""
    print(f"[VP API] 📋 Preview list request")
    print(f"[VP API] Work dir: {work_dir}")
    print(f"[VP API] Entity set: {entity_set_name}")

    try:
        # 표준 video/output/ 경로 사용
        video_output_path = os.path.join(
            work_dir, entity_set_name,
            'video', 'output'
        )

        print(f"[VP API] 📂 Looking for videos at: {video_output_path}")

        if not os.path.exists(video_output_path):
            print(f"[VP API] ⚠️ Video output directory not found")
            return {"previews": []}

        # cut.txt와 action_mapping.json 로드
        cut_file = os.path.join(work_dir, entity_set_name, 'story', 'cut.txt')
        mapping_file = os.path.join(
            work_dir, entity_set_name,
            'virtual-production', 'mappings', 'action_mapping.json'
        )

        print(f"[VP API] 📄 Cut file: {cut_file}")
        print(f"[VP API] 📄 Mapping file: {mapping_file}")

        # 매핑 로드
        action_by_cut = {}
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
                print(f"[VP API] ✅ Mapping loaded")

                # 씬별 컷 ID → action 추출
                for scene_key, scene_cuts in mapping.items():
                    if scene_key == 'sensor_mapping':
                        continue
                    for cut_id, cut_info in scene_cuts.items():
                        if isinstance(cut_info, dict) and 'action' in cut_info:
                            key = f"{scene_key}_{cut_id}"
                            action_by_cut[key] = cut_info['action']
                            print(f"[VP API]   Scene {scene_key}, Cut {cut_id}: {cut_info['action']}")
        else:
            print(f"[VP API] ⚠️ Mapping file not found")

        # 비디오 파일 목록
        previews = []
        video_files = [f for f in os.listdir(video_output_path) if f.endswith('_video.mp4')]
        print(f"[VP API] 📹 Found {len(video_files)} video files")

        for filename in video_files:
            # 파일명 파싱: S####-C####_video.mp4
            try:
                base_name = filename.replace('_video.mp4', '')
                parts = base_name.split('-')
                if len(parts) == 2:
                    scene_id = int(parts[0][1:])  # S#### -> ####
                    cut_id = int(parts[1][1:])    # C#### -> ####

                    # 매핑에서 action 찾기
                    key = f"{scene_id}_{cut_id}"
                    action = action_by_cut.get(key, 'unknown')

                    preview_item = PreviewItem(
                        scene_id=scene_id,
                        action=action,
                        video_filename=filename,
                        video_url=f"/vp/backgrounds/{filename}"
                    )
                    previews.append(preview_item)
                    print(f"[VP API]   ✅ {filename}: Scene {scene_id}, Action {action}")

            except Exception as e:
                print(f"[VP API] ⚠️ Failed to parse filename: {filename}, error: {e}")
                continue

        print(f"[VP API] ✅ Returning {len(previews)} preview items")
        return {"previews": previews}

    except Exception as e:
        print(f"[VP API] ❌ Error in preview list: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============= 센서 정보 엔드포인트 =============

@app.get("/sensor/available-actions")
async def get_available_sensor_actions():
    """센서가 감지할 수 있는 행동 목록"""
    analyzer = VPSceneAnalyzer()
    return {"actions": analyzer.get_sensor_actions()}


# ============= 헬스 체크 =============

@app.get("/")
async def root():
    return {"message": "Virtual Production API Server", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ============= 센서 HTTP 백업 엔드포인트 =============

@app.get("/api/status")
async def api_status():
    """센서용 HTTP 백업 엔드포인트 - 서버 상태"""
    return {
        "status": "online",
        "websocket_available": True,
        "websocket_endpoint": "/vp/sensor-events",
        "connected_clients": len(vp_state.websocket_clients),
        "mapping_loaded": vp_state.mapping is not None,
        "current_scene": vp_state.current_scene_id,
        "current_action": vp_state.current_action
    }


@app.post("/api/heartbeat")
async def api_heartbeat(data: dict):
    """센서용 HTTP 백업 엔드포인트 - 하트비트"""
    sensor_id = data.get("sensor_id", "unknown")
    print(f"[API/Heartbeat] Heartbeat received from {sensor_id}")
    return {
        "status": "ok",
        "message": "Heartbeat received",
        "recommendation": "Use WebSocket /vp/sensor-events for real-time events"
    }


@app.post("/api/behavior")
async def api_behavior(data: dict):
    """센서용 HTTP 백업 엔드포인트 - 행동 이벤트 (WebSocket 대신 사용 가능)"""
    try:
        # SensorEvent로 변환
        event = SensorEvent(
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            sensor_id=data.get("sensor_id", "unknown"),
            behavior=data.get("behavior", "stop"),
            metadata=data.get("metadata", {})
        )

        print(f"[API/Behavior] Behavior event received via HTTP: {event.behavior} from {event.sensor_id}")

        # 이벤트 처리 (WebSocket과 동일한 핸들러 사용)
        await handle_sensor_event(event)

        return {
            "status": "ok",
            "message": "Behavior event processed",
            "event": event.dict()
        }
    except Exception as e:
        print(f"[API/Behavior] Error processing behavior event: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
