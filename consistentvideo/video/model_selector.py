from .base import ImageGeneratorAIBase, VideoGeneratorAIBase
import os
from openai import OpenAI
import base64
import requests
from PIL import Image
from io import BytesIO
from runwayml import RunwayML
import time
import re
import logging
from google import genai
from mimetypes import guess_type
import tempfile
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

class CutImageGeneratorModelSelector:
    def __init__(self):
        pass

    def call_CutImageGenerator_ai(self, ai_model : str, prompt_text : str = None, prompt_images : list = None):
        if ai_model == "gemini":
            return ImageGeneratorModelGemini(prompt_text = prompt_text, prompt_images = prompt_images)
        elif ai_model == "gpt-image-1":
            return ImageGeneratorModelGPT_image_1(prompt_text = prompt_text, prompt_images = prompt_images)
        elif ai_model == "dalle3":
            return ImageGeneratorModelDalle3(prompt_text = prompt_text, prompt_images = prompt_images)
        else:
            return None
        

class ImageGeneratorModelGemini(ImageGeneratorAIBase):
    '''
    Need to fill this blank with Gemini version model
    '''
    def __init__(self, prompt_text : str = None, prompt_images : list = None):
        pass

    def execute(self):
        pass
    

class ImageGeneratorModelDalle3(ImageGeneratorAIBase):
    def __init__(self, prompt_text : str = None, prompt_images : list = None):
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        self.ai_model = OpenAI(api_key=api_key)
        self.prompt_text = prompt_text
        self.prompt_images = prompt_images

    def execute(self):
        # 입력 이미지가 없어도 DALL·E 3는 텍스트 생성이 가능. 이미지 경로가 주어졌다면 존재 여부만 확인
        if self.prompt_images:
            for prompt_image_path in self.prompt_images:
                if not os.path.exists(prompt_image_path):
                    raise FileNotFoundError(f"참조 이미지 파일을 찾을 수 없습니다: {prompt_image_path}")

        # ---------------dalle3 (can also dalle2)--------------

        result = self.ai_model.images.generate(
            model="dall-e-3",
            prompt=self.prompt_text,
            size="1792x1024"
        )
        image_url = result.data[0].url
        image_bytes = requests.get(image_url).content
        cut_image = Image.open(BytesIO(image_bytes))

        # -----------------------------------------------------

        return cut_image
    

class ImageGeneratorModelGPT_image_1(ImageGeneratorAIBase):
    def __init__(self, prompt_text : str = None, prompt_images : list = None, *, quality: str = "low", size: str = "1536x1024"):
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        self.ai_model = OpenAI(api_key=api_key)
        self.prompt_text = prompt_text
        self.prompt_images = prompt_images
        self.quality = quality
        self.size = size

    def execute(self):
        # ---------------------gpt-image-1---------------------
        image_file_handles = []
        try:
            if self.prompt_images:
                for img_path in self.prompt_images:
                    if not os.path.exists(img_path):
                        logger.warning(f"참조 이미지가 존재하지 않아 스킵합니다: {img_path}")
                        continue
                    image_file_handles.append(open(img_path, "rb"))

            if image_file_handles:
                # 여러 장의 참조 이미지를 모두 전달
                result = self.ai_model.images.edit(
                    model="gpt-image-1",
                    image=image_file_handles,
                    prompt=self.prompt_text,
                    quality=self.quality,  # high/medium/low
                    size=self.size  # e.g., 1536x1024
                )
            else:
                result = self.ai_model.images.generate(
                    model="gpt-image-1",
                    prompt=self.prompt_text,
                    quality=self.quality,  # high/medium/low
                    size=self.size  # e.g., 1536x1024
                )
        finally:
            for f in image_file_handles:
                try:
                    f.close()
                except Exception:
                    pass

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        cut_image = Image.open(BytesIO(image_bytes))
        # -----------------------------------------------------

        return cut_image

# -------------------------------------------------------------------------------------------


class VideoGeneratorModelSelector:
    def __init__(self):
        pass

    def call_VideoGenerator_ai(self, ai_model : str, prompt_text : str = None, prompt_image : str = None):
        if ai_model == "runway":
            return VideoGeneratorModelRunway(prompt_text = prompt_text, prompt_image = prompt_image)
        elif ai_model.startswith("veo-3.0"):
            return VideoGeneratorModelVeo3(prompt_text = prompt_text, prompt_image = prompt_image, ai_model = ai_model)
        else:
            return None


class VideoGeneratorModelRunway(VideoGeneratorAIBase):
    def __init__(self, prompt_text : str = None, prompt_image : str = None):
        super().__init__()
        api_key = os.getenv("RUNWAY_API_KEY")
        self.ai_model = RunwayML(api_key=api_key)
        self.prompt_text = prompt_text
        self.prompt_image = prompt_image

    def execute(self):
        # 파일명에서 S번호와 C번호 추출
        match = re.match(r'S(\d+)-C(\d+)', os.path.basename(self.prompt_image))
        if not match:
            raise ValueError("prompt_image 파일명이 'S####-C####' 형식을 따르지 않습니다.")
        scene_num = int(match.group(1))  # S번호
        cut_num = int(match.group(2))    # C번호

        logger.info(f"scene_num={scene_num}, cut_num={cut_num}")
        cut = self.cut_list[scene_num-1][cut_num-1]
        cut_id = cut.get('cut_id')

        with open(self.prompt_image, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read()).decode("utf-8")

        logger.info(f"Runway 작업 생성: scene={scene_num}, cut={cut_num}")
        task = self.ai_model.image_to_video.create(
            model='gen4_turbo',
            prompt_image=f"data:image/png;base64,{encoded_image}",
            prompt_text=self.prompt_text,
            ratio='1280:720',
            duration=5,
        )

        task_id = task.id

        time.sleep(10)
        task = self.ai_model.tasks.retrieve(task_id)
        while task.status not in ['SUCCEEDED', 'FAILED']:
            time.sleep(10)
            task = self.ai_model.tasks.retrieve(task_id)
            logger.debug(f"Runway 작업 상태: {task.status}")

        if task.status == 'FAILED':
            logger.error(f"[cut_id={cut_id}] 비디오 생성 실패: {task.status}")
            return None
        output_urls = task.output
        
        if output_urls == None or isinstance(output_urls, list) == False:
            logger.error(f"[cut_id={cut_id}] 출력 URL이 없습니다")
            return None
        video_url = output_urls[0]
        response = requests.get(video_url)
        
        if response.status_code != 200:
            logger.error(f"[cut_id={cut_id}] 응답 코드 오류: {response.status_code}")
            return None            

        return response.content # Binary type video data


class VideoGeneratorModelVeo3(VideoGeneratorAIBase):
    def __init__(self, prompt_text : str = None, prompt_image : str = None, ai_model : str = "veo-3.0-fast-generate-preview"):
        super().__init__()
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.prompt_text = prompt_text
        self.prompt_image = prompt_image
        self.ai_model = ai_model

    def execute(self):
        # 파일명에서 S번호와 C번호 추출
        match = re.match(r'S(\d+)-C(\d+)', os.path.basename(self.prompt_image))
        if not match:
            raise ValueError("prompt_image 파일명이 'S####-C####' 형식을 따르지 않습니다.")
        scene_num = int(match.group(1))  # S번호
        cut_num = int(match.group(2))    # C번호

        logger.info(f"scene_num={scene_num}, cut_num={cut_num}")
        cut = self.cut_list[scene_num-1][cut_num-1]
        cut_id = cut.get('cut_id')

        # 로컬 이미지 → bytes + mimeType 구성
        with open(self.prompt_image, "rb") as img_file:
            image_bytes = img_file.read()
        mime_type = guess_type(self.prompt_image)[0] or "image/png"

        logger.info(f"Veo 작업 생성: scene={scene_num}, cut={cut_num}")

        # Python SDK 전용 Image 타입 구성 (문서: Image object 필요)
        try:
            # 1차: google.genai.types.Image 사용
            image_obj = genai_types.Image(image_bytes=image_bytes, mime_type=mime_type)
        except Exception as e1:
            try:
                # 2차: genai.types.Image 시도
                image_obj = genai.types.Image(image_bytes=image_bytes, mime_type=mime_type)  # type: ignore[attr-defined]
            except Exception as e2:
                logger.error(f"[cut_id={cut_id}] Veo Image 객체 생성 실패: {e1} / {e2}")
                return None

        try:
            operation = self.client.models.generate_videos(
                model=self.ai_model,
                prompt=self.prompt_text,
                image=image_obj,
            )
        except Exception as e:
            logger.error(f"[cut_id={cut_id}] Veo 작업 생성 실패: {e}")
            return None

        # Poll the operation status until the video is ready.
        while not operation.done:
            logger.info("Waiting for video generation to complete...")
            time.sleep(10)
            operation = self.client.operations.get(operation)

        # Download the video.
        try:
            video = operation.response.generated_videos[0]
            self.client.files.download(file=video.video)
        except Exception as e:
            logger.error(f"[cut_id={cut_id}] Veo 파일 다운로드 실패: {e}")
            return None

        # 가능한 경우 bytes 추출, 아니면 임시파일로 저장 후 읽기
        output_bytes = None
        try:
            if hasattr(video.video, "video_bytes") and video.video.video_bytes:
                output_bytes = video.video.video_bytes
            elif hasattr(video.video, "bytes") and video.video.bytes:
                output_bytes = video.video.bytes
            elif hasattr(video.video, "data") and video.video.data:
                output_bytes = video.video.data
            elif hasattr(video.video, "save"):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                tmp_path = tmp.name
                try:
                    tmp.close()
                    video.video.save(tmp_path)
                    with open(tmp_path, "rb") as f:
                        output_bytes = f.read()
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"[cut_id={cut_id}] Veo 결과 처리 실패: {e}")
            return None

        if not output_bytes:
            logger.error(f"[cut_id={cut_id}] Veo 결과 바이트가 비어있습니다")
            return None

        return output_bytes