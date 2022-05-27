import ast
import sys

from scalpel.cfg import CFGBuilder

with open(sys.argv[1], 'r') as f:
    source = f.read()

tree = ast.parse(source)
print(ast.dump(tree, indent=2))

cfg = CFGBuilder().build_from_file("cfg", sys.argv[1])
blocks = cfg.get_all_blocks()
for i, b in enumerate(blocks):
    print(f"block: {i}")
    for s in b.statements:
        print(s)

def check_if_secret(state: dict, statement: ast.AST):
    ast.get_docstring(statement)
    return True

def state_transformer(state: dict, statement: ast.AST) -> tuple[dict, list]: # (state, observations)
    """Takes a state, returns the next state along with all things emitted to the attacker"""
    observations = []

    if isinstance(statement, ast.Assign):
        assert len(statement.targets) == 1
        name = statement.targets[0]
        assert isinstance(name, ast.Name)
        state[name.id] = statement.value.value
    if isinstance(statement, ast.Call) and statement.func.id == "print":
        pass


    return state, observations

state = {}
for block in blocks:
    for statement in block.statements:
        state, observations = state_transformer(state, statement)


