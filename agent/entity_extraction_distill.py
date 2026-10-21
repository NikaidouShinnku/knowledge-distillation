import json
from typing import List

import pyperclip

from common.show_utils import show_response
from chat_history import ChatHistory
from dataset import dataset_directory
from interviewee import interviewee_directory
from llms import chat
from prompts import read_prompt
from knowledge_graph.model import KnowledgeGraph


class EntityExtractionAgent:
    def __init__(
            self,
            name: str,
            distilled_tree: KnowledgeGraph,
            chat_history: ChatHistory,
            model: str,
            entity_types: List,
            entity_relationship_triple
    ):
        self.chat_history = chat_history
        self.name = name
        self.distilled_tree = distilled_tree
        self.model = model
        self.entity_types = entity_types
        self.entity_relation_triple = entity_relationship_triple

        self.final_prompt_template = read_prompt("entity_extraction_distill")

    def get_prompt(self):
        messages = self.chat_history.get_message()
        current_response = messages[-1]['content']
        chat_history = messages[:-1]
        return self.final_prompt_template.format(


            record_delimiter='##',
            tuple_delimiter='<|>',
            completion_delimiter='<|COMPLETE|>',
            entity_types=self.entity_types,
            domain=self.distilled_tree.domain,
            input_text=current_response,
            history_entities=self.entity_relation_triple.get_entities(),
            history_relationships=self.entity_relation_triple.get_relationships()
        )

    def write_mermaid_to_file(self, mermaid_code: str, file_path):
        try:
            with open(file_path + ".mmd", 'w', encoding='utf-8') as file:
                file.write(mermaid_code)
            print(f"Mermaid code successfully written to {file_path}")
        except Exception as e:
            print(f"An error occurred while writing to the file: {e}")

    def extract_triplet(self, turn: int):
        for i in range(3):
            try:
                return self.do_extract_triplet(turn=turn)
            except (ValueError, IndexError, KeyError) as exc:
                if i == 2:
                    raise ValueError("Fail to extract relationships") from exc


    def do_extract_triplet(self, turn:int):
        prompt = self.get_prompt()


        res = chat(prompt=prompt, model=self.model)


        from common.mermaid_code import parse_entity_relation, generate_mermaid

        entity, relation = parse_entity_relation(res)
        self.entity_relation_triple.merge_entities_and_relationships(entity, relation)
        mermaid_code = generate_mermaid(self.entity_relation_triple.get_entities(), self.entity_relation_triple.get_relationships())

        return mermaid_code, relation
