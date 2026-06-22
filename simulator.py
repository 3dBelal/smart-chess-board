import pygame
import chess
import sys
from game_state import GameState
from move_inference import apply_move_to_state
from board_state import print_board

# ── Constants ────────────────────────────────────────────────────
SQ       = 80          # pixel size of each square
BOARD_PX = SQ * 8     # 640px
W        = BOARD_PX * 2 + 60   # two boards + gap
H        = BOARD_PX + 200      # board + info panel below

LIGHT    = (240, 217, 181)
DARK     = (181, 136, 99)
SEL      = (20, 200, 20)
HINT     = (100, 200, 100, 160)
LAST     = (205, 209, 111)
BG       = (30, 30, 30)
TEXT     = (220, 220, 220)
DIM      = (140, 140, 140)
RED      = (220, 80, 80)
GREEN    = (80, 200, 80)
BLUE     = (100, 160, 255)

PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}

# ── Helpers ──────────────────────────────────────────────────────

def sq_to_xy(idx, offset_x=0):
    """Convert board array index to pixel top-left corner."""
    f = idx % 8
    r = idx // 8
    x = offset_x + f * SQ
    y = (7 - r) * SQ       # flip so rank 1 is at bottom
    return x, y

def xy_to_sq(mx, my, offset_x=0):
    """Convert mouse pixel position to board array index."""
    f = (mx - offset_x) // SQ
    r = 7 - (my // SQ)
    if 0 <= f < 8 and 0 <= r < 8:
        return r * 8 + f
    return None

def get_legal_dests(game, from_sq):
    """Return list of legal destination indices for a piece."""
    piece = game.state[from_sq]
    if not piece:
        return []
    dests = []
    for move in game.chess_board.legal_moves:
        if move.from_square == from_sq:
            dests.append(move.to_square)
    return dests

# ── Drawing ──────────────────────────────────────────────────────

def draw_board(surface, board_state, font, offset_x,
               selected=None, hints=None, last_from=-1, last_to=-1,
               label=""):
    hints = hints or []

    # Label above board
    lbl = font.render(label, True, DIM)
    surface.blit(lbl, (offset_x + 4, BOARD_PX + 10))

    for r in range(8):
        for f in range(8):
            idx = r * 8 + f
            x   = offset_x + f * SQ
            y   = (7 - r) * SQ

            # Square color
            base = LIGHT if (f + r) % 2 == 1 else DARK
            pygame.draw.rect(surface, base, (x, y, SQ, SQ))

            # Highlights
            if idx == last_from or idx == last_to:
                s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                s.fill((205, 209, 60, 140))
                surface.blit(s, (x, y))

            if idx == selected:
                pygame.draw.rect(surface, SEL, (x, y, SQ, SQ), 4)

            if idx in hints:
                s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                s.fill((80, 200, 80, 120))
                surface.blit(s, (x, y))

            # Piece
            piece = board_state[idx]
            if piece:
                glyph = font.render(PIECES.get(piece, piece), True, (20, 20, 20))
                gw, gh = glyph.get_size()
                surface.blit(glyph, (x + (SQ - gw)//2, y + (SQ - gh)//2))

    # Rank and file labels
    small = pygame.font.SysFont('Arial', 11)
    for i in range(8):
        rl = small.render(str(i+1), True, DIM)
        surface.blit(rl, (offset_x + 2, (7-i)*SQ + 2))
        fl = small.render('abcdefgh'[i], True, DIM)
        surface.blit(fl, (offset_x + i*SQ + SQ-12, BOARD_PX - 14))

    # Board border
    pygame.draw.rect(surface, DIM, (offset_x, 0, BOARD_PX, BOARD_PX), 2)


def draw_reed_strip(surface, board_state, small_font, offset_x, y_start):
    """Draw a compact reed switch status strip — 64 tiny squares."""
    size = 14
    gap  = 2
    label = small_font.render("Reed switches:", True, DIM)
    surface.blit(label, (offset_x, y_start))

    for r in range(8):
        for f in range(8):
            idx = r * 8 + f
            x   = offset_x + f * (size + gap)
            y   = y_start + 18 + (7 - r) * (size + gap)
            color = GREEN if board_state[idx] else (60, 60, 60)
            pygame.draw.rect(surface, color, (x, y, size, size))


def draw_info(surface, game, font, small_font, log_lines, y_start):
    """Draw turn, move history, and event log below the boards."""
    turn_text = f"Turn: {'White' if game.chess_board.turn == chess.WHITE else 'Black'}"
    turn_color = TEXT if game.chess_board.turn == chess.WHITE else BLUE

    if game.chess_board.is_check():
        turn_text += "  ⚠ CHECK"
        turn_color = RED
    if game.game_over:
        turn_text = f"Game over — {game.result}"
        turn_color = RED

    surface.blit(font.render(turn_text, True, turn_color), (10, y_start))

    # Move history
    moves = game.move_history
    history = "  ".join(
        f"{i//2+1}. {moves[i]}{' '+moves[i+1] if i+1 < len(moves) else ''}"
        for i in range(0, len(moves), 2)
    )
    hist_surf = small_font.render(history[-80:], True, DIM)
    surface.blit(hist_surf, (10, y_start + 28))

    # Log lines
    for i, (line, color) in enumerate(log_lines[-4:]):
        surface.blit(small_font.render(line, True, color), (10, y_start + 52 + i*18))

    # Controls hint
    hint = small_font.render("R = new game    ESC = quit", True, (80, 80, 80))
    surface.blit(hint, (W - 260, y_start + 4))


# ── Main ─────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen  = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Smart Chess Board — Simulator")

    # Try to load a font that has chess glyphs
    font = None
    for name in ['Segoe UI Symbol', 'Arial Unicode MS', 'DejaVu Sans', 'FreeSans']:
        try:
            font = pygame.font.SysFont(name, 52)
            test = font.render('♔', True, (0,0,0))
            if test.get_width() > 5:
                break
        except:
            pass
    if font is None:
        font = pygame.font.SysFont(None, 52)

    small_font = pygame.font.SysFont('Arial', 13)
    label_font = pygame.font.SysFont('Arial', 15, bold=True)

    game      = GameState("White", "Black", time_limit_seconds=600)
    selected  = None
    hints     = []
    last_from = -1
    last_to   = -1
    log_lines = [("Game started. Click a piece to move.", BLUE)]

    LEFT_BOARD  = 0
    RIGHT_BOARD = BOARD_PX + 60

    clock = pygame.time.Clock()

    while True:
        screen.fill(BG)

        # ── Draw left board (physical / interactive) ──
        draw_board(screen, game.state, font, LEFT_BOARD,
                   selected=selected, hints=hints,
                   last_from=last_from, last_to=last_to,
                   label="Physical board  (click to move)")

        # ── Draw right board (ESP32 inferred) ──
        draw_board(screen, game.state, font, RIGHT_BOARD,
                   last_from=last_from, last_to=last_to,
                   label="ESP32 inferred position")

        # ── Reed switch strip (between boards, below) ──
        draw_reed_strip(screen, game.state, small_font,
                        LEFT_BOARD + BOARD_PX + 4, BOARD_PX + 30)

        # ── Info panel ──
        draw_info(screen, game, label_font, small_font,
                  log_lines, BOARD_PX + 10)

        pygame.display.flip()

        # ── Events ───────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_r:
                    game      = GameState("White", "Black", time_limit_seconds=600)
                    selected  = None; hints = []
                    last_from = -1; last_to = -1
                    log_lines = [("New game started.", BLUE)]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # Only respond to clicks on the left board
                if my > BOARD_PX:
                    continue
                if mx > BOARD_PX:
                    continue

                clicked = xy_to_sq(mx, my, LEFT_BOARD)
                if clicked is None:
                    continue

                if selected is None:
                    # Select a piece
                    piece = game.state[clicked]
                    if not piece:
                        continue
                    is_white_piece = piece == piece.upper()
                    if game.chess_board.turn == chess.WHITE and not is_white_piece:
                        continue
                    if game.chess_board.turn == chess.BLACK and is_white_piece:
                        continue

                    selected = clicked
                    hints    = get_legal_dests(game, clicked)
                    log_lines.append((f"Selected {piece} on {'abcdefgh'[clicked%8]}{clicked//8+1}", DIM))

                else:
                    if clicked == selected:
                        selected = None; hints = []
                        continue

                    if clicked in hints:
                        # Build what the new physical board state will be
                        move_obj  = None
                        for m in game.chess_board.legal_moves:
                            if m.from_square == selected and m.to_square == clicked:
                                move_obj = m
                                break

                        if move_obj:
                            new_state = apply_move_to_state(
                                game.state, move_obj, game.chess_board
                            )
                            result = game.process_physical_move(new_state)

                            uci  = move_obj.uci()
                            last_from = selected
                            last_to   = clicked

                            log_lines.append((
                                f"Move: {uci}  |  FEN: {game.chess_board.fen()[:30]}...",
                                GREEN
                            ))

                            if game.game_over:
                                log_lines.append((f"Game over: {game.result}", RED))
                            elif game.chess_board.is_check():
                                log_lines.append(("Check!", RED))

                        selected = None; hints = []

                    else:
                        # Clicked a different piece
                        piece = game.state[clicked]
                        if piece:
                            is_white_piece = piece == piece.upper()
                            if game.chess_board.turn == chess.WHITE and not is_white_piece:
                                selected = None; hints = []; continue
                            if game.chess_board.turn == chess.BLACK and is_white_piece:
                                selected = None; hints = []; continue
                            selected = clicked
                            hints    = get_legal_dests(game, clicked)
                        else:
                            selected = None; hints = []

        clock.tick(60)


if __name__ == "__main__":
    main()