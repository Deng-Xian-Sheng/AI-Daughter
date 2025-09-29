from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
UPLOADS_DIR = IMAGES_DIR / "uploads"
GENERATED_DIR = IMAGES_DIR / "generated"
REFS_IMG_DIR = IMAGES_DIR / "refs"
REFS_META_DIR = DATA_DIR / "refs"
IMAGE_META_DIR = DATA_DIR / "image_meta"

class Providers(BaseModel):
    llm: str
    vlm: str
    text2img: str
    img2img: str

class ModelIDs(BaseModel):
    modelscope: str | None = None
    bailian: str | None = None

class ModelMap(BaseModel):
    llm: ModelIDs
    vlm: ModelIDs
    text2img: ModelIDs
    img2img: ModelIDs

class ImageTransport(BaseModel):
    modelscope: str  # "data_uri" | "public_url"
    public_base_url: str
    static_path_prefix: str  # e.g. "/static/images"

class Limits(BaseModel):
    images_per_session_per_10min: int = 3

class PromptCfg(BaseModel):
    prompt_extend: bool = False

class Safety(BaseModel):
    strict_family_friendly: bool = True

class Settings(BaseModel):
    providers: Providers
    model_ids: ModelMap
    image_transport: ImageTransport
    limits: Limits = Limits()
    prompt: PromptCfg = PromptCfg()
    safety: Safety = Safety()
    # 修复 "model_*" 命名冲突告警
    model_config = ConfigDict(protected_namespaces=())

SETTINGS_PATH = ROOT / "settings.json"

def load_settings() -> Settings:
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return Settings.model_validate(data)

def save_settings(cfg: Settings) -> None:
    SETTINGS_PATH.write_text(cfg.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")