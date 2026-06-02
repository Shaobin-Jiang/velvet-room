import json

import asyncio
import random
from textwrap import dedent
from typing import Dict, List

from base import Base
from persona import Persona
from typings import ModelConfig, ConstructValuePrettyName


class Scaffold(Base):
    """Generates a number of persona profiles as requested."""

    def __init__(
        self, description: str, number: int, model_config: ModelConfig
    ) -> None:
        """
        Initializes the `Scaffold` class with these parameters:

        - description: describes the group of agents whose profiles you want to create
        - number: the number of persona profiles you want to create
        - model_config: LLM configuration

        For example:

        ```python
        Scaffold(
            "high school teachers",
            100,
            {
                "base_url": "http://api.com/v1",
                "api_key": "sk-******",
                "model": "gemma4"
            }
        )
        ```
        """
        super().__init__(model_config)
        self._number = number
        self._description = description

    def create_sync(self) -> List[str]:
        """Run profile generation in a synchronous context."""
        return asyncio.run(self.create())

    async def create(self) -> List[str]:
        """Generate persona profiles."""
        dimensions = await self._analyze_description()
        combinations = {}
        for dimension, values in dimensions.items():
            combinations[dimension] = []
            quotient = self._number // len(values)
            remainder = self._number % len(values)
            for index, value in enumerate(values):
                count = quotient if index >= remainder else quotient + 1
                combinations[dimension].extend([value] * count)
            random.shuffle(combinations[dimension])

        profiles: List[str] = []
        for i in range(0, self._number):
            dimension_map = {}
            for dimension, values in combinations.items():
                dimension_map[dimension] = values[i]
            persona = Persona(self._description, dimension_map, self._model_config)
            await persona._create()
            profiles.append(persona.profile)

        return profiles

    async def _analyze_description(self) -> Dict[str, List[str]]:
        """
        Analyzes the provided profile description and returns the dimensions with which
        the desired group can be depicted.
        """
        exclude_dimensions = ",".join(ConstructValuePrettyName.keys())
        prompt = dedent(
            f"""From which aspects would you describe **{self._description}**?
            Provide the name of the dimensions and the exact values.

            For example, to describe "middle school students", you could response like this:

            {{
                "Grade Level": ["7th", "8th", "9th"],
                "School Type": ["Public", "Private", "Charter", "Magnet", "Home School"],
                "Extracurricular Involvement": ["Sports", "Arts", "Academic Clubs", "Student Government", "None"],
                "Primary Learning Modality": ["In-Person", "Online", "Hybrid"],
                "Geographic Setting of School": ["Urban", "Suburban", "Rural"]
            }}

            Rules you must follow:

            - provide at least 5 dimensions
            - these dimensions should be orthogonal with each other
            - these dimensions better be factual instead of mental attributes
            - these dimensions must not be one of {exclude_dimensions}
            - your response must be a JSON object that looks like this:
            {{"D1": ["v1", "v2", ...], "D2": ["v3", "v4", ...]}}

            Just the JSON. No markdown!!!"""
        )

        def rule(response: str) -> bool:
            is_valid = True
            try:
                obj: Dict[str, List[str]] = json.loads(response)
                if len(obj.keys()) < 5:
                    is_valid = False
                for values in obj.values():
                    if not isinstance(values, list):
                        is_valid = False
                        break
            except:
                is_valid = False
            return is_valid

        response = await self._get_response(prompt, rule)
        return json.loads(response)
