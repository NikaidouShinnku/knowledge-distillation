
import os
import pathlib
import re
import tomllib
from functools import lru_cache

prompt_directory = pathlib.Path(__file__).parent.absolute()
LANGUAGES = ("zh-CN", "en-US")


@lru_cache(maxsize=2)
def _load_language(language):
    templates = {}
    fragments = {}
    for category in ("agents", "cards", "shared"):
        with (prompt_directory / f"{category}.{language}.toml").open("rb") as source:
            bundle = tomllib.load(source)
        templates.update(bundle.get("templates", {}))
        fragments.update(bundle.get("fragments", {}))
    return {
        name: re.sub(r"\[\[include:([a-z0-9_]+)\]\]", lambda match: fragments[match[1]], text)
        for name, text in templates.items()
    }


def read_prompt(name: str, language: str | None = None):
    for suffix in LANGUAGES:
        if name.endswith(f".{suffix}"):
            name, explicit_language = name[: -len(suffix) - 1], suffix
            if language is not None and language != explicit_language:
                raise ValueError("Conflicting prompt languages")
            language = explicit_language
            break
    language = language or os.environ.get("PROMPT_LANGUAGE", "en-US")
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported prompt language: {language}")
    try:
        return _load_language(language)[name]
    except KeyError as error:
        raise FileNotFoundError(f"Prompt {name}.{language} does not exist") from error
