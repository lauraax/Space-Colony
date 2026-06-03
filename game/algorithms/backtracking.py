# =============================================================================
# Description: Backtracking algorithm used by the AI to plan its expansion.
#
#   The algorithm explores all valid sequences of colonisation moves and
#   selects the one that maximises total accumulated resources while
#   satisfying:
#     (a) The minimum distance constraint between same-owner colonies.
#     (b) The energy budget (deducted with each step).
#     (c) The adjacency rule (each new cell must be adjacent to the frontier).
#
#   Because brute-force backtracking is exponential, two pruning strategies
#   are applied to keep runtime acceptable on an 8×8 grid:
#     1. Candidate cells are sorted descending by resources before recursion
#        so that higher-value paths are explored first, enabling earlier
#        pruning via the best_solution upper-bound.
#     2. A depth limit (MAX_DEPTH) caps the search at a practical horizon.
#
# Pseudocode (from project report):
#   BACKTRACK(current_position, visited_cells, total_resources, energy):
#     if no more possible moves:
#       update best_solution(total_resources)
#       return
#     for each neighbor of current_position:
#       if neighbor not visited
#          and satisfies_distance(neighbor)
#          and neighbor.energy_cost <= energy:
#         mark neighbor as visited
#         BACKTRACK(neighbor, visited_cells,
#                   total_resources + neighbor.resources,
#                   energy - neighbor.energy_cost)
#         unmark neighbor
# =============================================================================

from __future__ import annotations

GRID_SIZE    = 8
MIN_DISTANCE = 2   # Minimum Manhattan distance between same-owner colonies
MAX_DEPTH    = 5   # Pruning depth limit — balances quality vs. runtime


def _manhattan(x1: int, y1: int, x2: int, y2: int) -> int:
    """
    Manhattan distance between two grid cells.

    """
    return abs(x1 - x2) + abs(y1 - y2)


def _satisfies_distance(x: int, y: int,
                         existing_colonies: list[tuple[int, int]]) -> bool:
    """
    Return True iff (x, y) is at least MIN_DISTANCE away from every colony
    in existing_colonies.

    satisfies_distance(position):
        for each colony in existing_colonies:
            if distance(position, colony) < MIN_DISTANCE:
                return false
        return true

    Parameters
    ----------
    x, y             : cell coordinates to test
    existing_colonies: list of (cx, cy) for the same owner

    """
    for (cx, cy) in existing_colonies:
        if _manhattan(x, y, cx, cy) < MIN_DISTANCE:
            return False
    return True


def _get_neighbors(x: int, y: int,
                   owner_grid: list[list[int]]) -> list[tuple[int, int]]:
    """
    Return empty cells at Manhattan distance exactly MIN_DISTANCE (2) from (x, y).
    This matches the engine's expansion rule: a new colony must be placed at
    exactly the minimum distance from the frontier, so it satisfies the distance
    constraint while staying as close as possible to expand territory.

    """
    neighbors = []
    for dy in range(-MIN_DISTANCE, MIN_DISTANCE + 1):
        for dx in range(-MIN_DISTANCE, MIN_DISTANCE + 1):
            if abs(dx) + abs(dy) == MIN_DISTANCE:  # exactly dist=2
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if owner_grid[ny][nx] == 0:
                        neighbors.append((nx, ny))
    return neighbors


def _backtrack(
    current_x:   int,
    current_y:   int,
    visited:     set[tuple[int, int]],
    total_res:   int,
    energy:      int,
    owner_grid:  list[list[int]],
    res_grid:    list[list[int]],
    colonies:    list[tuple[int, int]],  # current AI colony positions
    best:        list[int | list],       # best[0]=score, best[1]=sequence
    sequence:    list[tuple[int, int]],  # current path
    depth:       int,
) -> None:
    """
    Recursive backtracking helper.

    Explores all valid next steps from (current_x, current_y), updating
    best whenever a terminal or leaf state exceeds the previous best.

    Parameters
    ----------
    current_x, current_y : current frontier cell
    visited  : set of cells already placed in this path
    total_res: accumulated resources so far
    energy   : remaining energy budget
    owner_grid : 0=empty, 1=player, 2=ai (current board state, NOT mutated)
    res_grid : resource value per cell
    colonies : AI colony positions used for distance checks
    best     : mutable list [best_score, best_sequence] — updated in place
    sequence : current colonisation path
    depth    : recursion depth counter (pruning)

    """
    # ---- Update best solution if current path is better ----
    if total_res > best[0]:
        best[0] = total_res
        best[1] = list(sequence)

    # ---- Base case: depth limit reached ----
    if depth >= MAX_DEPTH:
        return

    # ---- Gather valid neighbours and sort descending by resources ----
    # Sorting is a greedy pruning heuristic: by exploring high-value cells
    # first we tend to find good solutions early, which then prune
    # less-promising branches faster.
    neighbors = _get_neighbors(current_x, current_y, owner_grid)
    neighbors.sort(key=lambda pos: res_grid[pos[1]][pos[0]], reverse=True)

    for (nx, ny) in neighbors:
        if (nx, ny) in visited:
            continue

        res  = res_grid[ny][nx]
        cost = max(1, res // 10)

        # Energy constraint
        if cost > energy:
            continue

        # Distance constraint from all current AI colonies on the path
        all_colonies = colonies + list(visited)
        if not _satisfies_distance(nx, ny, all_colonies):
            continue

        # ---- Recurse ----
        visited.add((nx, ny))
        sequence.append((nx, ny))

        _backtrack(
            nx, ny,
            visited,
            total_res + res,
            energy - cost,
            owner_grid,
            res_grid,
            colonies,
            best,
            sequence,
            depth + 1,
        )

        # ---- Undo (backtrack) ----
        visited.discard((nx, ny))
        sequence.pop()


def backtrack_best_expansion(state: dict) -> list[tuple[int, int]]:
    """
    Entry point: compute the best expansion sequence for the AI using
    backtracking, then return the first cell of that sequence.

    The function is called once per AI turn; only the *first* cell of the
    best path is returned (the engine only processes one action per turn).

    Parameters
    ----------
    state : dict
        Full game state from bridge.read_state(). Required keys:
            'grid'       : list[list[int]] — resource values
            'owner_grid' : list[list[int]] — 0=empty, 1=player, 2=ai
            'ai_energy'  : int
            'colonies'   : list of colony dicts

    Returns
    -------
    list of (x, y) tuples representing the best expansion sequence found,
    or an empty list if no valid move exists.

    """
    grid_res   = state["grid"]
    owner_grid = state["owner_grid"]
    ai_energy  = state["ai_energy"]

    # Collect current AI colony positions
    ai_colonies = [
        (c, r)
        for r in range(GRID_SIZE)
        for c in range(GRID_SIZE)
        if owner_grid[r][c] == 2
    ]

    # If AI has no colonies yet, find the globally best empty cell
    if not ai_colonies:
        best_res  = -1
        best_cell = None
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if owner_grid[r][c] == 0 and grid_res[r][c] > best_res:
                    best_res  = grid_res[r][c]
                    best_cell = (c, r)
        return [best_cell] if best_cell else []

    # Run backtracking from every existing AI colony as a starting frontier
    global_best = [0, []]

    for (sx, sy) in ai_colonies:
        best  = [0, []]
        visited = {(sx, sy)}   # treat starting colony as visited (already placed)
        sequence: list[tuple[int, int]] = []

        _backtrack(
            sx, sy,
            visited,
            0,           # total_res starts at 0 for this path
            ai_energy,
            owner_grid,
            grid_res,
            ai_colonies,
            best,
            sequence,
            0,
        )

        if best[0] > global_best[0]:
            global_best = best

    return global_best[1]


def get_best_ai_move(state: dict) -> dict | None:
    """
    Public API: returns the single best expansion cell for the AI this turn.

    Calls backtrack_best_expansion and returns the first cell of the best
    sequence as a dict suitable for writing to input.json.

    Parameters
    ----------
    state : dict
        Full game state.

    Returns
    -------
    dict | None
        {'x': int, 'y': int, 'resources': int, 'energy_cost': int}
        or None if no valid move exists.
    """
    sequence = backtrack_best_expansion(state)
    if not sequence:
        return None

    first_x, first_y = sequence[0]
    res  = state["grid"][first_y][first_x]
    cost = max(1, res // 10)
    return {
        "x": first_x,
        "y": first_y,
        "resources": res,
        "energy_cost": cost,
    }
