import copy


class KnowledgeTreeManager:
    def __init__(self):
        self.knowledge_tree_stack = []
        self.cursor = -1

    def push_back(self, knowledge_tree):
        del self.knowledge_tree_stack[self.cursor + 1:]
        self.knowledge_tree_stack.append(copy.deepcopy(knowledge_tree))
        self.cursor += 1

    def get_current_tree(self):
        if self.cursor < 0:
            return None
        return copy.deepcopy(self.knowledge_tree_stack[self.cursor])

    def undo(self):
        if self.cursor > 0:
            self.cursor -= 1
        return self.get_current_tree()

    def redo(self):
        if self.cursor + 1 < len(self.knowledge_tree_stack):
            self.cursor += 1
        return self.get_current_tree()

    def pop(self):
        return self.undo()

    def list_all_trees(self):
        return [tree.model_dump() for tree in self.knowledge_tree_stack]
