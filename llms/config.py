import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY"),
    "moonshot": ("https://api.moonshot.cn/v1", "MOONSHOT_API_KEY"),
    "baidu": ("https://qianfan.baidubce.com/v2", "BAIDU_API_KEY"),
    "ollama": ("http://127.0.0.1:11434/v1", "OLLAMA_API_KEY"),
    "compatible": ("", "LLM_API_KEY"),
}

RETIRED = {
    "llama3-70b-8192": "groq/openai/gpt-oss-120b",
    "llama3-8b-8192": "groq/openai/gpt-oss-20b",
    "llama3-tooluse": "groq/openai/gpt-oss-120b",
    "llama3-groq-70b-8192-tool-use-preview": "groq/openai/gpt-oss-120b",
    "deepseek-chat": "deepseek/deepseek-flash",
    "deepseek-coder": "deepseek/deepseek-flash",
    "moonshot-v1-128k": "moonshot/kimi-k3",
    "moonshot-v1-32k": "moonshot/kimi-k3",
}


class ConfigurationError(ValueError):
    pass


def load_environment():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def default_model():
    load_environment()
    return os.getenv("LLM_MODEL", "groq/openai/gpt-oss-120b")


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    base_url: str
    api_key: str = field(repr=False)
    timeout: float = 60
    attempts: int = 3

    @classmethod
    def resolve(cls, spec=None):
        load_environment()
        spec = spec or default_model()
        provider, separator, model = spec.partition("/")
        if not separator:
            if spec in RETIRED:
                raise ConfigurationError(f"Legacy model {spec}; choose --model {RETIRED[spec]} explicitly")
            if spec.startswith("deepseek-"):
                provider = "deepseek"
            elif spec.startswith("qwen-"):
                provider = "qwen"
            elif spec.startswith("kimi-"):
                provider = "moonshot"
            elif spec.startswith("ernie-"):
                provider = "baidu"
            elif spec.startswith("gemini-"):
                provider = "gemini"
            else:
                raise ConfigurationError("Use provider/model, for example groq/openai/gpt-oss-120b")
            model = spec
        if provider not in PROVIDERS or not model.strip():
            raise ConfigurationError(f"Unknown provider or empty model: {provider}")
        if model in RETIRED:
            raise ConfigurationError(f"Legacy model {model}; choose --model {RETIRED[model]} explicitly")
        base_url, key_variable = PROVIDERS[provider]
        base_url = os.getenv(f"{provider.upper()}_BASE_URL", base_url)
        if provider == "compatible":
            base_url = os.getenv("LLM_BASE_URL", base_url)
        if not base_url:
            raise ConfigurationError("Set LLM_BASE_URL for compatible/model")
        key = os.getenv(key_variable, "").strip()
        if not key and provider != "ollama":
            raise ConfigurationError(f"Set {key_variable} in the local .env file")
        try:
            timeout = float(os.getenv("LLM_TIMEOUT", "60"))
            attempts = int(os.getenv("LLM_ATTEMPTS", "3"))
        except ValueError as exc:
            raise ConfigurationError("LLM_TIMEOUT and LLM_ATTEMPTS must be numeric") from exc
        if not 0 < timeout <= 600 or not 1 <= attempts <= 5:
            raise ConfigurationError("LLM_TIMEOUT must be in (0, 600], LLM_ATTEMPTS in [1, 5]")
        return cls(provider, model, base_url, key or "ollama", timeout, attempts)
