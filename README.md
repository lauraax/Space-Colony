# Space Colony — CS1 Project

**Team:** Laura Paez · Nicolás Acero · Erik Fernandez  
**Variant:** Space Colony (No. 14)  
**Course:** Computer Science I — Universidad Distrital Francisco José de Caldas  
**Semester:** 2026-I

---

## Game Description

Space Colony is a turn-based strategy game where a human player competes against
an AI opponent to colonise and dominate an 8×8 grid planet.

**Phase 1 — Expansion:** Both sides take turns colonising empty cells.  
**Phase 2 — Combat:** Once the grid is full, sides attack adjacent enemy cells.  
**Win condition:** Player with most resources (or most cells) when the game ends.

---

## Project Structure

```
project/
├── engine/                  ← C++ core (compiled to ./engine/engine)
│   ├── linked_list.h / .cpp ← Colony history (singly linked list)
│   ├── tree.h / .cpp        ← Resource depot (AVL tree)
│   ├── main.cpp             ← Engine entry point (reads input.json → writes state.json)
│   ├── json.hpp             ← nlohmann/json single-header library
│   └── Makefile
│
├── game/
│   ├── algorithms/
│   │   ├── greedy.py        ← Greedy expansion and attack algorithms
│   │   └── backtracking.py  ← Backtracking expansion planner
│   └── ui/
│       ├── main.py          ← Pygame interface (ENTRY POINT)
│       └── bridge.py        ← JSON file I/O bridge (Python ↔ C++)
│
└── data/
    ├── input.json           ← Python → C++ action
    └── state.json           ← C++ → Python game state
```

---

## Requirements

### C++ Engine
- `g++` with C++17 support
- `make`

### Python UI
- Python 3.10+
- `pygame` library

Install pygame:
```bash
pip install pygame
```

---

## Setup & Execution

### 1. Compile the C++ engine (optional — auto-compiled on first run)

```bash
cd engine
make
cd ..
```

### 2. Run the game

```bash
# From the project root directory:
python game/ui/main.py
```

The Python layer will automatically compile the C++ engine if the binary is
not found.

---

## Controls

| Action | Input |
|---|---|
| Colonise a cell (expansion) | Left-click the target cell |
| Select attack origin (combat) | Left-click your own (green) cell |
| Attack enemy cell (combat) | Left-click an adjacent red cell after selecting origin |
| Pass turn | PASS button |
| Reset game | RESET button or `R` key |
| Help | HELP button or `H` key |
| Close help | Click anywhere or `ESC` |

---

## Architecture

```
Pygame UI  ──write──►  input.json  ──read──►  C++ Engine
           ◄──read──   state.json  ◄──write──
```

Communication between the Python and C++ layers is **exclusively through
JSON files** — no sockets, shared memory, or Python-C++ bindings.

---

## Algorithms

| Algorithm | Location | Phase | Complexity |
|---|---|---|---|
| Greedy Select Move | `greedy.py` | Expansion | O(n) |
| Greedy Attack | `greedy.py` | Combat | O(n) |
| Backtracking Expansion | `backtracking.py` | Expansion | O(4^d), d≤5 |

## Data Structures (C++)

| Structure | File | Purpose | Insert | Search |
|---|---|---|---|---|
| Singly Linked List | `linked_list.cpp` | Colony history | O(1) | O(n) |
| AVL Tree | `tree.cpp` | Resource depot, sorted by resources | O(log n) | O(log n) |

---

## Academic Integrity

All code was written by the team members. The use of external libraries is
limited to `nlohmann/json` (C++ JSON parsing) and `pygame` (Python UI),
both of which are explicitly permitted by the course specification.
