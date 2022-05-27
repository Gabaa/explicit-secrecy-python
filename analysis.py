import ast
import enum
import sys
from ast import (AST, Assign, Attribute, BinOp, Call, Constant, Expr, If, Import,
                 Name, Pass, While, alias)
from regex import P

from scalpel.cfg import CFG, Block, CFGBuilder


class TaintStatus(enum.Enum):
    TAINTED = 1
    UNTAINTED = 2

    @classmethod
    def lub(cls, left: 'TaintStatus', right: 'TaintStatus') -> 'TaintStatus':
        if cls.TAINTED in [left, right]:
            return cls.TAINTED
        return cls.UNTAINTED


State = dict[str, TaintStatus]

SOURCE = None


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


def display_warning(statement, expr):
    line_no = f"Ln {expr.lineno}, Col {expr.col_offset}"
    print(f"\t{line_no}: {ast.get_source_segment(SOURCE, statement)}")
    print("\t" + ' ' * (len(line_no) + 2 + expr.col_offset - statement.col_offset) +
          '^' * (expr.end_col_offset - expr.col_offset))


def state_transformer(statement: AST, state: State, verbose: bool = True) -> State:
    state = state.copy()

    match statement:
        case Expr(value=value):
            state = state_transformer(value, state, verbose=verbose)
        case Assign(targets=[Name(id=name)], value=value):
            state[name] = evaluate_taint_status(value, state)
        case Call(func=Name(id='print'), args=[expr]):
            match evaluate_taint_status(expr, state):
                case TaintStatus.TAINTED:
                    if verbose:
                        display_warning(statement, expr)
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

    return state


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
                new_state = state_transformer(
                    statement, new_state, verbose=False)
            if state != new_state:
                changed = True
            states[block.id] = new_state

    return states


def main():
    global SOURCE
    with open(sys.argv[1], 'r') as f:
        SOURCE = f.read()

    debug = False
    if '--debug' in sys.argv:
        debug = True

    # Show the full AST
    if debug:
        tree = ast.parse(SOURCE)
        print(ast.dump(tree, indent=2))

    # Build the CFG
    cfg: CFG = CFGBuilder().build_from_src("cfg", SOURCE)
    if debug:
        graph = cfg.build_visual('pdf', show=False)
        graph.save('cfg.gv')

    blocks: list[Block] = cfg.get_all_blocks()
    states = round_robin_iteration(blocks)
    if debug:
        print('All block exit states')
        for block_id, state in states.items():
            print(f'Block #{block_id}: {state}')

    # Run output iteration
    print("Found the following tainted outputs:")
    for block in blocks:
        pred_states = [states[link.source.id] for link in block.predecessors]
        new_state = join_states(pred_states)
        for statement in block.statements:
            new_state = state_transformer(statement, new_state)


if __name__ == '__main__':
    main()
