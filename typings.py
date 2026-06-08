from __future__ import annotations
from typing import Dict, TypedDict

ConstructValuePrettyName = {
    "age": ["young", "old"],
    "gender": ["male", "female"],
    "ses": ["low", "high"],
    "marital status": ["unmarried", "married"],
    "education": ["low", "high"],
    "cultural context": ["collectivistic", "individualistic"],
    "ideology": ["liberal", "conservative"],
    "neuroticism": ["low", "high"],
    "conscientiousness": ["low", "high"],
    "agreeableness": ["low", "high"],
    "openness": ["low", "high"],
    "extraversion": ["low", "high"],
    "subjective confidence": ["low", "high"],
    "attachment": ["insecure", "secure"],
    "optimism": ["low", "high"],
    "loneliness": ["low", "high"],
}


class ModelConfig(TypedDict):
    base_url: str
    api_key: str
    model: str


class Profile(TypedDict):
    map: Dict[str, str]
    profile: str
