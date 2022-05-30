import ast
import enum
import sys
from ast import (AST, Assign, Attribute, BinOp, Call, Constant, Expr, If,
                 Import, Name, Pass, While, alias)
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


State = dict[str, TaintStatus]


def evaluate_taint_status(expr: Expr, state: State) -> TaintStatus:
    match expr:
        case Constant():
            return TaintStatus.TAINTED
        case Name(id=name):
            return state[name]
        case Call(func=Attribute(value=Name(id='expsec'), attr='Public')):
            return TaintStatus.UNTAINTED
        case BinOp(left=left, right=right):
            return TaintStatus.lub(evaluate_taint_status(left, state), evaluate_taint_status(right, state))
        case _:
            raise NotImplementedError("Evaluator", ast.dump(expr))


def state_transformer(statement: AST, state: State) -> tuple[State, Optional[Warning]]:
    state = state.copy()
    warning = None

    match statement:
        case Expr(value=value):
            state, warning = state_transformer(value, state)
        case Assign(targets=[Name(id=name)], value=value):
            state[name] = evaluate_taint_status(value, state)
        case Call(func=Name(id='print'), args=[expr]):
            match evaluate_taint_status(expr, state):
                case TaintStatus.TAINTED:
                    warning = Warning(statement, expr)
                case TaintStatus.UNTAINTED:
                    pass
        case Call(func=Attribute(value=Name(id='expsec'), attr='declassify'), args=[Name(id=name)]):
            state[name] = TaintStatus.UNTAINTED
        case Import(names=[alias(name='expsec')]):
            pass
        case If() | While() | Pass():
            pass
        case _:
            raise NotImplementedError("State Transformer", ast.dump(statement))

    return state, warning


def join_states(states: list[State]) -> State:
    new_state = {}

    for state in states:
        for k, v in state.items():
            status = v if k not in new_state else TaintStatus.lub(
                new_state[k], v)
            new_state[k] = status

    return new_state


def round_robin_iteration(blocks: list[Block]):
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

    states = {block.id: {} for block in blocks}
    changed = True

    while changed:
        changed = False

        for block in blocks:
            state = states[block.id]
            pred_states = [states[link.source.id]
                           for link in block.predecessors]
            new_state = join_states(pred_states)
            for statement in block.statements:
                new_state, _ = state_transformer(statement, new_state)
            if state != new_state:
                changed = True
            states[block.id] = new_state

    return states


def run_analysis(file_name: str, debug: bool) -> Generator[str, None, None]:
    with open(file_name, 'r') as f:
        source = f.read()

    # Show the full AST
    if debug:
        tree = ast.parse(source)
        yield ast.dump(tree, indent=2)

    # Build the CFG
    cfg: CFG = CFGBuilder().build_from_src("cfg", source)
    if debug:
        graph = cfg.build_visual('pdf', show=False)
        graph.save('cfg.gv')

    blocks: list[Block] = cfg.get_all_blocks()
    states = round_robin_iteration(blocks)
    if debug:
        yield 'All block exit states'
        for block_id, state in states.items():
            yield f'Block #{block_id}: {state}'

    # Run output iteration
    results = []
    for block in blocks:
        pred_states = [states[link.source.id] for link in block.predecessors]
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
