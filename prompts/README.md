# Prompt bundles

Templates are grouped by purpose and language:

- `agents.zh-CN.toml` / `agents.en-US.toml`: interviewer, expert, extraction, review, summary and style templates.
- `cards.zh-CN.toml` / `cards.en-US.toml`: reusable instruction and example cards.
- `shared.zh-CN.toml` / `shared.en-US.toml`: identical blocks shared by multiple templates.

The original 23 template names remain available. `[[include:shared_01]]` references are expanded before Python format placeholders are filled. `manifest.json` records rendered content hashes; the Chinese hashes were captured from the original templates before consolidation.

```python
from prompts import read_prompt

read_prompt("summary")
read_prompt("summary", language="en-US")
read_prompt("summary.en-US")
```

The default language is `zh-CN`. Set `PROMPT_LANGUAGE=en-US` in `.env` to select the English bundles globally. Explicit language arguments or suffixes override the environment. English templates translate the instructions; original requirements to answer in Chinese still apply.

中文版仅抽取完全相同的公共片段，加载后的内容与原模板一致。各角色、流程和示例仍分别保留。英文版保留原有规则、示例、参数与输出结构，不会自动把原来的中文回答要求改成英文回答。
