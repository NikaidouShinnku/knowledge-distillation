from agent.resources import example_limit
import json

from knowledge_graph.actions import apply_actions, parse_actions

from common.show_utils import show_response
from chat_history import ChatHistory
from dataset import dataset_directory
from interviewee import interviewee_directory
from llms import chat
from prompts import read_prompt
from knowledge_graph.model import KnowledgeGraph


class SummaryAgent:
    def __init__(self,
                 name: str,
                 distilled_tree: KnowledgeGraph,
                 chat_history: ChatHistory,
                 model: str
                 ):
        self.chat_history = chat_history
        self.name = name
        self.distilled_tree = distilled_tree
        self.model = model

        self.final_prompt_template = read_prompt("summary")

        example_prompt_template = read_prompt("single_summary_example")
        with open(f"{dataset_directory()}/summary_examples.json", "r", encoding="utf-8") as f:
            example_dataset = json.loads(f.read())

        examples = []
        num = 1
        for example in example_dataset[:example_limit()]:
            examples.append(
                example_prompt_template.format(
                    description=example["description"],
                    distilled_tree=example["knowledge_graph"],
                    chat_history=example["chat_history"],
                    thought=example["thought"],
                    actions=example["actions"],
                    num=num
                )
            )
            num += 1
        self.examples = "\n\n".join(examples)


    def get_prompt(self):
        chat_history = self.chat_history.get_message()[-20:]
        return self.final_prompt_template.format(
            domain=self.distilled_tree.domain,
            examples=self.examples,
            distilled_tree=self.distilled_tree.get_tree(),
            chat_history=chat_history,
        )

    def restructure(self, turn: int):
        previous = self.distilled_tree.model_copy(deep=True)
        try:
            return self.do_restructure(turn)
        except Exception:
            self.distilled_tree.__dict__.update(previous.__dict__)
            raise

    def do_restructure(self, turn: int):
        res = chat(prompt=self.get_prompt(), model=self.model)
        actions = parse_actions(res)
        messages = self.chat_history.get_message()[-20:]
        response = messages[-1]['content'] if messages else ""
        apply_actions(self.distilled_tree, actions, response, turn)
        show_response(res, title="重新结构化知识树")
