
// Main file for the C++ game engine.
// It reads input.json from Python, runs one game action,
// and writes state.json so Python can draw the board.
//   - Writes state.json (read by Python / bridge.py for rendering)
//
// JSON is handled with the nlohmann/json header.
// The board, turns, phase, and energy are managed here.
//
// Usage: ./engine <data_dir>
// If no folder is given, it uses "../data".
// =============================================================================
 
#include "linked_list.h"
#include "tree.h"
 
// nlohmann/json is a header-only library placed next to this file.
// Download: https://github.com/nlohmann/json/releases
#include "json.hpp"
 
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <cstdlib>    // rand, srand
#include <ctime>      // time
#include <cmath>      // abs
#include <algorithm>  // std::max, std::min
#include <chrono>     // high_resolution_clock
 
using json = nlohmann::json;
 

// Constants

static const int GRID_SIZE        = 8;
static const int INITIAL_ENERGY   = 150;
static const int MAX_TURNS        = 200;  // enough turns for expansion before combat
static const int MIN_DISTANCE     = 2;    // Manhattan distance between own colonies
static const int RESOURCE_MIN     = 1;
static const int RESOURCE_MAX     = 100;
 
// Energy cost is resources / 10, but never less than 1.
static int energy_cost_of(int resources) {
    int cost = resources / 10;
    return (cost < 1) ? 1 : cost;
}
 
// =============================================================================
// Game state
// =============================================================================
struct GameState {
    int  grid[GRID_SIZE][GRID_SIZE];     // Resources in each cell (0 = occupied)
    int  owner_grid[GRID_SIZE][GRID_SIZE]; // 0=empty, 1=player, 2=ai
    int  resource_grid[GRID_SIZE][GRID_SIZE]; // Resources of the colony in the cell
    std::string phase;          // "expansion" or "combat"
    std::string turn;           // "player" or "ai"
    int  player_energy;
    int  ai_energy;
    int  player_total_resources;
    int  ai_total_resources;
    int  current_turn;
    int  max_turns;
    bool game_over;
    std::string winner;         // "player", "ai", or "draw"
    int  consecutive_passes;    // counts passes in a row to force combat
};
 
// =============================================================================
// Get the Manhattan distance between two cells.
// =============================================================================
static int manhattan_distance(int x1, int y1, int x2, int y2) {
    return std::abs(x1 - x2) + std::abs(y1 - y2);
}
 
// =============================================================================
// Check if a new colony keeps enough distance from the owner's other colonies.
// =============================================================================
static bool satisfies_distance(int x, int y, const std::string& owner,
                                const LinkedList& history) {
    const Node* current = history.get_head();
    while (current != nullptr) {
        if (current->owner == owner) {
            if (manhattan_distance(x, y, current->x, current->y) < MIN_DISTANCE) {
                return false;
            }
        }
        current = current->next;
    }
    return true;
}
 
// =============================================================================
// Check if (x,y) is close enough to any occupied cell.
// Reach uses Manhattan distance <= MIN_DISTANCE.
// This lets a player place a colony exactly MIN_DISTANCE cells away
// from an existing one, while still respecting the distance rule.
// =============================================================================
// =============================================================================
static bool is_adjacent_to_any(int x, int y, const GameState& state) {
    for (int r = 0; r < GRID_SIZE; ++r)
        for (int c = 0; c < GRID_SIZE; ++c)
            if (state.owner_grid[r][c] != 0 &&
                manhattan_distance(x, y, c, r) <= MIN_DISTANCE)
                return true;
    return false;
}
 
// =============================================================================
// Check if (x,y) is inside the board.
// =============================================================================
static bool in_bounds(int x, int y) {
    return x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE;
}
 
// =============================================================================
// Count how many cells belong to one owner.
// =============================================================================
static int count_cells(const GameState& state, int owner_id) {
    int count = 0;
    for (int r = 0; r < GRID_SIZE; ++r)
        for (int c = 0; c < GRID_SIZE; ++c)
            if (state.owner_grid[r][c] == owner_id) ++count;
    return count;
}
 
// =============================================================================
// Check if the whole board is occupied.
// =============================================================================
static bool grid_full(const GameState& state) {
    for (int r = 0; r < GRID_SIZE; ++r)
        for (int c = 0; c < GRID_SIZE; ++c)
            if (state.owner_grid[r][c] == 0) return false;
    return true;
}
 
// =============================================================================
// Check if a player can still expand.
// A valid cell must be empty, reachable, affordable, and not too close.
// =============================================================================
static bool has_expansion_moves(const std::string& owner, const GameState& state,
                                  const LinkedList& history, int energy) {
    for (int r = 0; r < GRID_SIZE; ++r) {
        for (int c = 0; c < GRID_SIZE; ++c) {
            if (state.owner_grid[r][c] != 0) continue;
            // The first colony for an owner can be placed on any empty cell.
            bool has_any = false;
            const Node* cur = history.get_head();
            while (cur) { if (cur->owner == owner) { has_any = true; break; } cur = cur->next; }
            if (has_any && !is_adjacent_to_any(c, r, state)) continue;
            int res = state.grid[r][c];
            int cost = energy_cost_of(res);
            if (cost > energy) continue;
            if (!satisfies_distance(c, r, owner, history)) continue;
            return true;
        }
    }
    return false;
}
 
// =============================================================================
// Start a new game with random resources on the board.
// =============================================================================
static GameState init_game() {
    GameState gs;
    srand(static_cast<unsigned int>(time(nullptr)));
 
    for (int r = 0; r < GRID_SIZE; ++r) {
        for (int c = 0; c < GRID_SIZE; ++c) {
            gs.grid[r][c]          = RESOURCE_MIN + rand() % (RESOURCE_MAX - RESOURCE_MIN + 1);
            gs.owner_grid[r][c]    = 0;
            gs.resource_grid[r][c] = 0;
        }
    }
 
    gs.phase                 = "expansion";
    gs.turn                  = "player";
    gs.player_energy         = INITIAL_ENERGY;
    gs.ai_energy             = INITIAL_ENERGY;
    gs.player_total_resources = 0;
    gs.ai_total_resources     = 0;
    gs.current_turn          = 1;
    gs.max_turns             = MAX_TURNS;
    gs.game_over             = false;
    gs.winner                = "";
    gs.consecutive_passes    = 0;
    return gs;
}
 
// =============================================================================
// Convert the game state and colony history into the state.json format.
// =============================================================================
static json state_to_json(const GameState& gs, const LinkedList& history,
                           const std::string& last_result = "") {
    json j;
    j["phase"]                  = gs.phase;
    j["turn"]                   = gs.turn;
    j["player_total_resources"] = gs.player_total_resources;
    j["ai_total_resources"]     = gs.ai_total_resources;
    j["player_energy"]          = gs.player_energy;
    j["ai_energy"]              = gs.ai_energy;
    j["current_turn"]           = gs.current_turn;
    j["max_turns"]              = gs.max_turns;
    j["game_over"]              = gs.game_over;
    j["winner"]                 = gs.winner;
    j["consecutive_passes"]     = gs.consecutive_passes;
    j["last_result"]            = last_result;
 
    // Board resources.
    json grid_arr = json::array();
    for (int r = 0; r < GRID_SIZE; ++r) {
        json row = json::array();
        for (int c = 0; c < GRID_SIZE; ++c) {
            row.push_back(gs.grid[r][c]);
        }
        grid_arr.push_back(row);
    }
    j["grid"] = grid_arr;
 
    // Cell owners: 0 = empty, 1 = player, 2 = ai.
    json owner_arr = json::array();
    for (int r = 0; r < GRID_SIZE; ++r) {
        json row = json::array();
        for (int c = 0; c < GRID_SIZE; ++c) {
            row.push_back(gs.owner_grid[r][c]);
        }
        owner_arr.push_back(row);
    }
    j["owner_grid"] = owner_arr;
 
    // Save the colonies from the linked list.
    json colonies = json::array();
    const Node* curr = history.get_head();
    while (curr != nullptr) {
        json col;
        col["x"]         = curr->x;
        col["y"]         = curr->y;
        col["owner"]     = curr->owner;
        col["resources"] = curr->resources;
        col["defense"]   = curr->resources;  // defense uses the resource value
        colonies.push_back(col);
        curr = curr->next;
    }
    j["colonies"] = colonies;
 
    return j;
}
 
// =============================================================================
// Write JSON to a file.
// This writes directly because rename can fail on Windows if the file exists.
// =============================================================================
static bool write_json(const std::string& path, const json& j) {
    // Write directly and replace the old content.

    std::ofstream out(path, std::ios::out | std::ios::trunc);
    if (!out.is_open()) {
        std::cerr << "[engine] ERROR: cannot open " << path << "\n";
        return false;
    }
    out << j.dump(2);
    out.close();
    return true;
}
 
// =============================================================================
// Read JSON from a file.
// =============================================================================
static bool read_json(const std::string& path, json& out) {
    std::ifstream in(path);
    if (!in.is_open()) {
        std::cerr << "[engine] ERROR: cannot open " << path << "\n";
        return false;
    }
    try {
        in >> out;
    } catch (const json::parse_error& e) {
        std::cerr << "[engine] JSON parse error: " << e.what() << "\n";
        return false;
    }
    return true;
}
 
// =============================================================================
// Colonize action for the player or the AI during expansion.
// Returns an empty string on success, or an error message.
// =============================================================================
static std::string action_colonize(int dest_x, int dest_y,
                                    const std::string& owner,
                                    GameState& gs,
                                    LinkedList& history,
                                    AVLTree& tree) {
    // Destination must be inside the board.
    if (!in_bounds(dest_x, dest_y))
        return "destination out of bounds";
 
    // Destination must be empty.
    if (gs.owner_grid[dest_y][dest_x] != 0)
        return "cell already occupied";
 
    int res  = gs.grid[dest_y][dest_x];
    int cost = energy_cost_of(res);
 
    // Owner must have enough energy.
    int& energy = (owner == "player") ? gs.player_energy : gs.ai_energy;
    if (cost > energy)
        return "not enough energy";
 
    // After the first colony, new colonies must be near occupied cells.
    bool has_any = false;
    const Node* curr = history.get_head();
    while (curr) {
        if (curr->owner == owner) { has_any = true; break; }
        curr = curr->next;
    }
    if (has_any && !is_adjacent_to_any(dest_x, dest_y, gs))
        return "destination not adjacent to any occupied cell";
 
    // New colony cannot be too close to another colony from the same owner.
    if (!satisfies_distance(dest_x, dest_y, owner, history))
        return "too close to another of your own colonies (min distance = 2)";
 
    // All checks passed, so apply the action.
    int owner_id = (owner == "player") ? 1 : 2;
    gs.owner_grid[dest_y][dest_x]    = owner_id;
    gs.resource_grid[dest_y][dest_x] = res;
    gs.grid[dest_y][dest_x]          = res;   // keep value visible for display
    energy -= cost;
 
    if (owner == "player") gs.player_total_resources += res;
    else                    gs.ai_total_resources     += res;
 
    history.append(dest_x, dest_y, owner, res);
    tree.insert(res, cost, dest_x, dest_y, owner);
 
    return "";  // success
}
 
// =============================================================================
// Attack action during combat.
// The origin must be owned by the attacker, and the destination by the enemy.
// Combat power is resources + a random number from 1 to 6.
// Returns "attacker_wins" or "defender_wins".
// =============================================================================
static std::string action_attack(int orig_x, int orig_y,
                                  int dest_x, int dest_y,
                                  const std::string& owner,
                                  GameState& gs,
                                  LinkedList& history,
                                  AVLTree& tree) {
    int owner_id    = (owner == "player") ? 1 : 2;
    int enemy_id    = (owner == "player") ? 2 : 1;
    std::string enemy = (owner == "player") ? "ai" : "player";
 
    // Origin must belong to the current owner.
    if (!in_bounds(orig_x, orig_y) || gs.owner_grid[orig_y][orig_x] != owner_id)
        return "invalid origin: must be your own colony";
 
    // Destination must belong to the enemy.
    if (!in_bounds(dest_x, dest_y) || gs.owner_grid[dest_y][dest_x] != enemy_id)
        return "invalid destination: must be an enemy colony";
 
    // Attacks only work on directly adjacent cells.
    if (manhattan_distance(orig_x, orig_y, dest_x, dest_y) != 1)
        return "can only attack directly adjacent cells";
 
    int atk_resources = gs.resource_grid[orig_y][orig_x];
    int def_resources = gs.resource_grid[dest_y][dest_x];
 
    int atk_power = atk_resources + (1 + rand() % 6);
    int def_power = def_resources + (1 + rand() % 6);
 
    std::string result;
    if (atk_power > def_power) {
        // Attacker wins and captures the cell.
        result = "attacker_wins";
 
        // Remove the defender from the AVL tree.
        tree.remove(def_resources, dest_x, dest_y);
        // Remove defender resources from the old owner.
        if (enemy == "player") gs.player_total_resources -= def_resources;
        else                    gs.ai_total_resources     -= def_resources;
 
        // Transfer the cell to the attacker.
        gs.owner_grid[dest_y][dest_x]    = owner_id;
        gs.resource_grid[dest_y][dest_x] = def_resources; // keep captured cell value

        // Add the captured cell to the attacker's AVL entries.
        tree.insert(def_resources, energy_cost_of(def_resources),
                    dest_x, dest_y, owner);
 
        // Add captured resources to the attacker.
        if (owner == "player") gs.player_total_resources += def_resources;
        else                    gs.ai_total_resources     += def_resources;
 
        // Save the capture in history.
        history.append(dest_x, dest_y, owner, def_resources);
 
    } else {
        result = "defender_wins";
        // Defender wins, so the board stays the same.
    }
 
    // Add the combat numbers to the result text.
    result += " (atk=" + std::to_string(atk_power) +
              " vs def=" + std::to_string(def_power) + ")";
    return result;
}
 
// =============================================================================
// Decide the winner when the game ends.
// =============================================================================
static std::string determine_winner(const GameState& gs) {
    if (gs.player_total_resources > gs.ai_total_resources) return "player";
    if (gs.ai_total_resources > gs.player_total_resources) return "ai";
    return "draw";
}
 
// =============================================================================
// Main game loop. Each run processes one action.
// =============================================================================
int main(int argc, char* argv[]) {
    srand(static_cast<unsigned int>(
        std::chrono::high_resolution_clock::now().time_since_epoch().count()
    ));

    std::string data_dir = (argc > 1) ? std::string(argv[1]) : "../data";
    std::string input_path = data_dir + "/input.json";
    std::string state_path = data_dir + "/state.json";
 
    // ------------------------------------------------------------------
    // The game state is saved in state.json between turns.
    // If there is no saved game, or the phase is "init", start fresh.
    // ------------------------------------------------------------------
    json state_j;
    GameState gs;
    LinkedList history;
    AVLTree    tree;
 
    bool state_exists = read_json(state_path, state_j);
 
    if (!state_exists || state_j.value("phase", "init") == "init") {
        // Start a fresh game.
        gs = init_game();
        std::cout << "[engine] New game initialised.\n";
        write_json(state_path, state_to_json(gs, history));
        return 0;
    }
 
    // ------------------------------------------------------------------
    // Restore the game state from state.json.
    // ------------------------------------------------------------------
    gs.phase                  = state_j.value("phase",                  "expansion");
    gs.turn                   = state_j.value("turn",                   "player");
    gs.player_energy          = state_j.value("player_energy",          INITIAL_ENERGY);
    gs.ai_energy              = state_j.value("ai_energy",              INITIAL_ENERGY);
    gs.player_total_resources = state_j.value("player_total_resources", 0);
    gs.ai_total_resources     = state_j.value("ai_total_resources",     0);
    gs.current_turn           = state_j.value("current_turn",           1);
    gs.max_turns              = state_j.value("max_turns",              MAX_TURNS);
    gs.game_over              = state_j.value("game_over",              false);
    gs.winner                 = state_j.value("winner",                 "");
    gs.consecutive_passes     = state_j.value("consecutive_passes",     0);
 
    // Restore the resource grid.
    auto& grid_arr = state_j["grid"];
    for (int r = 0; r < GRID_SIZE; ++r)
        for (int c = 0; c < GRID_SIZE; ++c)
            gs.grid[r][c] = grid_arr[r][c].get<int>();
 
    // Restore owners and colony resources.
    if (state_j.contains("owner_grid")) {
        auto& oa = state_j["owner_grid"];
        for (int r = 0; r < GRID_SIZE; ++r)
            for (int c = 0; c < GRID_SIZE; ++c)
                gs.owner_grid[r][c] = oa[r][c].get<int>();
    }
 
    // Rebuild the linked list and AVL tree from the saved colonies.
    if (state_j.contains("colonies")) {
        for (auto& col : state_j["colonies"]) {
            int cx    = col["x"].get<int>();
            int cy    = col["y"].get<int>();
            std::string cow = col["owner"].get<std::string>();
            int cres  = col["resources"].get<int>();
            history.append(cx, cy, cow, cres);
            tree.insert(cres, energy_cost_of(cres), cx, cy, cow);
            gs.resource_grid[cy][cx] = cres;
        }
    }
 
    if (gs.game_over) {
        std::cout << "[engine] Game already over. Winner: " << gs.winner << "\n";
        write_json(state_path, state_to_json(gs, history));
        return 0;
    }
 
    // ------------------------------------------------------------------
    // Read the next action from input.json.
    // ------------------------------------------------------------------
    json input_j;
    if (!read_json(input_path, input_j)) {
        std::cerr << "[engine] No valid input.json - writing current state.\n";
        write_json(state_path, state_to_json(gs, history));
        return 1;
    }
 
    std::string action = input_j.value("action", "pass");
    std::string result_msg = "";
 
    // ------------------------------------------------------------------
    // Process the requested action.
    // ------------------------------------------------------------------
    if (action == "colonize" && gs.phase == "expansion") {
        int dx = input_j["destination"]["x"].get<int>();
        int dy = input_j["destination"]["y"].get<int>();
        std::string err = action_colonize(dx, dy, gs.turn, gs, history, tree);
        if (err.empty()) {
            result_msg = "colonize_ok";
            gs.consecutive_passes = 0;   // a real move stops the pass streak
        } else {
            result_msg = "colonize_error: " + err;
            std::cerr << "[engine] " << result_msg << "\n";
        }
 
    } else if (action == "attack" && gs.phase == "combat") {
        int ox = input_j["origin"]["x"].get<int>();
        int oy = input_j["origin"]["y"].get<int>();
        int dx = input_j["destination"]["x"].get<int>();
        int dy = input_j["destination"]["y"].get<int>();
        result_msg = action_attack(ox, oy, dx, dy, gs.turn, gs, history, tree);
 
    } else if (action == "pass") {
        result_msg = "pass";
        ++gs.consecutive_passes;   // track passes in a row
 
    } else if (action == "reset") {
        // Python asked for a full reset.
        history.clear();
        tree.clear();
        gs = init_game();
        write_json(state_path, state_to_json(gs, history, "reset"));
        return 0;
    }
 
    // ------------------------------------------------------------------
    // Check if expansion should change to combat.
    // Because of the distance rule, the board may never become fully occupied.
    // Combat starts when the board is full, nobody can expand, or both pass.
    // ------------------------------------------------------------------
    // ------------------------------------------------------------------
    if (gs.phase == "expansion") {
        bool player_can_expand = has_expansion_moves("player", gs, history, gs.player_energy);
        bool ai_can_expand     = has_expansion_moves("ai",     gs, history, gs.ai_energy);
        // The pass check helps when empty cells are blocked by the distance rule.


        // empty cells are all blocked by the minimum-distance rule.
        if (grid_full(gs) ||
            (!player_can_expand && !ai_can_expand) ||
            gs.consecutive_passes >= 2) {
            gs.phase = "combat";
            gs.consecutive_passes = 0;
            result_msg += " | PHASE: combat";
        }
    }
 
    // ------------------------------------------------------------------
    // Move to the next turn.
    // ------------------------------------------------------------------
    if (gs.turn == "player") {
        gs.turn = "ai";
    } else {
        gs.turn = "player";
        ++gs.current_turn;
    }
 
    // ------------------------------------------------------------------
    // Check if the game has ended.
    // ------------------------------------------------------------------
    // The turn limit only counts during combat.
    // Expansion can take many turns and ends when no moves remain.
    if (gs.phase == "combat" && gs.current_turn > gs.max_turns) {
        gs.game_over = true;
        gs.winner    = determine_winner(gs);
    }
    // In combat, the game also ends if one side has no cells left.
    if (gs.phase == "combat") {
        int p_cells = count_cells(gs, 1);
        int a_cells = count_cells(gs, 2);
        if (p_cells == 0) { gs.game_over = true; gs.winner = "ai"; }
        if (a_cells == 0) { gs.game_over = true; gs.winner = "player"; }
    }
 
    // ------------------------------------------------------------------
    // Save the updated state.
    // ------------------------------------------------------------------
    write_json(state_path, state_to_json(gs, history, result_msg));
    std::cout << "[engine] Action='" << action << "' Result='" << result_msg << "'\n";
 
    return 0;
}
