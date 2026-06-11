import json
import linecache
import random
import sqlite3

from textwrap import dedent
from typing import Any

from base import Base
from typings import ModelConfig, ConstructValuePrettyName


class Persona(Base):
    """Generates a single persona profile."""

    def __init__(
        self, description: str, dimensions: dict[str, str], model_config: ModelConfig
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
    def map(self) -> dict[str, str]:
        return self._dimensions | self._constructs_json

    async def _create(self) -> None:
        """Execute the full persona-building pipeline in sequence."""
        self._create_base_profile()
        await self._assign_constructs()
        await self._sample_from_personahub()
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
        # TODO: allow users to customize the source
        conn = sqlite3.connect("persona.sqlite")
        conn.row_factory = sqlite3.Row

        parameters = [
            self._constructs_json["occupation"],
            self._constructs_json["region"],
        ]
        first_line = "SELECT p.persona"
        for construct in ConstructValuePrettyName.keys():
            construct = construct.replace(" ", "_")
            first_line += f", p.{construct}"
        command = (
            f"{first_line}\n"
            + "FROM personas p\n"
            + "LEFT JOIN persona_regions r ON r.persona_id = p.id\n"
            + "WHERE p.type = ?\n"
            + "  AND (r.persona_id IS NULL OR r.region = ?)\n"
        )

        for construct, value in self._constructs_json.items():
            if construct in ("occupation", "region") or value == "both":
                continue
            candidates = ConstructValuePrettyName[construct]
            construct =  construct.replace(" ", "_")
            v = candidates[1] if candidates[0] == value else candidates[0]
            command += f"  AND p.{construct} != ?\n"
            parameters.append(v)

        command += "ORDER BY random()"
        command += f"LIMIT 20"
        rows = conn.execute(command, parameters).fetchall()

        personahub_descriptions = {row["persona"]: row for row in rows}

        count = len(rows)
        prompt = dedent(
            f"""{self._base_profile}

            Here below are some potential descriptions about this person:

            - {"\n- ".join(personahub_descriptions.keys())}

            Which of these {count} descriptions most likely describes this person?
            Respond **ONLY** with the most likely description.
            When responding, leave the origin description AS IS. No modification."""
        )

        result = (
            await self._get_response(
                prompt, lambda x: x.strip() in personahub_descriptions
            )
        ).strip()
        self._base_profile += f"\n\n- {result}"

        entry = dict(personahub_descriptions[result])
        for construct in ConstructValuePrettyName.keys():
            self._constructs_json[construct] = entry.get(construct.replace(" ", "_")) or "both"

    async def _assign_constructs(self) -> None:
        """Assign values to the 16 constructs based on base profile."""
        constructs_list = ""
        example: dict[str, Any] = {"occupation": 0, "region": "CN"}
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

            Additionally, include these two piececs of information:

            - occupation: whether the profile describes the occupation of this person; 1 for yes and 0 for no
            - region: exactly one ISO 3166-1 alpha-2 country code you think this person might belong to or an empty string if you cannot be 100% certain
            
            Respond ONLY with a JSON object that looks like this:

            {json.dumps(example, indent=2)}

            Just the JSON. No markdown!!!"""
        )

        def rule(response: str) -> bool:
            is_valid = True
            try:
                obj: dict[str, str] = json.loads(response)
                if len(obj.keys()) != len(ConstructValuePrettyName.keys()) + 2:
                    is_valid = False
                for construct in ConstructValuePrettyName.keys():
                    candidates = [*ConstructValuePrettyName[construct], "both"]
                    value = obj.get(construct)
                    if (
                        construct not in ConstructValuePrettyName
                        or value not in candidates
                    ):
                        is_valid = False
                        break

                if obj.get("occupation") not in [0, 1]:
                    is_valid = False

                if "region" not in obj:
                    is_valid = False
            except:
                is_valid = False
            return is_valid

        response = json.loads(await self._get_response(prompt, rule))
        response["occupation"] = (
            "occupation" if response["occupation"] == 1 else "hobby"
        )
        self._constructs_json = response

    async def _create_construct_descriptions(self) -> None:
        """Generate one-sentence construct descriptions from assigned values."""
        for construct, value in self._constructs_json.items():
            if value == "both":
                candidates = ConstructValuePrettyName[construct]
                value = candidates[random.randint(0, len(candidates) - 1)]
            self._constructs_json[construct] = value

        desc = ""
        obj = {}
        for construct, value in self._constructs_json.items():
            if construct in ("occupation", "region"):
                continue
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
                obj: dict[str, str] = json.loads(response)
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

            Help me polish this and create a more natural persona profile in English.

            You MUST NOT add information (such as name) to the profile. AVOID omitting any information, including the adjectives.
            The only exception is when the information contains **range values**, such as "0-3 years of teaching experience".
            In this case, you should change the range value to a precise value, such as "2 years of teaching experience".

            Instead of "This person...", use "You ..." to describe the person.
            Only rearrange and polish the language, but no fancy expressions.
            Your response should ONLY contain the polished persona profile. """
        )

        profile = await self._get_response(prompt, lambda x: len(x) > 0.5 * length)
        self.profile = profile.replace("\n", "")
