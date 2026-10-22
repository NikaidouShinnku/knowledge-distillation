import time
import re

import httpx

from openai import APIConnectionError, APIStatusError, OpenAI

from llms.config import ModelConfig
from llms.statistics import update_usage


class ModelAPIError(RuntimeError):
    pass


class ModelClient:
    def __init__(self, config, client=None, sleeper=time.sleep):
        self.config = config
        self.client = client or OpenAI(api_key=config.api_key, base_url=config.base_url,
                                       timeout=config.timeout, max_retries=0)
        self.sleeper = sleeper

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def _call(self, operation):
        for attempt in range(self.config.attempts):
            try:
                return operation()
            except (APIConnectionError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                transient = status is None or status in (408, 409, 429) or status >= 500
                if not transient or attempt + 1 == self.config.attempts:
                    reason = str(status) if status else "connection or timeout"
                    hints = {401: "invalid or revoked key", 402: "insufficient balance",
                             403: "service disabled or permission denied", 404: "model or endpoint unavailable",
                             429: "quota or rate limit exceeded", 503: "service temporarily unavailable"}
                    hint = hints.get(status, "request failed")
                    raise ModelAPIError(f"{self.config.provider}/{self.config.model}: {reason} ({hint})") from None
                retry_after = getattr(exc, "response", None)
                headers = retry_after.headers if retry_after is not None else {}
                retry_after = headers.get("retry-after", "")
                try:
                    delay = min(60, max(0, float(retry_after)))
                except ValueError:
                    reset = headers.get("x-ratelimit-reset-tokens", "")
                    units = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}
                    values = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", reset)
                    if status == 429 and values:
                        delay = min(60, max(1, sum(float(value) * units[unit] for value, unit in values)))
                    else:
                        delay = 60 if status == 429 else min(8, 2 ** attempt)
                print(f"[{self.config.provider}: {'rate limited' if status == 429 else 'temporary API failure'}; retry {attempt + 2}/{self.config.attempts} in {delay:.1f}s]", flush=True)
                self.sleeper(delay)

    def models(self):
        return [model.id for model in self._call(self.client.models.list)]

    def transcribe(self, file, *, prompt=None, **kwargs):
        from pathlib import Path

        path = Path(file)
        payload = path.read_bytes()
        if prompt is not None:
            kwargs["prompt"] = prompt
        result = self._call(lambda: self.client.audio.transcriptions.create(
            model=self.config.model, file=(path.name, payload), **kwargs))
        return result.text

    def complete(self, *, prompt=None, messages=None, stream=False, **kwargs):
        if (prompt is None) == (messages is None):
            raise ValueError("Provide exactly one of prompt or messages")
        messages = [{"role": "user", "content": prompt}] if prompt is not None else messages
        if not messages:
            raise ValueError("Messages cannot be empty")
        response = self._call(lambda: self.client.chat.completions.create(
            model=self.config.model, messages=messages, stream=stream, **kwargs))
        if stream:
            return self._chunks(response)
        if response.usage:
            update_usage(response.usage)
        if not response.choices or response.choices[0].message.content is None:
            raise ModelAPIError(f"{self.config.provider}: no text response")
        return response.choices[0].message.content

    def _chunks(self, response):
        try:
            for chunk in response:
                if chunk.usage:
                    update_usage(chunk.usage)
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except (APIConnectionError, APIStatusError, httpx.HTTPError) as exc:
            raise ModelAPIError(f"{self.config.provider}: stream interrupted; partial output was not retried") from None
        finally:
            response.close()


def chat(model=None, *, stream=False, **kwargs):
    config = ModelConfig.resolve(model)
    if stream:
        def generate():
            with ModelClient(config) as client:
                yield from client.complete(stream=True, **kwargs)
        return generate()
    with ModelClient(config) as client:
        return client.complete(**kwargs)
