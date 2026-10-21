import argparse
import json

from llms import ConfigurationError, ModelAPIError, ModelClient, ModelConfig


def check(model, generate=False):
    result = {"model": model}
    try:
        config = ModelConfig.resolve(model)
        with ModelClient(config) as client:
            models = client.models()
            result = {"provider": config.provider, "model": config.model,
                      "listed": config.model in models or f"models/{config.model}" in models, "available_models": models}
            if generate:
                result["response"] = client.complete(prompt="Reply only OK", max_tokens=128)
                result["generation"] = "passed"
            return result
    except (ConfigurationError, ModelAPIError) as exc:
        result["error"] = str(exc)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+")
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    results = [check(model, args.generate) for model in args.models]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return int(any("error" in result or not result.get("listed") for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
