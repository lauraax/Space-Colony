# =============================================================================
# Team 14: Laura Paez, Nicolas Acero, Erik Fernandez
# Variant: Space Colony 
# Description: Pygame graphical interface for Space Colony.
#   Entry point — run with:  py game/ui/main.py   (from project root)
# =============================================================================

import sys
import os
import time
import pygame

_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from game.ui.bridge import init_engine, write_input, read_state, reset_game
from game.algorithms.greedy import (
    greedy_select_move,
    greedy_attack,
    get_ai_expansion_candidates,
    get_ai_attack_candidates,
)
from game.algorithms.backtracking import get_best_ai_move

# =============================================================================
# Display constants
# =============================================================================
GRID_SIZE    = 8
SCREEN_W     = 1280
SCREEN_H     = 720
CELL_SIZE    = 60
GRID_LEFT    = (SCREEN_W - GRID_SIZE * CELL_SIZE) // 2
GRID_TOP     = 92
HUD_HEIGHT   = 74
LOG_HEIGHT   = 58
FPS          = 30
AI_DELAY     = 0.8        # seconds before AI acts (visual clarity)

# Background image.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
BG_CANDIDATES = ["background.png", "background.jpg"]
# =============================================================================
# Colours
# =============================================================================
C_BG          = (28,  14,  10)    # dark rusty brown (fallback background)
C_GRID_LINE   = (90,  45,  30)    # burnt sienna grid lines
C_PLAYER      = (40, 130,  70)    # player still green for clear contrast
C_PLAYER_LIT  = (80, 210, 110)
C_AI          = (190,  55,  35)   # AI red-orange (Mars themed)
C_AI_LIT      = (240, 110,  70)
C_SELECTED    = (255, 210,  60)   # gold selection ring
C_TEXT        = (240, 225, 210)   # warm off-white
C_TEXT_DIM    = (170, 130, 110)   # muted clay
C_HUD_BG      = (40,  20,  14)     # semi-transparent panels use this + alpha
C_LOG_BG      = (24,  12,   8)
C_BTN         = (150,  60,  35)    # rust button
C_BTN_HOV     = (200,  95,  55)    # brighter rust on hover
C_BTN_DIS     = (70,  40,  30)
C_WIN         = (255, 195,  70)
C_PANEL_ALPHA = 205                # 0-255 opacity for HUD/log panels over image
C_ACCENT      = (255, 140,  60)    # orange accent for titles


def resource_shade(v: int) -> tuple:
    """
    Map a resource value (1-100) to a Mars-dust colour: dark rusty brown for
    low resources, bright amber/gold for high resources.
 
    Parameters
    ----------
    v : int  resource value 1-100
 
    Returns
    -------
    tuple[int,int,int]  RGB
    """
    t = max(0.0, min(1.0, v / 100.0))
    r = int(70  + t * (235 - 70))
    g = int(35  + t * (165 - 35))
    b = int(25  + t * (55  - 25))
    return (r, g, b)


# =============================================================================
# Simple Button
# =============================================================================
class Button:
    def __init__(self, rect: pygame.Rect, label: str, font: pygame.font.Font):
        """
        Clickable button widget.

        Parameters
        ----------
        rect  : pygame.Rect
        label : str
        font  : pygame.font.Font
        """
        self.rect  = rect
        self.label = label
        self.font  = font

    def draw(self, surface: pygame.Surface, mouse_pos: tuple,
             enabled: bool = True) -> None:
        """
        Draw the button. Highlights on hover, dims when disabled.

        Parameters
        ----------
        surface   : pygame.Surface
        mouse_pos : tuple (x, y)
        enabled   : bool
        """
        if not enabled:
            col = C_BTN_DIS
        elif self.rect.collidepoint(mouse_pos):
            col = C_BTN_HOV
        else:
            col = C_BTN
        pygame.draw.rect(surface, col, self.rect, border_radius=6)
        pygame.draw.rect(surface, C_TEXT_DIM, self.rect, 1, border_radius=6)
        txt = self.font.render(self.label, True, C_TEXT)
        surface.blit(txt, (
            self.rect.x + (self.rect.w - txt.get_width())  // 2,
            self.rect.y + (self.rect.h - txt.get_height()) // 2,
        ))

    def clicked(self, event: pygame.event.Event) -> bool:
        """
        Return True if this button was left-clicked by event.

        Parameters
        ----------
        event : pygame.event.Event
        """
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


# =============================================================================
# Main game
# =============================================================================
class SpaceColonyGame:
    """
    Owns the Pygame window and main loop.

    Attributes
    ----------
    state      : dict | None  — latest parsed state.json
    log        : list[str]    — last 5 event messages
    selected   : tuple|None   — (col, row) selected origin for combat
    ai_pending : bool         — AI turn is queued
    ai_timer   : float        — time.time() when AI was queued
    """

    def __init__(self):
        """Initialise Pygame, compile engine, load first state."""
        pygame.init()
        pygame.display.set_caption("Space Colony - CS1 Project")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        self.font_xl = pygame.font.SysFont("monospace", 24, bold=True)
        self.font_md = pygame.font.SysFont("monospace", 14)
        self.font_sm = pygame.font.SysFont("monospace", 11)

        self.state      = None
        self.log        = []
        self.selected   = None
        self.ai_pending = False
        self.ai_timer   = 0.0
        self.show_help  = False
        self.background = self._load_background()
        # Buttons — positioned inside the HUD strip
        hud_y = GRID_TOP + GRID_SIZE * CELL_SIZE
        self.btn_pass  = Button(pygame.Rect(SCREEN_W - 180, hud_y + 10, 80, 30), "PASS",  self.font_md)
        self.btn_reset = Button(pygame.Rect(SCREEN_W -  90, hud_y + 10, 80, 30), "RESET", self.font_md)
        self.btn_help  = Button(pygame.Rect(12, 12, 80, 30), "HELP",  self.font_md)

        if not init_engine():
            self._log("ERROR: g++ not found. See README.")
            return

        state = reset_game()
        if state:
            self.state = state
            self._log("New game started. You are GREEN.")
        else:
            self._log("ERROR: engine did not start.")

    def _load_background(self):
        """
        Load a background image from assets/ if present and scale it to the
        window size.
 
        Looks for any file in BG_CANDIDATES inside game/ui/assets/.
        To use your own image, save it as game/ui/assets/background.png
        (or .jpg). The image is stretched to fill the whole window.
 
        Returns
        -------
        pygame.Surface | None
            The scaled background surface, or None if no image was found.
        """
        for name in BG_CANDIDATES:
            path = os.path.join(ASSETS_DIR, name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert()
                    return pygame.transform.smoothscale(img, (SCREEN_W, SCREEN_H))
                except pygame.error as e:
                    print(f"[ui] Could not load background '{name}': {e}")
        return None
    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        """Append msg to log, keeping at most 5 lines."""
        self.log.append(msg)
        if len(self.log) > 5:
            self.log.pop(0)

    # ------------------------------------------------------------------
    def _is_player_turn(self) -> bool:
        """Return True when it is the human player's turn and game is live."""
        return (self.state is not None and
                self.state.get("turn") == "player" and
                not self.state.get("game_over", False) and
                not self.ai_pending)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    @staticmethod
    def cell_rect(col: int, row: int) -> pygame.Rect:
        """
        Pixel Rect for grid cell (col, row).

        Parameters
        ----------
        col, row : int  0-based grid indices

        Returns
        -------
        pygame.Rect
        """
        return pygame.Rect(
            GRID_LEFT + col * CELL_SIZE,
            GRID_TOP  + row * CELL_SIZE,
            CELL_SIZE, CELL_SIZE,
        )

    @staticmethod
    def pixel_to_cell(px: int, py: int):
        """
        Convert screen pixel to (col, row), or None if outside the grid.

        Parameters
        ----------
        px, py : int  screen coordinates

        Returns
        -------
        tuple[int,int] | None
        """
        col = (px - GRID_LEFT) // CELL_SIZE
        row = (py - GRID_TOP)  // CELL_SIZE
        if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
            # Verify pixel is actually inside (handles negative adjusted coords)
            if px >= GRID_LEFT and py >= GRID_TOP:
                return (col, row)
        return None

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _panel(self, x: int, y: int, w: int, h: int, colour: tuple,
               alpha: int = None) -> None:
        """
        Draw a translucent filled rectangle so the background image shows
        through. Used for the title, HUD, and log panels.
 
        Parameters
        ----------
        x, y, w, h : int     panel rectangle
        colour     : tuple   RGB fill colour
        alpha      : int|None opacity 0-255 (defaults to C_PANEL_ALPHA)
        """
        if alpha is None:
            alpha = C_PANEL_ALPHA
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((colour[0], colour[1], colour[2], alpha))
        self.screen.blit(surf, (x, y))

    def _draw_grid(self, mouse_pos: tuple) -> None:
        """
        Render the 8x8 grid.
 
        Parameters
        ----------
        mouse_pos : tuple  current mouse position
        """
        if not self.state:
            return
        grid       = self.state.get("grid", [])
        owner_grid = self.state.get("owner_grid", [])
        hovered    = self.pixel_to_cell(*mouse_pos)
 
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                rect     = self.cell_rect(col, row)
                owner_id = owner_grid[row][col] if owner_grid else 0
                res      = grid[row][col] if grid else 0
 
                if owner_id == 1:
                    base = C_PLAYER
                elif owner_id == 2:
                    base = C_AI
                else:
                    base = resource_shade(res)
 
                if owner_id == 0:
                    # Empty cells are semi-transparent so the Mars background
                    # shows through, blending the grid into the scene.
                    cell_surf = pygame.Surface((CELL_SIZE, CELL_SIZE),
                                               pygame.SRCALPHA)
                    cell_surf.fill((base[0], base[1], base[2], 170))
                    self.screen.blit(cell_surf, (rect.x, rect.y))
                else:
                    # Owned cells are solid for clear ownership reading.
                    pygame.draw.rect(self.screen, base, rect)
 
                # Hover highlight
                if hovered == (col, row) and owner_id == 0:
                    pygame.draw.rect(self.screen, C_SELECTED, rect, 3)
 
                # Selected-origin highlight (combat)
                if self.selected == (col, row):
                    pygame.draw.rect(self.screen, C_SELECTED, rect, 4)
 
                # Resource number
                if res > 0:
                    lbl = self.font_sm.render(str(res), True,
                                              (255, 255, 200) if owner_id else C_TEXT)
                    self.screen.blit(lbl, (rect.x + 4, rect.y + 4))
 
                # Owner dot
                if owner_id == 1:
                    pygame.draw.circle(self.screen, C_PLAYER_LIT, rect.center, 9)
                elif owner_id == 2:
                    pygame.draw.circle(self.screen, C_AI_LIT, rect.center, 9)
 
                pygame.draw.rect(self.screen, C_GRID_LINE, rect, 1)

    def _draw_hud(self, mouse_pos: tuple) -> None:
        """
        Render HUD panel (resources, energy, phase, buttons).
 
        Parameters
        ----------
        mouse_pos : tuple  current mouse position
        """
        if not self.state:
            return
        hud_y = GRID_TOP + GRID_SIZE * CELL_SIZE
        self._panel(0, hud_y, SCREEN_W, HUD_HEIGHT, C_HUD_BG)
        pygame.draw.line(self.screen, C_ACCENT,
                         (0, hud_y), (SCREEN_W, hud_y), 2)
 
        phase  = self.state.get("phase",  "expansion").upper()
        turn   = self.state.get("turn",   "player").upper()
        c_turn = self.state.get("current_turn", 1)
        m_turn = self.state.get("max_turns",   50)
        p_res  = self.state.get("player_total_resources", 0)
        a_res  = self.state.get("ai_total_resources",     0)
        p_en   = self.state.get("player_energy",  0)
        a_en   = self.state.get("ai_energy",       0)
 
        tc = C_PLAYER_LIT if turn == "PLAYER" else C_AI_LIT
 
        self.screen.blit(self.font_md.render(
            f"Phase: {phase}   Turn: {turn}   Round: {c_turn}/{m_turn}",
            True, tc), (12, hud_y + 8))
        self.screen.blit(self.font_md.render(
            f"Player   Res: {p_res:4d}   Energy: {p_en:3d}",
            True, C_PLAYER_LIT), (12, hud_y + 30))
        self.screen.blit(self.font_md.render(
            f"AI       Res: {a_res:4d}   Energy: {a_en:3d}",
            True, C_AI_LIT), (12, hud_y + 50))
 
        if self.state.get("game_over", False):
            w = self.state.get("winner", "").upper()
            msg = f"GAME OVER - {w} WINS!" if w != "DRAW" else "GAME OVER - DRAW"
            banner = self.font_xl.render(msg, True, C_WIN)
            self.screen.blit(banner, (
                (SCREEN_W - banner.get_width()) // 2, hud_y + 8))
 
        is_pt = self._is_player_turn()
        self.btn_pass.draw(self.screen, mouse_pos, enabled=is_pt)
        self.btn_reset.draw(self.screen, mouse_pos, enabled=True)
 
    def _draw_log(self) -> None:
        """Render the event log strip at the bottom."""
        log_y = GRID_TOP + GRID_SIZE * CELL_SIZE + HUD_HEIGHT
        self._panel(0, log_y, SCREEN_W, LOG_HEIGHT, C_LOG_BG)
        pygame.draw.line(self.screen, C_ACCENT,
                         (0, log_y), (SCREEN_W, log_y), 2)
        for i, msg in enumerate(self.log[-4:]):
            fade = max(80, 220 - (3 - i) * 45)
            self.screen.blit(
                self.font_sm.render(msg, True, (fade, fade, min(255, fade + 20))),
                (8, log_y + 4 + i * 18))
 
    def _draw_title(self) -> None:
        """Render the title bar."""
        self._panel(0, 0, SCREEN_W, GRID_TOP, (20, 10, 6), alpha=180)
        pygame.draw.line(self.screen, C_ACCENT,
                         (0, GRID_TOP), (SCREEN_W, GRID_TOP), 2)
        title = self.font_xl.render("SPACE COLONY", True, C_ACCENT)
        self.screen.blit(title, ((SCREEN_W - title.get_width()) // 2, 12))
        sub = self.font_md.render("CS1 Project  |  Green = You  |  Red = AI",
                                  True, C_TEXT_DIM)
        self.screen.blit(sub, ((SCREEN_W - sub.get_width()) // 2, 50))
        self.btn_help.draw(self.screen, pygame.mouse.get_pos(), enabled=True)
        # Column letters and row numbers for easier cell identification
        for i in range(GRID_SIZE):
            lbl = self.font_sm.render(str(i), True, C_TEXT_DIM)
            # Column header
            cx = GRID_LEFT + i * CELL_SIZE + CELL_SIZE // 2 - lbl.get_width() // 2
            self.screen.blit(lbl, (cx, GRID_TOP - 18))
            # Row header
            ry = GRID_TOP + i * CELL_SIZE + CELL_SIZE // 2 - lbl.get_height() // 2
            self.screen.blit(lbl, (GRID_LEFT - 18, ry))
 

    def _draw_help(self) -> None:
        """Render a semi-transparent help overlay."""
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        self.screen.blit(ov, (0, 0))
        lines = [
            "CONTROLS",
            "",
            "EXPANSION PHASE:",
            "  Click any empty cell to colonise it.",
            "  First colony: anywhere on the grid.",
            "  Later: must be within 2 cells of existing territory.",
            "  Your colonies must be at least 2 apart from each other.",
            "",
            "COMBAT PHASE (when grid is full):",
            "  1. Click your colony (green dot) to select it.",
            "  2. Click an adjacent enemy cell (red) to attack.",
            "  Power = Resources + dice roll (1-6).",
            "  Higher power wins the cell.",
            "",
            "BUTTONS:  PASS = skip turn   RESET = new game",
            "KEYS:     H = help   R = reset   ESC = close help",
            "",
            "           Click anywhere to close",
        ]
        y = 80
        for line in lines:
            colour = (255, 215, 0) if line == "CONTROLS" else (210, 210, 230)
            self.screen.blit(self.font_md.render(line, True, colour), (50, y))
            y += 22

    # ------------------------------------------------------------------
    # Game logic
    # ------------------------------------------------------------------
    def _send_action(self, action: dict) -> None:
        """
        Write action to input.json, invoke engine, reload state.

        Parameters
        ----------
        action : dict  JSON-serialisable action payload
        """
        ok = write_input(action)
        if not ok:
            self._log("Engine error - check console.")
            return
        new_state = read_state()
        if new_state:
            self.state = new_state
            result = new_state.get("last_result", "")
            self._log(f"{action['action'].upper()}: {result}")
            if (new_state.get("turn") == "ai" and
                    not new_state.get("game_over", False)):
                self.ai_pending = True
                self.ai_timer   = time.time()
        else:
            self._log("Could not read state.json.")

    def _handle_cell_click(self, col: int, row: int) -> None:
        """
        Handle a player left-click on grid cell (col, row).

        Expansion: sends a colonize action.
        Combat: first click selects origin, second click attacks.

        Parameters
        ----------
        col, row : int  0-based grid indices
        """
        if not self._is_player_turn():
            return

        phase      = self.state.get("phase", "expansion")
        owner_grid = self.state.get("owner_grid", [])
        owner_id   = owner_grid[row][col]

        if phase == "expansion":
            if owner_id != 0:
                self._log("That cell is already occupied.")
                return
            self._send_action({"action": "colonize",
                               "destination": {"x": col, "y": row}})

        else:  # combat
            if self.selected is None:
                if owner_id == 1:
                    self.selected = (col, row)
                    self._log(f"Selected ({col},{row}). Now click an enemy cell.")
                else:
                    self._log("Click one of YOUR colonies (green) first.")
            else:
                ox, oy = self.selected
                if owner_id == 2:
                    self.selected = None
                    self._send_action({
                        "action": "attack",
                        "origin":      {"x": ox,  "y": oy},
                        "destination": {"x": col, "y": row},
                    })
                elif owner_id == 1:
                    self.selected = (col, row)
                    self._log(f"Re-selected ({col},{row}).")
                else:
                    self._log("Target must be a RED (enemy) cell.")
                    self.selected = None

    def _execute_ai_turn(self) -> None:
        """
        Compute and submit the AI action.

        Expansion: backtracking, greedy fallback.
        Combat: greedy attack.
        """
        if not self.state:
            self.ai_pending = False
            return

        phase = self.state.get("phase", "expansion")

        if phase == "expansion":
            move = get_best_ai_move(self.state)
            if move is None:
                cands = get_ai_expansion_candidates(self.state)
                move  = greedy_select_move(cands, self.state["ai_energy"])
            if move:
                self._log(f"AI colonises ({move['x']},{move['y']}) res={move['resources']}")
                action = {"action": "colonize",
                          "destination": {"x": move["x"], "y": move["y"]}}
            else:
                self._log("AI passes (no valid move).")
                action = {"action": "pass"}
        else:
            cands  = get_ai_attack_candidates(self.state)
            target = greedy_attack(cands)
            if target:
                self._log(f"AI attacks ({target['x']},{target['y']})")
                action = {
                    "action": "attack",
                    "origin":      {"x": target["origin_x"], "y": target["origin_y"]},
                    "destination": {"x": target["x"],        "y": target["y"]},
                }
            else:
                self._log("AI passes (no valid attack).")
                action = {"action": "pass"}

        self._send_action(action)
        self.ai_pending = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """
        Pygame main loop.

        Each frame: handle events -> AI turn if pending -> draw.
        """
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.show_help = False
                    elif event.key == pygame.K_h:
                        self.show_help = not self.show_help
                    elif event.key == pygame.K_r:
                        self._do_reset()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Close help on any click
                    if self.show_help:
                        self.show_help = False
                        continue

                    # Buttons (checked before grid so overlapping is unambiguous)
                    if self.btn_reset.clicked(event):
                        self._do_reset()
                    elif self.btn_help.clicked(event):
                        self.show_help = True
                    elif self.btn_pass.clicked(event) and self._is_player_turn():
                        self._send_action({"action": "pass"})
                    else:
                        # Grid click
                        cell = self.pixel_to_cell(*event.pos)
                        if cell:
                            self._handle_cell_click(*cell)

            # AI move after delay
            if self.ai_pending and time.time() - self.ai_timer >= AI_DELAY:
                self._execute_ai_turn()

            # Draw
            if self.background is not None:
                self.screen.blit(self.background, (0, 0))
            else:
                self.screen.fill(C_BG)
            self._draw_title()
            self._draw_grid(mouse_pos)
            self._draw_hud(mouse_pos)
            self._draw_log()
            if self.show_help:
                self._draw_help()

            pygame.display.flip()
            self.clock.tick(FPS)

    def _do_reset(self) -> None:
        """Reset to a fresh game."""
        self.selected   = None
        self.ai_pending = False
        self.log        = []
        state = reset_game()
        if state:
            self.state = state
            self._log("Game reset. You are GREEN.")
        else:
            self._log("Reset failed.")


if __name__ == "__main__":
    game = SpaceColonyGame()
    game.run()
