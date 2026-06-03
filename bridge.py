# =============================================================================
# Team: Laura Paez, Nicolas Acero, Erik Fernandez
# Variant: Space Colony (No. 14)
# Course: Computer Science I — Universidad Distrital Francisco Jose de Caldas
# File: game/ui/bridge.py
# Description: File I/O bridge between the Python layer and the C++ engine.
#
#   Python (Pygame UI + algorithms) communicates with the C++ engine
#   exclusively through two JSON files:
#       input.json   (Python -> C++) : the action to process
#       state.json   (C++ -> Python) : updated game state for rendering
#
#   Windows compatibility:
#       - Binary is engine.exe on Windows, engine on Linux/macOS.
#       - Compiles with g++ directly (no make needed).
#       - If g++ is not found, prints clear instructions and exits.
# =============================================================================

import json
import os
import platform
import shutil
import subprocess
import time
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
_BRIDGE_DIR  = Path(__file__).resolve().parent        # game/ui/
_PROJECT_DIR = _BRIDGE_DIR.parent.parent              # project/
_DATA_DIR    = _PROJECT_DIR / "data"
_ENGINE_DIR  = _PROJECT_DIR / "engine"
_INPUT_JSON  = _DATA_DIR / "input.json"
_STATE_JSON  = _DATA_DIR / "state.json"

_IS_WINDOWS = platform.system() == "Windows"
_ENGINE_BIN = _ENGINE_DIR / ("engine.exe" if _IS_WINDOWS else "engine")

_CPP_SOURCES = [
    str(_ENGINE_DIR / "main.cpp"),
    str(_ENGINE_DIR / "linked_list.cpp"),
    str(_ENGINE_DIR / "tree.cpp"),
]

_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _check_gpp() -> bool:
    """
    Return True if g++ is available on PATH, False otherwise.

    Time  : O(1)
    Space : O(1)
    """
    return shutil.which("g++") is not None


def _print_install_instructions() -> None:
    """Print clear installation instructions for the missing compiler."""
    print("\n" + "=" * 60, file=sys.stderr)
    print("ERROR: g++ compiler not found.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if _IS_WINDOWS:
        print(
            "\nTo fix this on Windows:\n"
            "  1. Install MSYS2 from https://www.msys2.org\n"
            "  2. Open the MSYS2 UCRT64 terminal and run:\n"
            "       pacman -S mingw-w64-ucrt-x86_64-gcc\n"
            "  3. Add  C:\\msys64\\ucrt64\\bin  to your Windows PATH:\n"
            "       Settings > System > Advanced > Environment Variables\n"
            "       Edit 'Path' > New > C:\\msys64\\ucrt64\\bin\n"
            "  4. Close and reopen PowerShell, then run compile.bat\n"
            "  5. Run: py game\\ui\\main.py",
            file=sys.stderr,
        )
    else:
        print(
            "\nTo fix this on Linux/macOS:\n"
            "  Ubuntu/Debian : sudo apt install g++\n"
            "  macOS         : xcode-select --install",
            file=sys.stderr,
        )
    print("=" * 60 + "\n", file=sys.stderr)


def init_engine() -> bool:
    """
    Compile the C++ engine if the binary does not exist.

    Uses g++ directly — no 'make' required.

    Returns
    -------
    bool
        True if the engine binary is ready, False on compile error.

    Time  : O(compilation time) on first call, O(1) after.
    Space : O(1)
    """
    if _ENGINE_BIN.exists():
        return True

    if not _check_gpp():
        _print_install_instructions()
        return False

    print("[bridge] Compiling C++ engine...", flush=True)

    cmd = [
        "g++", "-std=c++17", "-O2", "-Wall",
        *_CPP_SOURCES,
        "-o", str(_ENGINE_BIN),
    ]

    result = subprocess.run(
        cmd,
        cwd=str(_ENGINE_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("[bridge] Compilation FAILED:\n", result.stderr, file=sys.stderr)
        return False

    print("[bridge] Engine compiled successfully.", flush=True)
    return True


def _run_engine() -> bool:
    """
    Invoke the C++ engine binary synchronously (blocking).

    Returns
    -------
    bool
        True on success (exit code 0), False otherwise.

    Time  : O(n log n) for n colonies.
    Space : O(1)
    """
    try:
        result = subprocess.run(
            [str(_ENGINE_BIN), str(_DATA_DIR)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print("[bridge] Engine error:\n", result.stderr, file=sys.stderr)
            return False
        if result.stdout:
            print("[bridge]", result.stdout.strip(), flush=True)
        return True
    except subprocess.TimeoutExpired:
        print("[bridge] Engine timeout!", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(
            "[bridge] engine.exe not found.\n"
            "[bridge] Run compile.bat first (Windows) or: "
            "g++ -std=c++17 -O2 engine/*.cpp -o engine/engine",
            file=sys.stderr,
        )
        return False


def write_input(action: dict) -> bool:
    """
    Write action dict to input.json and invoke the C++ engine.

    The action dict must follow the JSON contract:
        colonize : {"action": "colonize",
                    "destination": {"x": int, "y": int}}
        attack   : {"action": "attack",
                    "origin":      {"x": int, "y": int},
                    "destination": {"x": int, "y": int}}
        pass     : {"action": "pass"}
        reset    : {"action": "reset"}

    Parameters
    ----------
    action : dict
        Action payload to write.

    Returns
    -------
    bool
        True if the engine processed the action successfully.

    Time  : O(1) write + O(engine runtime)
    Space : O(1)
    """
    try:
        tmp_path = str(_INPUT_JSON) + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(action, f, indent=2)
        os.replace(tmp_path, str(_INPUT_JSON))
    except OSError as e:
        print(f"[bridge] Cannot write input.json: {e}", file=sys.stderr)
        return False

    return _run_engine()


def read_state() -> dict | None:
    """
    Read and parse state.json produced by the C++ engine.

    Returns
    -------
    dict | None
        Parsed state dictionary, or None on error.

    Time  : O(|state.json|)
    Space : O(|state|)
    """
    for _ in range(5):
        try:
            with open(str(_STATE_JSON), "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            time.sleep(0.05)
    print("[bridge] Failed to read state.json after 5 attempts.", file=sys.stderr)
    return None


def reset_game() -> dict | None:
    """
    Ask the C++ engine to initialise a brand-new game.

    Returns
    -------
    dict | None
        Initial state, or None on error.

    Time  : O(GRID_SIZE^2) = O(64) = O(1)
    Space : O(1)
    """
    try:
        if _STATE_JSON.exists():
            _STATE_JSON.unlink()
    except OSError:
        pass

    if not _run_engine():
        return None

    return read_state()
