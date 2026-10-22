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
default is English. Use `--prompt-language zh-CN` for Chinese prompts and the
original Chinese style menu. English prompts require English dialogue, reviewer
feedback, summaries and extracted knowledge, including when the user replies in Chinese.
See [prompt names and usage](prompts/README.md).

Install **64-bit Python 3.12** and **Node.js 22.13 or newer with npm** first.
Reopen the terminal after installing Node.js. From the project directory, run
the complete installer (the same command works in CMD and PowerShell):

```text
python install.py
```

Windows users can also double-click `install.cmd`. The installer creates
`.venv`, installs all Python dependencies from `requirements.txt`, installs
Mermaid CLI locally from `package.json`, and verifies an actual PNG render.
It uses an installed Edge/Chrome browser when available; otherwise Puppeteer
downloads its browser during npm installation. Allow the initial download to finish.
`task_result/install-check.png` confirms that rendering succeeded.

图形、语音所需的 Python 包现在都属于默认必装依赖，不再需要单独安装可选包。
Mermaid CLI 是 Node.js 工具，不能由 pip 安装；请运行上面的统一安装脚本，
不要只执行 `pip install -r requirements.txt` 后就跳过图形工具。
`requirements-optional.txt` 仅保留旧命令兼容，现在也会安装完整 Python 依赖。

For an existing virtual environment, the manual equivalent is:

```text
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
```

Copy `.env.example` to `.env` if `.env` does not already exist. In CMD use
`if not exist .env copy .env.example .env`; in PowerShell use:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set your keys in the local `.env` file. Existing environment variables take
precedence. `.env` is ignored by Git and excluded from source exports.

### API keys (required / 必须配置)

This repository does not include shared API keys or a bundled offline model.
Each user must supply their own API key before using a cloud model. Downloading
the repository or installing dependencies does not configure a key automatically.

使用云端模型前，需要自行申请 API 密钥并填入项目根目录的 `.env` 文件，
与 `main.py` 放在同一目录。仓库只提供空白的 `.env.example`，不包含可用密钥。
复制 `.env.example` 后，请编辑 `.env`；只编辑 `.env.example` 不会生效。
至少配置下面的一家，并将示例占位值替换为自己的真实密钥。

For Groq:

```dotenv
LLM_MODEL=groq/openai/gpt-oss-120b
GROQ_API_KEY=your-own-groq-api-key
```

For Gemini instead:

```dotenv
LLM_MODEL=gemini/gemini-flash-lite-latest
GEMINI_API_KEY=your-own-gemini-api-key
```

`LLM_MODEL` may be left empty to select an existing Groq key first, then Gemini.
If you set `LLM_MODEL` or pass `--model`, configure the corresponding provider's
key. Both keys can coexist in the same `.env` file. A missing-key error such as
`Set GROQ_API_KEY in the local .env file` means that the selected model's key is
missing or empty; installing more packages will not fix it. Free-tier access is
subject to the provider's quotas and availability. Keep `.env` private when
sharing the project, and preserve it when updating or re-extracting a ZIP.

```powershell
.\.venv\Scripts\python.exe main.py --model groq/openai/gpt-oss-120b
.\.venv\Scripts\python.exe main.py --model gemini/gemini-flash-lite-latest
```

Startup asks who you are, lists saved expert names, and offers
`None of these / 都不是我` to collect and save a new expert profile.
Next, choose an existing interview topic or create one with your own objectives.
For a realistic demonstration, choose Alex Chen (Machine Learning Engineer)
with ML Fundamentals, or Emily Parker (Early Childhood Educator) with Fundamentals
of Early Childhood Education. Both are fictional example profiles. The original
Maria and Arthas profiles remain available.
Your new profiles and topics are local files ignored by Git. To skip these menus,
pass `--interviewee maria --task organism-classification-distill-plan`.
Restoring a snapshot skips the setup menus and preserves its expert, topic and tone.

The English style menu includes Serious, Humorous, Pirate, Shakespearean and Neutral.
The default `conversation` mode shows the question proposer and reviewer in
separate group-discussion panels, followed by the approved interviewer question.
Streaming replies retain the bordered panels. Question review adds a model call
and may request revisions. For fewer calls, select `--generation-mode solo`,
which updates the knowledge tree and generates the next question with two model
calls per ordinary turn. Entity relationship
extraction is optional via `--entities` and is also enabled by `--graph`.
Question review, entity extraction and evaluation each add model calls.
Replies stream by default; `--no-stream` waits for the complete reply.
Processing stages show elapsed time, and rate-limit retries show their wait time.

Both providers have a free tier with quotas; availability depends on your
account and model. No automatic fallback to another provider is performed.
An explicit `--model` takes priority, followed by a non-empty `LLM_MODEL`.
Without either, an existing Groq key selects Groq GPT-OSS 120B; otherwise an
existing Gemini key selects Gemini Flash Lite. This selects a configured
provider at startup; failed requests do not silently switch providers.
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

`--auto` simulates an expert and still uses the selected API. Extraction uses
complete JSON responses. `--evaluate` enables answer scoring with an extra model
call. In conversation mode, a question rejected five times stops the interview
rather than reaching the expert.

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

## Graph, knowledge edits and saved sessions / 图形、修改和存档

### View the graph / 怎么看图

The knowledge tree and the entity relationship graph are separate views.
`/tree` displays objectives and distilled knowledge directly in the terminal.
`/graph` renders the entities and relationships collected from expert replies.
Relationship extraction makes an additional API call, so enable it when starting:

```text
.venv\Scripts\python.exe main.py --entities
```

Choose an expert and topic, then answer at least one question. At the next input
prompt, enter `/graph`. The image opens with the Windows default image viewer;
WezTerm can display it inline when running inside WezTerm, but is not required.
Other desktops use their default browser. The saved files are:

- `task_result/knowledge_graph.png`: the latest rendered relationship graph.
- `task_result/knowledge_graph.mmd`: editable Mermaid source for that graph.

For automatic rendering after every answer, start with `--graph` instead:

```text
.venv\Scripts\python.exe main.py --graph
```

刚开始还没回答问题时，图中还没有实体；此时 `/graph` 会解释如何收集数据，
不是图形功能被删除。未使用 `--entities` 或 `--graph` 的会话仍然会更新知识树，
但不会额外调用模型收集关系图数据。此时可以用 `/tree` 查看知识树。

The renderer discovers project-local Mermaid CLI automatically, then a global
`mmdc`, or an explicit executable/script path in `MERMAID_CLI`. A custom browser
configuration can be selected with `MERMAID_PUPPETEER_CONFIG`. If `mmdc` is
missing, run `python install.py`; for a missing browser, remove a stale custom
browser configuration and rerun the installer with browser downloads enabled.

### Edit knowledge and diagrams / 怎么修改

During an interview, type a correction or instruction as a normal answer,
for example: `Rename the knowledge node about accuracy to Classification accuracy`
or `Remove the duplicated knowledge node about supervised learning`.
The extraction agent applies supported add/update/delete operations to the
knowledge tree. Use `/tree` to check the result, `/undo` to undo a tree change,
and `/redo` to restore it. These commands affect the knowledge tree, not the
separately collected entities and relationships. `/refine` asks the model to
reorganize the tree and makes another API call.

To change only the diagram labels or connections, edit
`task_result/knowledge_graph.mmd` in a text editor, then render it manually:

```text
node node_modules/@mermaid-js/mermaid-cli/src/cli.js -i task_result/knowledge_graph.mmd -o task_result/knowledge_graph.png -t dark -b transparent
```

If using a system browser instead of Puppeteer's downloaded browser, add
`-p path/to/puppeteer.json`, where the JSON contains an `executablePath` pointing
to that browser. Open the resulting PNG from Explorer. Editing `.mmd` changes
only that diagram; it does not modify the knowledge tree or saved relationships.
The next `/graph` regenerates and overwrites these files from session data.
Keep a separate copy if you want to retain a hand-edited diagram.

### Save, restore and customize / 保存、恢复和定制

Enter `/dump` to save `snapshot/test-snapshot2.json`, including the knowledge
tree, conversation, progress and entity relationship data. Restore it with:

```text
.venv\Scripts\python.exe main.py --restore test-snapshot2
```

For direct data edits, stop the interview, back up the snapshot, then edit its
`knowledge_graph` or `entity_graph` sections and restore it. Keep JSON valid and
preserve node identifiers and relationship source/target names. There is no
dedicated interactive relationship-edit command; editing a snapshot is the
persistent way to correct collected entities or relationships.

Use the startup menus to create expert profiles and topics. To edit an existing
expert, change the fields in `interviewee/*.json`; to edit a topic, change its
description, objectives or duration in `plan/*.json`. Restart to load the edits.
Files named `local-*.json` created by the menus stay local and are ignored by Git.

### Voice / 语音

Voice dependencies are installed by default. Launch with `--tts` for spoken
interviewer replies; type `/asr` to record and transcribe an answer. TTS uses
`edge-tts` through the current Python interpreter;
playback uses ffplay when installed, otherwise miniaudio. ASR requires
a working microphone and `GROQ_API_KEY`. Audio transcription shares the
common API client and its retry/error handling. Unavailable audio devices
fall back to text input.

Validation on Windows/Python 3.12 covers 81 automated tests, all 16
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
