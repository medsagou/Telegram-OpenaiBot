

from openai import AsyncOpenAI
from typing import Any
def getOpenAiClient(API_KEY: str):
    return AsyncOpenAI(api_key=API_KEY)

async def chat(MSGS: list, MaxToken: int=50, outputs: int=3, client: Any=None) -> str:
    # We use the Chat Completion endpoint for chat like inputs
    if not client:
        return "ERROR: API client not provided"
    try:
        response = await client.chat.completions.create(
        # gpt-4, gpt-4-0314, gpt-4-32k, gpt-4-32k-0314,
        # gpt-3.5-turbo, gpt-3.5-turbo-0301
        model="gpt-3.5-turbo",
        # MSGS=[
        #     {"role": "system", "content": "<message generated by system>"},
        #     {"role": "user", "content": "<message generated by user>"},
        #     {"role": "assistant", "content": "<message generated by assistant>"}
        # ]
        messages=MSGS,
        # max_tokens generated by the AI model
        # maximu value can be 4096 tokens for "gpt-3.5-turbo"
        max_tokens = MaxToken,
        # number of output variations to be generated by AI model
        n = outputs,
        )
    except Exception as e:
        return f"Error: {str(e)}"
    print(response.choices[0].message)
    return response.choices[0].message.content if response and response.choices else "No response from AI model"