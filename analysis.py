import ast
import enum
import sys
from ast import (AST, Assign, Attribute, BinOp, Call, Constant, Expr, If,
                 Import, List, Module, Name, Pass, Subscript, While, alias)
from typing import Generator, Optional

from scalpel.cfg import CFG, Block, CFGBuilder


class TaintStatus(enum.Enum):
    TAINTED = 1
    UNTAINTED = 2

    @classmethod
    def lub(cls, left: 'TaintStatus', right: 'TaintStatus') -> 'TaintStatus':
        if cls.TAINTED in [left, right]:
            return cls.TAINTED
        return cls.UNTAINTED


class Warning:
    def __init__(self, statement, expr):
        self.statement = statement
        self.expr = expr

    def format(self, source) -> str:
        line_no = f"Ln {self.expr.lineno}, Col {self.expr.col_offset}"

        return (
            f"\t{line_no}: {ast.get_source_segment(source, self.statement)}\n" +
            "\t" + ' ' * (len(line_no) + 2 + self.expr.col_offset - self.statement.col_offset) +
            '^' * (self.expr.end_col_offset - self.expr.col_offset)
        )


class State:
    public: set[str]

    def __init__(self, public: set[str]):
        self.public = public

    def __str__(self) -> str:
        return f"State(public={self.public})"

    def __eq__(self, other: 'State') -> bool:
        return self.public == other.public

    def get_taint_status(self, variable: str) -> TaintStatus:
        if variable in self.public:
            return TaintStatus.UNTAINTED
        return TaintStatus.TAINTED

    def set_taint_status(self, variable: str, ts: TaintStatus):
        match ts:
            case TaintStatus.TAINTED if variable in self.public:
                self.public.remove(variable)
            case TaintStatus.UNTAINTED:
                self.public.add(variable)

    def copy(self):
        return State(self.public.copy())


def evaluate_taint_status(expr: Expr, state: State) -> TaintStatus | None:
    """Evaluate the expression and return the taint status (or none, if the
    expression has no specific taint status)."""

    match expr:
        case Constant():
            return None
        case Name(id=name):
            return state.get_taint_status(name)
        case BinOp(left=left, right=right):
            return TaintStatus.lub(evaluate_taint_status(left, state), evaluate_taint_status(right, state))
        case List(elts=elts):
            for elt in elts:
                ts = evaluate_taint_status(elt, state)
                if ts == TaintStatus.TAINTED:
                    return TaintStatus.TAINTED
            return None  # elements are all untainted or neutral
        case _:
            raise NotImplementedError("Evaluator", ast.dump(expr))


# detvarsaalidt
# - Bolette (02/06/2022)

def state_transformer(statement: AST, state: State) -> tuple[State, Optional[Warning]]:
    state = state.copy()
    warning = None

    match statement:
        case Expr(value=Constant(value=value)) if type(value) is str:
            pass  # this is just a docstring
        case Expr(value=value):
            state, warning = state_transformer(value, state)
        case Assign(targets=[Name(id=name)], value=value):
            ts = evaluate_taint_status(value, state)
            state.set_taint_status(name, ts)
        case Assign(targets=[Subscript(value=Name(id=name), slice=Constant(value=index))], value=value):
            ts = evaluate_taint_status(value, state)
            state.set_taint_status(name, ts)
        case Call(func=Name(id='print'), args=[expr]):
            match evaluate_taint_status(expr, state):
                case TaintStatus.TAINTED:
                    warning = Warning(statement, expr)
                case TaintStatus.UNTAINTED | None:
                    pass
        case If() | While() | Pass():
            pass
        case _:
            raise NotImplementedError("State Transformer", ast.dump(statement))

    return state, warning


def join_states(states: list[State]) -> State:
    new_state = states[0].copy()

    for state in states[1:]:
        new_state.public.intersection_update(state.public)

    return new_state


def round_robin_iteration(public_variables: set[str], blocks: list[Block]):
    """
    procedure RoundRobin(f1, . . . , fn)
        (x1, . . . , xn) := (⊥, . . . , ⊥)
        while (x1, . . . , xn) != f (x1, . . . , xn) do
            for i := 1 . . . n do
                xi := fi(x1, . . . , xn)
            end for
        end while
        return (x1, . . . , xn)
    end procedure
    """

    states = {block.id: State(public_variables.copy()) for block in blocks}
    changed = True

    while changed:
        changed = False

        for block in blocks:
            pred_states = [states[link.source.id]
                           for link in block.predecessors]

            if len(pred_states) == 0:
                new_state = State(public_variables)
            else:
                new_state = join_states(pred_states)

            for statement in block.statements:
                new_state, _ = state_transformer(statement, new_state)
            if states[block.id] != new_state:
                changed = True
            states[block.id] = new_state

    return states


def get_public_variables_from_docstring(tree: Module) -> set[str]:
    ds = ast.get_docstring(tree)

    if ds is None:
        return set()

    for line in ds.split('\n'):
        if line.startswith('expsec_public:'):
            vars = line[14:].strip().split(', ')
            return set(vars)


def run_analysis(file_name: str, debug: bool) -> Generator[str, None, None]:
    with open(file_name, 'r') as f:
        source = f.read()

    # Show the full AST
    tree = ast.parse(source)
    if debug:
        yield ast.dump(tree, indent=2)

    public_variables = get_public_variables_from_docstring(tree)

    # Build the CFG
    cfg: CFG = CFGBuilder().build_from_src("cfg", source)
    if debug:
        graph = cfg.build_visual('pdf', show=False)
        graph.save('cfg.gv')

    blocks: list[Block] = cfg.get_all_blocks()
    states = round_robin_iteration(public_variables, blocks)
    if debug:
        yield 'All block exit states'
        for block_id, state in states.items():
            yield f'Block #{block_id}: {state}'

    # Run output iteration
    results = []
    for block in blocks:
        pred_states = [states[link.source.id] for link in block.predecessors]

        if len(pred_states) == 0:
            new_state = State(public_variables)
        else:
            new_state = join_states(pred_states)

        for statement in block.statements:
            new_state, warning = state_transformer(statement, new_state)
            if warning != None:
                results.append(warning.format(source))

    if len(results) > 0:
        yield f"Found the following tainted outputs in {file_name}:"
    for result in results:
        yield result


def main():
    output_generator = run_analysis(sys.argv[1], '--debug' in sys.argv)
    for output in output_generator:
        print(output)


if __name__ == '__main__':
    main()
