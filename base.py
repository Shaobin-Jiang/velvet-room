from openai import AsyncOpenAI
from typing import Callable

from typings import ModelConfig


class Base:
    def __init__(self, model_config: ModelConfig) -> None:
        """Initialize shared model configuration and in-memory request logs."""
        self._model_config = model_config
        self._logs: dict[str, list[str]] = {}

    async def _get_response(self, prompt: str, validate: Callable[[str], bool]) -> str:
        """
        Gets response from LLM and repeats until a valid response is given.

        Uses label to store the prompt / response in a dictionary for debugging.
        """
        if prompt not in self._logs:
            self._logs[prompt] = []
        print(f">>> prompt: \033[31m{prompt}\033[0m")
        attempt = 1
        response = await self._call_llm(prompt)
        print(f">>> Attempt 1: \033[36m{response}\033[0m")
        while not validate(response):
            response = await self._call_llm(prompt)
            attempt += 1
            print(f">>> Attempt {attempt}: \033[36m{response}\033[0m")
        print("--------------------")
        return response

    async def _call_llm(self, prompt: str) -> str:
        """Sends a request to the LLM using `prompt` and returns the LLM response."""
        client = AsyncOpenAI(
            base_url=self._model_config["base_url"],
            api_key=self._model_config["api_key"],
        )

        success = False
        response = ""
        while not success:
            success = True
            try:
                completion = await client.chat.completions.create(
                    model=self._model_config["model"],
                    messages=[{"role": "user", "content": prompt}],
                )
                try:
                    response = completion.choices[0].message.content or ""
                except:
                    success = False
            except:
                success = False
        self._logs[prompt].append(response)
        return response
