from llms.client import chat as unified_chat


def chat(*, model, **kwargs):
    return unified_chat(model=f"baidu/{model}", **kwargs)
