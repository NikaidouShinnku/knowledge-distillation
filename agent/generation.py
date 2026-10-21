from agent.resources import example_limit
import json
from datetime import datetime

from chat_history import ChatHistory
from dataset import dataset_directory
from interviewee import interviewee_directory
from llms import chat
from progress.progress import Progress
from prompts import read_prompt
from knowledge_graph.model import KnowledgeGraph


import re


def extract_reply(res: str) -> str:
    pattern = r"<reply>(.*?)</reply>"
    match = re.search(pattern, res, re.DOTALL)
    if match:
        return match.group(1).strip()
    return res


def stream_reply(chunks):
    buffer = ""
    started = False
    closing = "</reply>"
    try:
        for chunk in chunks:
            buffer += chunk
            if not started:
                position = buffer.find("<reply>")
                if position < 0:
                    continue
                started = True
                buffer = buffer[position + len("<reply>"):]
            position = buffer.find(closing)
            if position >= 0:
                if position:
                    yield buffer[:position]
                return
            keep = len(closing) - 1
            if len(buffer) > keep:
                yield buffer[:-keep]
                buffer = buffer[-keep:]
        if buffer:
            yield buffer
    finally:
        close = getattr(chunks, "close", None)
        if close:
            close()


class GenerationAgent:

    def __init__(
            self, name: str,
            distilled_tree:
            KnowledgeGraph,
            chat_history:
            ChatHistory,
            interviewee: str,
            model: str,
            progress: Progress,
            tone: str,
            review_history:
            ChatHistory
    ):
        self.review_history = review_history
        self.chat_history = chat_history
        self.tone = tone
        self.name = name
        self.distilled_tree = distilled_tree
        self.interviewee = interviewee
        self.begin = datetime.now()
        self.final_prompt_template = read_prompt("roleplay_generate")


        self.suggestion = None
        self.model = model
        self.progress = progress

        background_prompt_template = read_prompt("single_background")
        with open(f"{interviewee_directory()}/{interviewee}.json", "r", encoding="utf-8") as f:
            background_dataset = json.loads(f.read())
            self.interviewee_name = background_dataset["name"]
            self.background_info = background_prompt_template.format(
                user_name=background_dataset["name"],
                user_age=background_dataset["age"],
                user_sex=background_dataset["sex"],
                user_edu=background_dataset["education_level"],
                user_prof=background_dataset["profession"],
                user_other=background_dataset["other"]
            )

        example_prompt_template = read_prompt("single_question")
        with open(f"{dataset_directory()}/generation_examples.json", "r", encoding="utf-8") as f:
            example_dataset = json.loads(f.read())

        examples = []
        num = 1
        for example in example_dataset[:example_limit()]:
            examples.append(
                example_prompt_template.format(
                    description=example["description"],
                    distilled_tree=example["knowledge_graph"],
                    chat_history=self.format_chat_history(example['chat_history']),
                    current_response=example["current_response"],
                    question=example["question"],
                    objective=example["target_objective"],
                    reasons=example["thought"],
                    review_history=example["review_history"],
                    num=num
                )
            )
            num += 1
        self.examples = "\n\n".join(examples)

    def get_prompt(self):
        messages = self.chat_history.get_message()[-20:]
        if len(messages) > 0:
            current_response = messages[-1]['content']
            chat_history = messages[:-1]
        else:
            current_response = ""
            chat_history = []

        progress_stats = self.progress.get_progress()
        task_progress_template = read_prompt("task_progress")
        self.task_progress = task_progress_template.format(
            **progress_stats
        )

        self.readable_tree = (self.distilled_tree.to_readable_tree
                              (drop_objective_attrs=["id"],
                               drop_knowledge_attrs=["id", "raw_user_response"]
                                ))

        return self.final_prompt_template.format(
            interviewee=self.interviewee_name,
            user_background=self.background_info,
            tone=self.tone,
            review_history=self.format_chat_history(self.review_history.get_message()[-10:]),
            domain=self.distilled_tree.domain,
            examples=self.examples,
            distilled_tree=self.readable_tree,
            chat_history=self.format_chat_history(chat_history),
            current_response=current_response,
            task_progress=self.task_progress,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    def generate_question(self, stream=False):
        prompt = self.get_prompt()


        res = chat(prompt=prompt, model=self.model, temperature=0.7, stream=stream)


        return stream_reply(res) if stream else extract_reply(res=res)

    def end_chat(self):
        self.get_prompt()
        end_prompt_template = read_prompt("end_timeover")

        chat_history = self.chat_history.get_message()[-20:]

        end_prompt = end_prompt_template.format(
            interviewee=self.interviewee_name,
            user_background=self.background_info,
            tone=self.tone,
            domain=self.distilled_tree.domain,
            distilled_tree=self.readable_tree,
            chat_history=chat_history,
            task_progress=self.task_progress
        )

        return chat(prompt=end_prompt, model=self.model, temperature=0.7)

    def format_chat_history(self, messages):
        formatted = ""
        for message in messages:
            formatted += message['role'] + ": " + message['content'].replace("\n", "") + "\n\n"

        return formatted
