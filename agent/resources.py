import os


def example_limit():
    value = int(os.getenv("LLM_EXAMPLE_LIMIT", "1"))
    if not 0 <= value <= 5:
        raise ValueError("LLM_EXAMPLE_LIMIT must be between 0 and 5")
    return value
