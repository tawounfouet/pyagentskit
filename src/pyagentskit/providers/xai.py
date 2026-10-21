"""xAI's documented Chat Completions-compatible API, with explicit identity."""

from .openai import OpenAIModel


class XAIModel(OpenAIModel):
    provider = "xai"
    endpoint = "https://api.x.ai/v1"
    key_variable = "XAI_API_KEY"
