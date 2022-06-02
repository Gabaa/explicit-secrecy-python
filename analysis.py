import ast
import enum
import sys
import uuid
from ast import (AST, Assign, BinOp, Call, Constant, Expr, If, List, Module,
                 Name, Pass, Subscript, While)
from dataclasses import dataclass
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


@dataclass
class Warning:
    statement: AST
    expr: ast.expr

    def format(self, source) -> str:
        prefix = f"Ln {self.expr.lineno}, Col {self.expr.col_offset}: "
        num_of_spaces = len(prefix) + self.expr.col_offset - \
            self.statement.col_offset
        num_of_carets = self.expr.end_col_offset - self.expr.col_offset

        return (f"\t{prefix}{ast.get_source_segment(source, self.statement)}\n" +
                "\t" + ' ' * num_of_spaces + '^' * num_of_carets)


@dataclass
class State:
    """Abstract program state.

    - public_primitive_vars: the set of variables pointing to untainted
      primitives.
    - heap_vars: a dict mapping variables to heap locations.
    - heap_locations: a dict mapping heap locations to their taint status. The
      status may be `None` if the object's taint status has not been decided
      yet, which occurs if the object's taint status depends on the variable,
      which has not been checked yet.
    - block_id: the id of the current block being
    """

    public_primitive_vars: set[str]
    heap_vars: dict[str, str]
    heap_locations: dict[str, TaintStatus | None]
    block_id: str
    next_loc: int = 0

    def get_taint_status(self, variable: str) -> TaintStatus:
        if variable in self.public_primitive_vars:
            return TaintStatus.UNTAINTED
        if variable in self.heap_vars.keys():
            return self.heap_locations[self.heap_vars[variable]]
        return TaintStatus.TAINTED

    def set_taint_status(self, variable: str, result: TaintStatus | str | None):
        # Get the previous taint status for the variable
        prev_ts = self.get_taint_status(variable)

        match result:
            case None:
                pass  # TODO: Skal vi sørge for overgang mellem heap var og prim var her?
            case TaintStatus.TAINTED if variable in self.public_primitive_vars:
                self.public_primitive_vars.remove(variable)
            case TaintStatus.UNTAINTED:
                self.public_primitive_vars.add(variable)
            case loc if type(loc) == str:
                if variable in self.public_primitive_vars:
                    self.public_primitive_vars.remove(variable)
                self.heap_vars[variable] = loc
                if self.heap_locations[loc] is None:
                    self.heap_locations[loc] = prev_ts

    def add_location(self, result: TaintStatus | None) -> str:
        """Create a new location and return the name."""
        loc = f"{self.block_id}-loc{self.next_loc}"
        self.next_loc += 1
        self.heap_locations[loc] = result
        return loc

    def get_location(self, variable: str) -> str:
        return self.heap_vars[variable]

    def update_location_taint_status(self, loc: str, ts: TaintStatus):
        self.heap_locations[loc] = ts

    def copy_for_block(self, block_id: str):
        ppv_copy = self.public_primitive_vars.copy()
        hv_copy = self.heap_vars.copy()
        hl_copy = self.heap_locations.copy()
        return State(ppv_copy, hv_copy, hl_copy, block_id)

    def join_for_block(self, other: 'State', block_id: str) -> 'State':
        """Return the conservative join of the states as a new state."""

        ppv = self.public_primitive_vars.intersection(
            other.public_primitive_vars)

        # TODO: This seems wrong! example23 may be related to this.
        hv = self.heap_vars.copy()
        hv.update(other.heap_vars)

        hl = self.heap_locations.copy()
        hl.update(other.heap_locations)

        return State(ppv, hv, hl, block_id)


def eval(expr: Expr, state: State) -> TaintStatus | str | None:
    """Evaluate the expression and return the taint status or location (or none, if the
    expression has no specific taint status associated)."""

    match expr:
        case Constant():
            return None
        case Name(id=name):
            if name in state.heap_vars:
                return state.heap_vars[name]
            return state.get_taint_status(name)
        case BinOp(left=left, right=right):
            left_ts = eval(left, state)
            right_ts = eval(right, state)
            return TaintStatus.lub(left_ts, right_ts)
        case List(elts=elts):
            ts = None
            for elt in elts:
                ts = eval(elt, state)
                if ts == TaintStatus.TAINTED:
                    ts = TaintStatus.TAINTED
                    break
            loc = state.add_location(ts)
            return loc
        case Subscript(value=Name(id=name)):
            return state.heap_locations[state.heap_vars[name]]
        case _:
            raise NotImplementedError("Evaluator", ast.dump(expr))


# detvarsaalidt
# - Bolette (02/06/2022)

def state_transformer(statement: AST, state: State) -> Optional[Warning]:
    match statement:
        case Expr(value=Constant(value=value)) if type(value) is str:
            pass  # this is likely the docstring, do nothing
        case Assign(targets=[Name(id=name)], value=value):
            result = eval(value, state)
            state.set_taint_status(name, result)
        case Assign(targets=[Subscript(value=Name(id=name))], value=value):
            result = eval(value, state)
            loc = state.get_location(name)
            state.update_location_taint_status(loc, result)
        case Expr(value=Call(func=Name(id='print'), args=[expr])):
            match eval(expr, state):
                case TaintStatus.TAINTED:
                    return Warning(statement, expr)
                case TaintStatus.UNTAINTED | None:
                    pass
                case loc:
                    if state.heap_locations[loc] == TaintStatus.TAINTED:
                        return Warning(statement, expr)

        case If() | While() | Pass():
            pass
        case _:
            raise NotImplementedError("State Transformer", ast.dump(statement))


def join_states(states: list[State], block_id: str) -> State:
    new_state = states[0].copy_for_block(block_id)

    for state in states[1:]:
        new_state = new_state.join_for_block(state, block_id)

    return new_state


def round_robin_iteration(initial_state: State, blocks: list[Block]):
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

    states = {block.id: initial_state.copy_for_block(
        str(block.id)) for block in blocks}
    changed = True

    while changed:
        changed = False

        for block in blocks:
            block_id = str(block.id)
            pred_states = [states[link.source.id]
                           for link in block.predecessors]

            if len(pred_states) == 0:
                new_state = initial_state.copy_for_block(block_id)
            else:
                new_state = join_states(pred_states, block_id)

            for statement in block.statements:
                state_transformer(statement, new_state)

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
    initial_state = State(public_variables, {}, {}, "")

    # Build the CFG
    cfg: CFG = CFGBuilder().build_from_src("cfg", source)
    if debug:
        graph = cfg.build_visual('pdf', show=False)
        graph.save('cfg.gv')

    blocks: list[Block] = cfg.get_all_blocks()
    states = round_robin_iteration(initial_state, blocks)
    if debug:
        yield 'All block exit states'
        for block_id, state in states.items():
            yield f'Block #{block_id}: {state}'

    # Run output iteration
    results = []
    for block in blocks:
        pred_states = [states[link.source.id] for link in block.predecessors]

        if len(pred_states) == 0:
            new_state = initial_state.copy_for_block(str(block.id))
        else:
            new_state = join_states(pred_states, str(block.id))

        for statement in block.statements:
            warning = state_transformer(statement, new_state)
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
