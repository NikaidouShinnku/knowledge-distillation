import json
import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from knowledge_graph.model import Knowledge, KnowledgeGraph


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Details(StrictModel):
    concept: str
    why_important: str | None = None
    knowledge_description: str | None = None
    example: str | None = None
    other: list[str] | None = None


class AddArguments(StrictModel):
    parent_id: str
    knowledge_detail: Details


class UpdateArguments(StrictModel):
    knowledge_id: str
    knowledge_type: Literal["concept", "why_important", "knowledge_description", "example", "other"]
    knowledge_detail: str | list[str]

    @model_validator(mode="after")
    def validate_detail(self):
        if (self.knowledge_type == "other") != isinstance(self.knowledge_detail, list):
            raise ValueError("other requires a list; text fields require a string")
        return self


class DeleteArguments(StrictModel):
    knowledge_id: str


class MoveArguments(StrictModel):
    source_knowledge_id: str
    destination_knowledge_id: str


class GeneralizeArguments(AddArguments):
    sub_knowledge_ids: list[str] = Field(min_length=1)


class AddAction(StrictModel):
    action: Literal["add_new_knowledge_node"]
    arguments: AddArguments


class UpdateAction(StrictModel):
    action: Literal["update_existing_knowledge_node"]
    arguments: UpdateArguments


class DeleteAction(StrictModel):
    action: Literal["delete_knowledge_node"]
    arguments: DeleteArguments


class MoveAction(StrictModel):
    action: Literal["move_knowledge_node"]
    arguments: MoveArguments


class GeneralizeAction(StrictModel):
    action: Literal["generalize_and_combine_knowledge"]
    arguments: GeneralizeArguments


Action = Annotated[Union[AddAction, UpdateAction, DeleteAction, MoveAction, GeneralizeAction], Field(discriminator="action")]
ACTION_LIST = TypeAdapter(list[Action])


def parse_actions(text):
    if not isinstance(text, str):
        raise ValueError("Expected a JSON response")
    tagged = re.search(r"<action>\s*(.*?)\s*</action>", text, re.DOTALL)
    payload = tagged.group(1).strip() if tagged else text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", payload, re.DOTALL)
    payload = fenced.group(1).strip() if fenced else payload
    if not payload.startswith("["):
        start = payload.find("[")
        if start < 0:
            raise ValueError("No action array in response")
        payload = payload[start:]
    actions, remaining = json.JSONDecoder().raw_decode(payload)
    if payload[remaining:].strip():
        raise ValueError("Unexpected content after action array")
    return ACTION_LIST.validate_python(actions)


def apply_actions(tree, actions, response, turn):
    candidate = tree.model_copy(deep=True)
    for action in actions:
        arguments = action.arguments
        if isinstance(action, AddAction):
            candidate.add_knowledge_node(response, arguments.knowledge_detail.model_dump(exclude_none=True), turn, arguments.parent_id)
        elif isinstance(action, UpdateAction):
            candidate.renew_knowledge(response, arguments.knowledge_detail, arguments.knowledge_type, turn, arguments.knowledge_id)
        elif isinstance(action, DeleteAction):
            candidate.delete_knowledge(arguments.knowledge_id)
        elif isinstance(action, MoveAction):
            candidate.move_knowledge(arguments.source_knowledge_id, arguments.destination_knowledge_id)
        elif isinstance(action, GeneralizeAction):
            candidate.generalize_knowledge(response, arguments.knowledge_detail.model_dump(exclude_none=True), arguments.sub_knowledge_ids, turn, arguments.parent_id)
    validated = KnowledgeGraph.model_validate(candidate.model_dump())
    tree.__dict__.update(validated.__dict__)
