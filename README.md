# Knowledge Distillation Expert Agent

A multi-agent system that interviews human domain experts and automatically distills, organizes, and structures their tacit knowledge into a queryable knowledge tree — built during an AI R&D internship at Jiangsu YXT Network Technology (an enterprise learning platform serving 2,500+ corporate clients).

## Overview

Large organizations often struggle to share the expertise locked inside individual experts' heads. This project addresses that with a group of cooperating LLM-powered agents that conduct a structured "interview" with an expert, extract the knowledge shared in real time, evaluate its relevance and depth, and continuously build a living knowledge tree that the whole organization can learn from.

## How It Works

Given a **topic** and a set of **goals**, the agent group runs an interactive loop:

1. **Generation Agent** – asks the expert well-crafted questions, keeping the conversation natural and steering it toward the interview goals.
2. **Distillation Agent** – extracts knowledge points from the expert's answers and places them into the knowledge tree, keeping structure and relationships accurate.
3. **Evaluation Agent** – scores each answer for relevance and depth/breadth, flags weak or off-topic responses, and can refine/restructure the knowledge tree.
4. **Feedback Agent** – reviews and prioritizes the Generation Agent's candidate questions so the interview stays focused when time or attention is limited.

The expert can watch the knowledge tree, scores, and progress build up live, and can inspect or tweak the underlying prompts ("Prompt cards") and parameters ("Data cards") of any agent at any time.

## Key Features

- Real-time knowledge tree / knowledge graph construction during the conversation
- Live relevance & professionalism scoring of expert answers
- Adjustable interview tone/persona and per-agent prompt customization
- Save/load interview sessions (snapshotting)
- Voice input/output (ASR/TTS) support
- A "simulated expert" mode for testing the agent flow without a live human
- Slash-command controls, e.g. `/tree`, `/graph`, `/progress`, `/refine`, `/undo`, `/redo`

## Prompt Engineering

The agents are built almost entirely through prompt design rather than fine-tuning, combining:
- Role-play personas (e.g. an experienced interviewer / data analyst)
- Few-shot examples
- Chain-of-Thought reasoning
- Prompt-based tool calling

## Tech Stack

Python · LLM APIs · JSON/text-based prompt & example templates

## Project Scale

~3,500 lines of Python, ~2,800 lines of prompt/example templates (JSON & text), built over ~1 month, with roughly 10M tokens used during testing and iteration.

## Status

This was a personal/internship R&D project exploring multi-agent knowledge extraction. The core interview → extraction → evaluation → feedback loop is generalizable beyond knowledge distillation to other structured-conversation tasks.

## Run (Windows / Python 3.12)

Prompt templates are grouped into bilingual bundles under `prompts/`. The
default remains Chinese; set `PROMPT_LANGUAGE=en-US` in `.env` to load the
English translations. Original response-language requirements still apply.
See [prompt names and usage](prompts/README.md).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set your keys in the local `.env` file. Existing environment variables take
precedence. `.env` is ignored by Git and excluded from source exports.

```powershell
.\.venv\Scripts\python.exe main.py --model groq/openai/gpt-oss-120b
.\.venv\Scripts\python.exe main.py --model gemini/gemini-flash-lite-latest
```

Both providers have a free tier with quotas; availability depends on your
account and model. No automatic fallback to another provider is performed.
The default model comes from `LLM_MODEL`, otherwise Groq GPT-OSS 120B.
Legacy model names produce a migration message rather than silently
changing the provider or billing behavior.

Commands during an interview:

- `/model` displays the selected model.
- `/model gemini/gemini-flash-lite-latest` switches every agent to Gemini.
- `/model groq/openai/gpt-oss-20b` switches every agent to Groq.
- `/models groq` or `/models gemini` lists models available to your key.
- `/dump` saves `snapshot/test-snapshot2.json`; use `--restore test-snapshot2`
  to restore. An explicit `--model` overrides the saved model.
- `/undo` and `/redo` affect the knowledge tree and its progress.
- `/quit` or `/exit` ends the session.

`--auto` simulates an expert and still uses the selected API. `--stream`
streams question generation; extraction uses complete JSON responses.
`--evaluate` enables answer scoring with an extra model call. A question
rejected five times stops the interview rather than reaching the expert.

The common client also supports `deepseek/<model>`, `qwen/<model>`,
`moonshot/<model>`, `baidu/<model>`, `ollama/<model>`, and
`compatible/<model>`. The compatible provider requires `LLM_BASE_URL` and
`LLM_API_KEY`. Provider-specific endpoints can be overridden using
`GROQ_BASE_URL`, `GEMINI_BASE_URL`, and corresponding provider names.
Ollama defaults to `http://127.0.0.1:11434/v1` and requires a running local
server and downloaded model. Models are selected explicitly; support for
a provider does not imply its key, quota, or every model was validated.

Check model access without generating tokens, or explicitly test generation:

```powershell
.\.venv\Scripts\python.exe -m llms.check groq/openai/gpt-oss-120b gemini/gemini-flash-lite-latest
.\.venv\Scripts\python.exe -m llms.check groq/openai/gpt-oss-20b --generate
```

Token counts are recorded when returned by the provider. Cost is not
estimated using the obsolete price constants; consult your provider bill.

Optional voice and graph dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
```

Graph rendering requires Mermaid CLI (`mmdc`) on PATH, or its executable
path in `MERMAID_CLI`. If Puppeteer needs a system browser, set
`MERMAID_PUPPETEER_CONFIG` to a Puppeteer JSON configuration file.
Use `--graph` to render every round, or `/graph` manually. The PNG is saved
to `task_result/knowledge_graph.png`; WezTerm can display it inline when
available. TTS uses `edge-tts` through the current Python interpreter;
playback uses ffplay when installed, otherwise miniaudio. ASR requires
a working microphone and `GROQ_API_KEY`. Audio transcription shares the
common API client and its retry/error handling. Unavailable audio devices
fall back to text input.

Validation on Windows/Python 3.12 covers 52 automated tests, all 16
interview-mode combinations, every plan/persona combination, real Gemini
interview/evaluation/summary, real Groq calls, Mermaid PNG export, speech
synthesis/playback and transcription of synthesized speech. Microphone
capture on the test machine failed at the driver level; its failure path
and device cleanup are tested. Free-tier Groq calls can wait for token
rate-limit windows; the client honors reset headers or waits a bounded
window when those headers are missing.

Run offline regressions:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

See [repair notes](REPAIR_NOTES.zh-CN.md) for findings and validation.
Previously committed credentials remain in Git history and should be
rotated in their provider consoles.

Sources: [Groq free-plan limits](https://console.groq.com/docs/rate-limits),
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai),
[Ollama compatibility](https://docs.ollama.com/api/openai-compatibility).

The prompt example count defaults to one and can be set with
`LLM_EXAMPLE_LIMIT` (0–5). Interview prompts use the latest 20 messages
and review prompts the latest 10, while snapshots retain the full history.
Streaming question output keeps only the reply text instead of feeding
thought wrappers back into subsequent prompts.
