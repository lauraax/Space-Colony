# =============================================================================
# Team 14: Laura Paez, Nicolas Acero, Erik Fernandez
# Variant: Space Colony 
# Description: Greedy algorithms used by the AI opponent.
#   - greedy_select_move : expansion phase  — pick the highest-resource empty
#                          cell adjacent to the AI's existing colonies.
#   - greedy_attack      : combat phase     — pick the weakest adjacent enemy
#                          cell to maximise capture probability.
#
# Complexity analysis is provided as inline comments for each function.
# =============================================================================

import math


def greedy_select_move(available_cells: list[dict], energy: int) -> dict | None:
    """
    Greedy expansion: select the affordable cell with the most resources.

    Follows GREEDY_SELECT_MOVE pseudocode from the project report exactly:
        best_cell  <- null
        max_value  <- -∞
        for each cell in available_cells:
            if cell.energy_cost <= energy:
                value <- cell.resources
                if value > max_value:
                    max_value <- value
                    best_cell <- cell
        return best_cell

    Parameters
    ----------
    available_cells : list of dict
        Each dict must have keys:
            'x'           (int) column
            'y'           (int) row
            'resources'   (int) resource value of the cell
            'energy_cost' (int) energy required to colonise
    energy : int
        Current available energy of the AI.

    Returns
    -------
    dict | None
        The best cell dict, or None if no affordable cell exists.

    Complexity
    ----------
    Time  : O(n) — single pass through available_cells of length n.
    Space : O(1) — only two scalar variables are kept (best_cell, max_value).
    """
    best_cell = None
    max_value = -math.inf

    for cell in available_cells:
        if cell["energy_cost"] <= energy:
            value = cell["resources"]
            if value > max_value:
                max_value = value
                best_cell = cell

    return best_cell


def greedy_attack(neighbor_enemy_cells: list[dict]) -> dict | None:
    """
    Greedy combat: select the enemy cell with the lowest defense (resources).

    Follows GREEDY_ATTACK pseudocode from the project report exactly:
        target         <- null
        lowest_defense <- +∞
        for each cell in neighbor_enemy_cells:
            defense <- cell.resources
            if defense < lowest_defense:
                lowest_defense <- defense
                target         <- cell
        return target

    Attacking the weakest cell maximises the probability that the attacker's
    power (resources + dice) exceeds the defender's power.

    Parameters
    ----------
    neighbor_enemy_cells : list of dict
        Each dict must have keys:
            'x'         (int) column
            'y'         (int) row
            'resources' (int) resource / defense value
            'origin_x'  (int) attacking colony column
            'origin_y'  (int) attacking colony row

    Returns
    -------
    dict | None
        The weakest enemy cell dict, or None if the list is empty.

    """
    target         = None
    lowest_defense = math.inf

    for cell in neighbor_enemy_cells:
        defense = cell["resources"]
        if defense < lowest_defense:
            lowest_defense = defense
            target         = cell

    return target


def get_ai_expansion_candidates(state: dict) -> list[dict]:
    """
    Build the list of valid expansion candidates for the AI.

    A cell is a candidate if:
      1. It is currently empty (owner_grid value == 0).
      2. It is 4-directionally adjacent to at least one AI colony.
      3. Its Manhattan distance to every existing AI colony is >= MIN_DISTANCE (2).
      4. Its energy cost <= ai_energy.

    Parameters
    ----------
    state : dict
        Full game state as returned by bridge.read_state().

    Returns
    -------
    list of dict
        List of candidate cells with keys x, y, resources, energy_cost.

    """
    GRID_SIZE    = 8
    MIN_DISTANCE = 2
    grid         = state["grid"]         # resource values (original)
    owner_grid   = state["owner_grid"]   # 0=empty, 1=player, 2=ai
    ai_energy    = state["ai_energy"]

    # Collect current AI colony positions
    ai_colonies = [
        (c, r)
        for r in range(GRID_SIZE)
        for c in range(GRID_SIZE)
        if owner_grid[r][c] == 2
    ]

    # Check adjacency to ANY occupied cell within MIN_DISTANCE steps
    def is_adjacent_to_any(x: int, y: int) -> bool:
        for r2 in range(GRID_SIZE):
            for c2 in range(GRID_SIZE):
                if owner_grid[r2][c2] != 0:
                    if abs(x - c2) + abs(y - r2) <= MIN_DISTANCE:
                        return True
        return False

    # Check minimum distance from all AI colonies
    def satisfies_distance(x: int, y: int) -> bool:
        for (cx, cy) in ai_colonies:
            if abs(x - cx) + abs(y - cy) < MIN_DISTANCE:
                return False
        return True

    candidates = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if owner_grid[r][c] != 0:
                continue  # occupied
            if ai_colonies and not is_adjacent_to_any(c, r):
                continue  # not adjacent (unless first placement)
            if not satisfies_distance(c, r):
                continue  # too close to own colony
            res  = grid[r][c]
            cost = max(1, res // 10)
            if cost > ai_energy:
                continue  # not affordable
            candidates.append({
                "x": c, "y": r,
                "resources": res,
                "energy_cost": cost,
            })

    return candidates


def get_ai_attack_candidates(state: dict) -> list[dict]:
    """
    Build the list of valid attack targets for the AI in combat phase.

    A pair (origin, target) is valid if:
      1. origin is an AI colony.
      2. target is an adjacent (Manhattan distance == 1) player colony.

    Returns a flat list where each entry includes both origin and target info,
    so that greedy_attack can be called on this list directly.

    Parameters
    ----------
    state : dict
        Full game state.

    Returns
    -------
    list of dict
        Each dict: x, y, resources, origin_x, origin_y.

    """
    GRID_SIZE    = 8
    owner_grid   = state["owner_grid"]
    resource_grid_map = {}
    for col in state.get("colonies", []):
        resource_grid_map[(col["x"], col["y"])] = col["resources"]

    candidates = []
    dx_list = [0, 0, 1, -1]
    dy_list = [1, -1, 0, 0]

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if owner_grid[r][c] != 2:
                continue  # not an AI colony
            origin_resources = resource_grid_map.get((c, r), 0)
            for d in range(4):
                nx = c + dx_list[d]
                ny = r + dy_list[d]
                if nx < 0 or nx >= GRID_SIZE or ny < 0 or ny >= GRID_SIZE:
                    continue
                if owner_grid[ny][nx] == 1:  # player cell
                    target_res = resource_grid_map.get((nx, ny), 0)
                    candidates.append({
                        "x": nx, "y": ny,
                        "resources": target_res,
                        "origin_x": c,
                        "origin_y": r,
                        "origin_resources": origin_resources,
                    })

    return candidates
