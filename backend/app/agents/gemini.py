from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

StructuredOutput = TypeVar("StructuredOutput", bound=BaseModel)


async def generate_structured(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    prompt: str,
    response_schema: type[StructuredOutput],
) -> StructuredOutput:
    """Call Gemini and validate the response against a Pydantic schema."""
    client = genai.Client(api_key=api_key)
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1,
            ),
        )
        if isinstance(response.parsed, response_schema):
            return response.parsed
        if not response.text:
            raise ValueError("Gemini returned no structured content")
        return response_schema.model_validate_json(response.text)
    finally:
        await client.aio.aclose()
