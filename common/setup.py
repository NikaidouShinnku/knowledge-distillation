import json
from pathlib import Path
import uuid

from prompt_toolkit import prompt

from interviewee import interviewee_directory
from knowledge_graph.model import KnowledgeGraph, Objective
from plan import plan_directory


def choose(title, options, extra=None):
    print(title)
    for index, label in enumerate(options, 1):
        print(f"{index}. {label}")
    if extra:
        print(f"0. {extra}")
    while True:
        value = prompt(">> ").strip()
        if value.isdecimal():
            index = int(value)
            if 1 <= index <= len(options):
                return index - 1
            if index == 0 and extra:
                return None
        print("Please enter one of the listed numbers.")


def required(label):
    while True:
        value = prompt(label).strip()
        if value:
            return value
        print("This field is required.")


def write_local(directory, prefix, data):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    identifier = f"{prefix}{uuid.uuid4().hex}"
    with (directory / f"{identifier}.json").open("x", encoding="utf-8", newline="\n") as target:
        json.dump(data, target, ensure_ascii=False, indent=2)
        target.write("\n")
    return identifier


def select_expert(directory=None):
    directory = Path(directory or interviewee_directory())
    profiles = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("name") and all(key in data for key in ("age", "sex", "education_level", "profession", "other")):
                profiles.append((path.stem, data))
        except (ValueError, OSError, AttributeError):
            print(f"Skipping invalid expert profile: {path.name}")
    selected = choose("Who are you? / 你是谁？", [f"{data['name']} ({data['profession']})" for _, data in profiles], "None of these / 都不是我")
    if selected is not None:
        return profiles[selected][0]
    print("Create your expert profile. Optional fields may be left blank.")
    data = {"name": required("Name / 姓名: ")}
    for key, label in (("age", "Age / 年龄"), ("sex", "Gender / 性别"), ("education_level", "Education / 学历"), ("profession", "Profession and expertise / 职业与专长"), ("other", "Other background / 其他背景")):
        data[key] = prompt(f"{label} (optional): ").strip()
    identifier = write_local(directory, "local-", data)
    print(f"Expert profile saved: {data['name']}")
    return identifier


def select_topic(directory=None):
    directory = Path(directory or plan_directory())
    topics = []
    for path in sorted(directory.glob("*.json")):
        try:
            tree = KnowledgeGraph.model_validate_json(path.read_text(encoding="utf-8"))
            if tree.objectives and tree.estimated_minute and tree.estimated_minute > 0:
                topics.append((path.stem, tree))
        except (ValueError, OSError):
            print(f"Skipping invalid topic: {path.name}")
    selected = choose("Choose an interview topic / 选择访谈话题", [f"{tree.name} - {tree.domain} ({tree.estimated_minute} min)" for _, tree in topics], "Create a topic / 新建话题")
    if selected is not None:
        return topics[selected][0]
    name = required("Topic / 话题名称: ")
    domain = required("Domain / 领域: ")
    description = required("What would you like to discuss? / 访谈目标: ")
    outline = prompt("Objectives, separated by ; / 分目标，用分号分隔 (optional): ").strip()
    objectives = [part.strip() for part in outline.replace("；", ";").split(";") if part.strip()] or [description]
    while True:
        minutes = prompt("Duration in minutes / 时长，分钟 [30]: ").strip() or "30"
        if minutes.isdecimal() and 1 <= int(minutes) <= 480:
            break
        print("Please enter a duration between 1 and 480 minutes.")
    tree = KnowledgeGraph(name=name, domain=domain, task_description=description, objectives=[Objective(obj_description=objective) for objective in objectives], estimated_minute=int(minutes))
    identifier = write_local(directory, "local-", tree.model_dump())
    print(f"Topic saved: {name}")
    return identifier


def select_tone(language):
    tones = ["Serious", "Humorous", "Pirate", "Shakespearean", "Neutral"] if language == "en-US" else ["严肃", "幽默", "海盗式", "甄嬛传风格", "莎士比亚式", "鲁迅风格", "无建议"]
    selected = choose("Choose the interviewer's tone / 选择访谈风格", tones)
    return tones[selected]
