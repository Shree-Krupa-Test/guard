# policies/hallucination_checker.py

from services.azure_openai import call_llm


async def validate_response(prompt: str, response: str) -> bool:

    validation_prompt = f"""
    Original Question:
    {prompt}

    AI Response:
    {response}

    Does the response logically follow from the question?
    Answer only YES or NO.
    """

    result, _ = await call_llm(validation_prompt)

    return "yes" in result.lower()