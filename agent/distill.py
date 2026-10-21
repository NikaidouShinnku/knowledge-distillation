from agent.resources import example_limit
import json

from knowledge_graph.actions import apply_actions, parse_actions

import pyperclip

from common.show_utils import show_response
from chat_history import ChatHistory
from dataset import dataset_directory
from interviewee import interviewee_directory
from llms import chat
from prompts import read_prompt
from knowledge_graph.model import KnowledgeGraph


class DistillAgent:
    def __init__(self, name: str, distilled_tree: KnowledgeGraph, chat_history: ChatHistory, interviewee: str, model: str):
        self.chat_history = chat_history
        self.name = name
        self.distilled_tree = distilled_tree
        self.interviewee = interviewee
        self.model = model

        self.final_prompt_template = read_prompt("roleplay_layer_distill")

        example_prompt_template = read_prompt("single_example")
        with open(f"{dataset_directory()}/distill_examples.json", "r", encoding="utf-8") as f:
            example_dataset = json.loads(f.read())

        examples = []
        num = 1
        for example in example_dataset[:example_limit()]:
            examples.append(
                example_prompt_template.format(
                    description=example["description"],
                    distilled_tree=example["knowledge_graph"],
                    chat_history=example["chat_history"],
                    current_response=example["current_response"],
                    actions=example["actions"],
                    num=num
                )
            )
            num += 1
        self.examples = "\n\n".join(examples)

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

    def get_prompt(self):
        messages = self.chat_history.get_message()[-20:]
        current_response = messages[-1]['content']
        chat_history = messages[:-1]
        return self.final_prompt_template.format(
            interviewee=self.interviewee_name,
            user_background=self.background_info,
            domain=self.distilled_tree.domain,
            examples=self.examples,
            distilled_tree=self.distilled_tree.get_tree(),
            chat_history=chat_history,
            current_response=current_response
        )

    def update_tree(self, turn: int):
        for i in range(3):
            previous = self.distilled_tree.model_copy(deep=True)
            try:
                return self.do_update_tree(turn=turn)
            except (ValueError, KeyError, TypeError) as exc:
                self.distilled_tree.__dict__.update(previous.__dict__)
                if i == 2:
                    raise ValueError("Fail to update tree") from exc


    def do_update_tree(self, turn: int):
        actions = parse_actions(chat(prompt=self.get_prompt(), model=self.model))
        current_response = self.chat_history.get_message()[-20:][-1]['content']
        apply_actions(self.distilled_tree, actions, current_response, turn)
        self.distilled_tree.dump("task_result/current_distilled_tree")
