from board_state import fen_to_board, print_board
import chess

def get_occupancy(state):
    """
    Convert the full board state into a simple set of occupied square indices.
    This is what the reed switches give us — just presence/absence, no piece identity.
    """
    return {i for i, piece in enumerate(state) if piece is not None}


def detect_changes(before_state, after_state):
    """
    Compare two board snapshots and return which squares changed.
    
    For captures: the destination square stays occupied throughout,
    so we track piece identity changes too, not just occupancy.
    
    Returns a dict with:
      'vacated'  — squares that had a piece and now don't
      'occupied' — squares that were empty and now have a piece
      'from_sq'  — the square a piece moved FROM (for captures)
      'to_sq'    — the square a piece moved TO (for captures)
    """
    before_occ = get_occupancy(before_state)
    after_occ  = get_occupancy(after_state)

    vacated  = before_occ - after_occ
    occupied = after_occ - before_occ

    # Handle captures: destination was already occupied so doesn't show in 'occupied'
    # We detect this by finding a square that lost a piece AND a square whose
    # piece identity changed (different piece now on it)
    if len(vacated) == 1 and len(occupied) == 0:
        from_sq = list(vacated)[0]
        # Find a square where the piece changed (capture destination)
        for i in range(64):
            if before_state[i] is not None and after_state[i] is not None:
                if before_state[i] != after_state[i]:
                    occupied = {i}
                    break

    return {
        'vacated':  vacated,
        'occupied': occupied
    }


def classify_change(changes):
    """
    Look at the pattern of vacated/occupied squares and classify what kind
    of physical event happened. This tells Stage 3 what to expect.

    Patterns:
      1 vacated + 1 occupied = normal move or capture
      2 vacated + 2 occupied = castling (king and rook both move)
      2 vacated + 1 occupied = en passant (pawn + captured pawn vacate, one occupied)
      anything else          = error / desync
    """
    v = len(changes['vacated'])
    o = len(changes['occupied'])

    if v == 1 and o == 1:
        return 'normal'
    elif v == 2 and o == 2:
        return 'castling'
    elif v == 2 and o == 1:
        return 'en_passant'
    else:
        return 'error'


def index_to_square(idx):
    """Convert array index back to human-readable square like 'e2'."""
    file = idx % 8
    rank = idx // 8
    return f"{'abcdefgh'[file]}{rank + 1}"


# ── Tests ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from copy import deepcopy

    board = fen_to_board(chess.STARTING_FEN)

    # ── Test 1: normal pawn move (e2 → e4) ──
    print("=== Test 1: e2 → e4 (normal move) ===")
    after = deepcopy(board)
    after[28] = after[12]   # move piece from e2 (index 12) to e4 (index 28)
    after[12] = None        # e2 is now empty

    changes = detect_changes(board, after)
    kind    = classify_change(changes)

    print(f"Vacated:  {[index_to_square(i) for i in changes['vacated']]}")
    print(f"Occupied: {[index_to_square(i) for i in changes['occupied']]}")
    print(f"Type: {kind}")
    print()

    # ── Test 2: castling (king e1→g1, rook h1→f1) ──
    print("=== Test 2: white kingside castling ===")
    castle_fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    pre  = fen_to_board(castle_fen)
    post = deepcopy(pre)

    post[6]  = post[4]   # king e1 → g1
    post[4]  = None
    post[5]  = post[7]   # rook h1 → f1
    post[7]  = None

    changes = detect_changes(pre, post)
    kind    = classify_change(changes)

    print(f"Vacated:  {[index_to_square(i) for i in changes['vacated']]}")
    print(f"Occupied: {[index_to_square(i) for i in changes['occupied']]}")
    print(f"Type: {kind}")
    print()

    # ── Test 3: en passant ──
    print("=== Test 3: en passant ===")
    ep_fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    pre  = fen_to_board(ep_fen)
    post = deepcopy(pre)

    # white pawn on e5 captures black pawn on d5, lands on d6
    e5 = 4 + 4*8   # index 36
    d5 = 3 + 4*8   # index 35
    d6 = 3 + 5*8   # index 43

    post[d6] = post[e5]   # white pawn moves to d6
    post[e5] = None       # e5 vacated
    post[d5] = None       # d5 vacated (captured pawn disappears)

    changes = detect_changes(pre, post)
    kind    = classify_change(changes)

    print(f"Vacated:  {[index_to_square(i) for i in changes['vacated']]}")
    print(f"Occupied: {[index_to_square(i) for i in changes['occupied']]}")
    print(f"Type: {kind}")