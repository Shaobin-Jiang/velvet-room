import json
import linecache
import random

from textwrap import dedent
from typing import Dict

from base import Base
from typings import ModelConfig, ConstructValuePrettyName


class Persona(Base):
    """Generates a single persona profile."""

    def __init__(
        self, description: str, dimensions: Dict[str, str], model_config: ModelConfig
    ) -> None:
        """
        Initializes the `Persona` class with these parameters:

        - description: describes the group to which the agent belongs
        - dimensions: describes various aspects of the agent
        - model_config: LLM configuration
        """
        super().__init__(model_config)
        self._description = description
        self._dimensions = dimensions

        self._base_profile = ""
        self._constructs_json = {}
        self._constructs_description = ""

        self.profile = ""

    @property
    def map(self) -> Dict[str, str]:
        return self._dimensions | self._constructs_json

    async def _create(self) -> None:
        """Execute the full persona-building pipeline in sequence."""
        self._create_base_profile()
        await self._sample_from_personahub()
        await self._assign_constructs()
        await self._create_construct_descriptions()
        await self._polish()

    def _create_base_profile(self) -> None:
        """
        Creates the profile base by concatenating the persona description and various
        dimensions.
        """
        information = ""
        for dimension, value in self._dimensions.items():
            information += f"- {dimension}: {value}\n"
        information = information[0:-1]

        self._base_profile = dedent(
            f"""This person belongs to a group described as **{self._description}**.
            Here is some information about this person:

            {information}"""
        )

    async def _sample_from_personahub(self) -> None:
        """
        Samples one description from personhub. 20 candidates are provided and one
        most likely item is picked based on and then merged into base profile.
        """
        count = 20
        lines = random.sample(range(0, 200000), count)
        personahub_descriptions = []
        for lineno in lines:
            # TODO: allow users to customize the source
            line = linecache.getline("./persona.txt", lineno).strip()
            personahub_descriptions.append(line)

        prompt = dedent(
            f"""{self._base_profile}

            Here below are some potential descriptions about this person:

            - {"\n- ".join(personahub_descriptions)}

            Which of these {count} descriptions most likely describes this person?
            Respond **ONLY** with the most likely description."""
        )

        result = (
            await self._get_response(
                prompt, lambda x: x.strip() in personahub_descriptions
            )
        ).strip()
        self._base_profile += f"\n\n- {result}"

    async def _assign_constructs(self) -> None:
        """Assign values to the 16 constructs based on base profile."""
        constructs_list = ""
        example = {}
        for construct, values in ConstructValuePrettyName.items():
            constructs_list += f'- {construct}: {" / ".join(values)}\n'
            candidates = [*values, "both"]
            example[construct] = candidates[random.randint(0, len(candidates) - 1)]
        constructs_list = constructs_list[0:-1]
        prompt = dedent(
            f"""{self._base_profile}

            Now, for each of these constructs, which value might describe this person?

            {constructs_list}

            For each of these constructs, you should select a specific value ONLY IF you are certain that the other value cannot possibly describe this person.
            If you feel unsure, i.e., both values might describe this person, the value for that construct should be "both".
            
            Respond ONLY with a JSON object that looks like this:

            {json.dumps(example, indent=2)}

            Just the JSON. No markdown!!!"""
        )

        def rule(response: str) -> bool:
            is_valid = True
            try:
                obj: Dict[str, str] = json.loads(response)
                if len(obj.keys()) != len(ConstructValuePrettyName.keys()):
                    is_valid = False
                for construct, value in obj.items():
                    candidates = [*ConstructValuePrettyName[construct], "both"]
                    if (
                        construct not in ConstructValuePrettyName
                        or value not in candidates
                    ):
                        is_valid = False
                        break
            except:
                is_valid = False
            return is_valid

        response = json.loads(await self._get_response(prompt, rule))
        constructs_json = {}
        for construct, value in response.items():
            if value == "both":
                candidates = ConstructValuePrettyName[construct]
                value = candidates[random.randint(0, len(candidates) - 1)]
            constructs_json[construct] = value

        self._constructs_json = constructs_json

    async def _create_construct_descriptions(self) -> None:
        """Generate one-sentence construct descriptions from assigned values."""
        desc = ""
        obj = {}
        for construct, value in self._constructs_json.items():
            desc += f"\n- {construct}: {value}"
            obj[construct] = "This person is..."
            if construct == "attachment":
                desc += " (this description should preferrably be related to intimate relationship or friendship)"
            if construct == "cultural context":
                desc += " (this description should be about what country this person was born and grew up in)"
            if construct == "age":
                desc += (
                    " (this description should be about the exact age of this person)"
                )
        prompt = dedent(
            f"""{self._base_profile}

            Here is also a list of constructs that describe this person, and I want you to give me a one-sentence description for each of them below:"
            {desc}

            Each sentence should begin with "This person..." and end with a period.
            It SHOULD describe what this person did or the attitude it holds and reflect the corresponding construct.
            It should NOT be something like "You have xxx level construct". 

            Your descriptions MUST NOT conflict with the information provided about this person. 
            For example, it is not right for an 18-year-old to have finished PhD even if I ask you to create a description reflecting high education. 

            Avoid over complicated sentences / vocabulary. Use casual language. 

            Return a JSON object that looks like this:

            {json.dumps(obj, indent=2)}

            Just the JSON. No markdown!!!"""
        )

        def rule(response: str) -> bool:
            is_valid = True
            try:
                obj: Dict[str, str] = json.loads(response)
                if len(obj.keys()) != len(ConstructValuePrettyName.keys()):
                    is_valid = False
                for construct, value in obj.items():
                    if (
                        construct not in self._constructs_json
                        or not value.startswith("This person")
                        or not value.endswith(".")
                    ):
                        is_valid = False
                        break
            except:
                is_valid = False
            return is_valid

        response = json.loads(await self._get_response(prompt, rule))
        self._constructs_description = " ".join(response.values())

    async def _polish(self) -> None:
        """Refine the assembled profile text into a natural final narrative."""
        length = len(self._base_profile) + len(self._constructs_description)
        prompt = dedent(
            f"""Here is a persona profile:

            {self._base_profile}
            {self._constructs_description}

            Help me polish this and create a more natural persona profile.

            You MUST NOT add information (such as name) to the profile. AVOID omitting any information, including the adjectives.
            Instead of "This person...", use "You ..." to describe the person.
            Only rearrange and polish the language, but no fancy expressions.
            Your response should ONLY contain the polished persona profile. """
        )

        self.profile = await self._get_response(prompt, lambda x: len(x) > 0.5 * length)
