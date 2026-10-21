from llms.client import chat as unified_chat


def chat(*, model, **kwargs):
    return unified_chat(model=f"qwen/{model}", **kwargs)
