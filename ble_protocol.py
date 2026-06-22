import json
import chess
from game_state import GameState
from move_inference import apply_move_to_state


# ── Message types ──────────────────────────────────────────────────
# Every message has a 'type' field. These are the only valid types.
# ESP32 → Phone
MSG_SYNC        = 'sync'         # full game state (sent on connect + after every move)
MSG_MOVE        = 'move'         # a move was made (lightweight update)
MSG_EVAL_REQ    = 'eval_req'     # request Stockfish evaluation for this FEN
MSG_DESYNC      = 'desync'       # board is desynced, phone should show warning
MSG_GAME_OVER   = 'game_over'    # game ended

# Phone → ESP32
MSG_EVAL        = 'eval'         # Stockfish centipawn score
MSG_RESYNC      = 'resync'       # phone sending corrected FEN
MSG_PROMOTION   = 'promotion'    # player chose a non-queen promotion
MSG_START       = 'start'        # start a new game with player names


# ── Message builders — ESP32 side ──────────────────────────────────

def build_sync_message(game):
    """Full state dump. Sent immediately when a phone connects."""
    packet = game.get_sync_packet()
    return json.dumps({'type': MSG_SYNC, **packet})


def build_move_message(move_uci, game):
    """Lightweight move notification sent after each move."""
    times = game.get_remaining_time()
    return json.dumps({
        'type':       MSG_MOVE,
        'move':       move_uci,
        'fen':        game.chess_board.fen(),
        'turn':       'white' if game.chess_board.turn == chess.WHITE else 'black',
        'white_time': times['white'],
        'black_time': times['black'],
        'in_check':   game.chess_board.is_check(),
        'move_count': len(game.move_history),
    })


def build_eval_request(game):
    """Ask the phone to run Stockfish on the current position."""
    return json.dumps({
        'type': MSG_EVAL_REQ,
        'fen':  game.chess_board.fen(),
    })


def build_desync_message():
    return json.dumps({
        'type':    MSG_DESYNC,
        'message': 'Board desynced. Please correct the position.',
    })


def build_game_over_message(game):
    return json.dumps({
        'type':   MSG_GAME_OVER,
        'result': game.result,
        'moves':  game.move_history,
    })


# ── Message handlers — Phone side ──────────────────────────────────

def handle_message(raw_message, game):
    """
    Parse a message arriving from the phone and act on it.
    Returns a response message to send back, or None.
    """
    try:
        msg = json.loads(raw_message)
    except json.JSONDecodeError:
        print("  [BLE] Invalid JSON received")
        return None

    kind = msg.get('type')

    if kind == MSG_EVAL:
        score = msg.get('score', 0)
        print(f"  [BLE] Eval received: {score} centipawns")
        # In real ESP32 code this drives the LED bar
        return None

    elif kind == MSG_RESYNC:
        fen = msg.get('fen', '')
        success = game.resync(fen)
        if success:
            return build_sync_message(game)
        return None

    elif kind == MSG_PROMOTION:
        piece_map = {'q': chess.QUEEN, 'r': chess.ROOK,
                     'b': chess.BISHOP, 'n': chess.KNIGHT}
        piece = piece_map.get(msg.get('piece', 'q'), chess.QUEEN)
        game.promotion_piece = piece
        print(f"  [BLE] Promotion override: {msg.get('piece', 'q')}")
        return None

    elif kind == MSG_START:
        print(f"  [BLE] New game started: "
              f"{msg.get('white', 'White')} vs {msg.get('black', 'Black')}")
        return None

    else:
        print(f"  [BLE] Unknown message type: {kind}")
        return None


# ── Simulate a full BLE session ─────────────────────────────────────

class BLESession:
    """
    Simulates the BLE link between ESP32 and phone.
    In real code this would be replaced by BLE characteristic writes.
    """
    def __init__(self):
        self.esp_to_phone = []   # message queue ESP32 → phone
        self.phone_to_esp = []   # message queue phone → ESP32

    def esp_send(self, message):
        self.esp_to_phone.append(message)
        parsed = json.loads(message)
        print(f"  [ESP32 → Phone] type={parsed['type']}"
              + (f" move={parsed.get('move','')}" if 'move' in parsed else "")
              + (f" fen={parsed.get('fen','')[:30]}..." if 'fen' in parsed else ""))

    def phone_send(self, message):
        self.phone_to_esp.append(message)
        parsed = json.loads(message)
        print(f"  [Phone → ESP32] type={parsed['type']}"
              + (f" score={parsed.get('score','')}" if 'score' in parsed else "")
              + (f" fen={parsed.get('fen','')[:30]}..." if 'fen' in parsed else ""))

    def esp_process_incoming(self, game):
        """ESP32 processes all messages waiting from the phone."""
        while self.phone_to_esp:
            msg = self.phone_to_esp.pop(0)
            response = handle_message(msg, game)
            if response:
                self.esp_send(response)

    def phone_process_incoming(self):
        """Phone processes all messages waiting from ESP32."""
        messages = []
        while self.esp_to_phone:
            messages.append(json.loads(self.esp_to_phone.pop(0)))
        return messages


# ── Tests ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    def sim_move(game, session, uci):
        """Simulate a physical move and the BLE messages it triggers."""
        move      = chess.Move.from_uci(uci)
        new_state = apply_move_to_state(game.state, move, game.chess_board)
        game.process_physical_move(new_state)

        # After every move ESP32 sends a move message + eval request
        session.esp_send(build_move_message(uci, game))
        session.esp_send(build_eval_request(game))

    # ── Test 1: normal game flow ──
    print("=== Test 1: normal BLE game flow ===\n")
    game    = GameState("Belal", "Magnus", time_limit_seconds=300)
    session = BLESession()

    # Phone connects — ESP32 sends full sync immediately
    print("-- Phone connects --")
    session.esp_send(build_sync_message(game))
    session.phone_process_incoming()

    # Moves happen
    print("\n-- Moves --")
    sim_move(game, session, "e2e4")
    sim_move(game, session, "e7e5")
    sim_move(game, session, "g1f3")

    # Phone sends back an eval score
    print("\n-- Phone returns eval --")
    session.phone_send(json.dumps({'type': MSG_EVAL, 'score': 35}))
    session.esp_process_incoming(game)

    # ── Test 2: hot-swap ──
    print("\n=== Test 2: hot-swap — new phone connects mid-game ===\n")
    print("-- New phone connects, ESP32 sends full sync --")
    session2 = BLESession()
    session2.esp_send(build_sync_message(game))
    received = session2.phone_process_incoming()
    print(f"  New phone got: turn={received[0]['turn']}, "
          f"moves={received[0]['move_history']}, "
          f"fen={received[0]['fen'][:40]}...")

    # ── Test 3: phone sends resync ──
    print("\n=== Test 3: resync from phone ===\n")
    session3 = BLESession()
    session3.phone_send(json.dumps({
        'type': MSG_RESYNC,
        'fen':  chess.STARTING_FEN,
    }))
    session3.esp_process_incoming(game)

    # ── Test 4: promotion override ──
    print("\n=== Test 4: promotion override from phone ===\n")
    session4 = BLESession()
    session4.phone_send(json.dumps({'type': MSG_PROMOTION, 'piece': 'r'}))
    session4.esp_process_incoming(game)
    piece_names = {chess.QUEEN: 'queen', chess.ROOK: 'rook',
                   chess.BISHOP: 'bishop', chess.KNIGHT: 'knight'}
    print(f"  Promotion piece is now: {piece_names[game.promotion_piece]}")