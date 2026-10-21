from agent.resources import example_limit
import json
from datetime import datetime

from chat_history import ChatHistory
from common.show_utils import show_response
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


def extract_verification(res: str) -> str:
    pattern = r"<verify>(.*?)</verify>"
    match = re.search(pattern, res, re.DOTALL)
    if match:
        return match.group(1).strip()
    return res


class ReviewGenerationAgent:

    def __init__(
            self, name: str,
            distilled_tree:
            KnowledgeGraph,
            model: str,
            progress: Progress,
            review_history:
            ChatHistory
    ):
        self.review_history = review_history
        self.name = name
        self.distilled_tree = distilled_tree
        self.begin = datetime.now()
        self.final_prompt_template = read_prompt("review_generate_reply")
        self.suggestion = None
        self.model = model
        self.progress = progress

        example_prompt_template = read_prompt("single_question_review")
        with open(f"{dataset_directory()}/review_generation_examples.json", "r", encoding="utf-8") as f:
            example_dataset = json.loads(f.read())

        examples = []
        num = 1
        for example in example_dataset[:example_limit()]:
            examples.append(
                example_prompt_template.format(
                    description=example["description"],
                    distilled_tree=example["knowledge_graph"],
                    review_history=example["review_history"],
                    reply=example["reply"],
                    newest_question=example["newest_question"],
                    verification=example["verification"],
                    reasons=example["thought"],
                    task_progress=example["task_progress"],
                    num=num
                )
            )
            num += 1
        self.examples = "\n\n".join(examples)

    def get_prompt(self):
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
            domain=self.distilled_tree.domain,
            examples=self.examples,
            distilled_tree=self.readable_tree,
            review_history=self.format_chat_history(self.review_history.get_message()[-10:]),
            newest_question=self.review_history.get_message()[-10:][-1]['content'],
            task_progress=self.task_progress,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    def generate_review(self):
        prompt = self.get_prompt()

        # show_response(res=prompt, title="REVIEW PROMPT")

        res = chat(prompt=prompt, model=self.model, temperature=0.7)

        return extract_verification(res=res), extract_reply(res=res)

    def format_chat_history(self, messages):
        formatted = ""
        for message in messages:
            formatted += message['role'] + ": " + message['content'].replace("\n", "") + "\n\n"

        return formatted
