"""
Minimal LangGraph orchestration example connecting Orchestrator -> Coder -> QA.

This is a proof-of-concept that demonstrates how to wire agents using the
installed LangGraph runtime. It keeps the flow local and deterministic so it
can run without cloud APIs.
"""
from typing import TypedDict, Any

try:
    from langgraph.graph import StateGraph, START, END
except Exception:
    StateGraph = None
    START = 'START'
    END = 'END'


class OrchestrationState(TypedDict, total=False):
    task: str
    subtasks: list[dict[str, Any]]
    artifact: dict[str, str]
    qa: dict[str, Any]


def build_graph():
    """Build a small orchestration graph.

    If LangGraph is unavailable, fall back to the in-repo simple graph so the
    proof-of-concept remains runnable.
    """
    if StateGraph is not None:
        graph = StateGraph(OrchestrationState)

        def decompose(state: OrchestrationState) -> OrchestrationState:
            return {
                'task': state.get('task', 'demo: create hello world'),
                'subtasks': [
                    {'id': 1, 'role': 'coder', 'prompt': 'Implement a hello world script'},
                    {'id': 2, 'role': 'qa', 'prompt': 'Write and run tests for hello world'},
                ],
            }

        def assign(state: OrchestrationState) -> OrchestrationState:
            subtasks = []
            for subtask in state.get('subtasks', []):
                updated = dict(subtask)
                updated['status'] = 'assigned'
                subtasks.append(updated)
            return {'subtasks': subtasks}

        def coder(state: OrchestrationState) -> OrchestrationState:
            return {
                'artifact': {
                    'path': 'github-repos/demo/hello.py',
                    'content': 'print("Hello, world")',
                }
            }

        def qa(state: OrchestrationState) -> OrchestrationState:
            return {'qa': {'passed': True, 'coverage': 100}}

        graph.add_node('decompose', decompose)
        graph.add_node('assign', assign)
        graph.add_node('coder', coder)
        graph.add_node('qa', qa)
        graph.add_edge(START, 'decompose')
        graph.add_edge('decompose', 'assign')
        graph.add_edge('assign', 'coder')
        graph.add_edge('coder', 'qa')
        graph.add_edge('qa', END)

        return graph.compile()

    # Fallback simple graph implementation
    class SimpleGraph:
        def __init__(self):
            self.nodes = {}

        def add_node(self, name, fn):
            self.nodes[name] = fn

        def invoke(self, state):
            cur = START
            while True:
                fn = self.nodes.get(cur)
                if fn is None:
                    break
                nxt = fn(state)
                if nxt == END:
                    break
                cur = nxt
            return state

    g = SimpleGraph()

    def start(state):
        state['task'] = state.get('task', 'demo: create hello world')
        return 'decompose'

    def decompose(state):
        state['subtasks'] = [
            {'id': 1, 'role': 'coder', 'prompt': 'Implement a hello world script'},
            {'id': 2, 'role': 'qa', 'prompt': 'Write and run tests for hello world'}
        ]
        return 'assign'

    def assign(state):
        for t in state['subtasks']:
            t['status'] = 'assigned'
        return 'coder'

    def coder(state):
        state['artifact'] = {'path': 'github-repos/demo/hello.py', 'content': 'print("Hello, world")'}
        return 'qa'

    def qa(state):
        state['qa'] = {'passed': True, 'coverage': 100}
        return END

    g.add_node(START, start)
    g.add_node('decompose', decompose)
    g.add_node('assign', assign)
    g.add_node('coder', coder)
    g.add_node('qa', qa)

    return g


if __name__ == '__main__':
    graph = build_graph()
    state: OrchestrationState = {'task': 'Demo: build hello world'}
    result = graph.invoke(state)
    print('Graph finished. State:')
    print(result)
