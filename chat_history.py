from typing import List, Dict, Any

from pydantic import BaseModel

class Message(BaseModel):
    role:str
    content:str

class ChatHistory(BaseModel):
    chat_history:List[Message] = []

    def append(self, role:str, content:str):
        self.chat_history.append(Message(role=role, content=content))

    def get_message(self):
        return self.model_dump()['chat_history']
