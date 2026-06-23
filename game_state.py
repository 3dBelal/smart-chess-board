import chess
import time
from copy import deepcopy
from board_state import fen_to_board, board_to_fen, print_board
from move_detection import detect_changes
from move_inference import infer_move, apply_move_to_state


class GameState:
    def __init__(self, white_name="White", black_name="Black",
                 time_limit_seconds=600):
        # Board and chess engine
        self.chess_board     = chess.Board()
        self.state           = fen_to_board(chess.STARTING_FEN)

        # Player info
        self.white_name      = white_name
        self.black_name      = black_name

        # Move history — list of UCI strings e.g. ['e2e4', 'e7e5']
        self.move_history    = []

        # Clock — remaining seconds for each player
        self.time_limit      = time_limit_seconds
        self.white_time      = float(time_limit_seconds)
        self.black_time      = float(time_limit_seconds)
        self._clock_start    = None   # when current player's turn started

        # Status flags
        self.desync          = False
        self.game_over       = False
        self.result          = None   # '1-0', '0-1', '1/2-1/2'

        # Promotion default
        self.promotion_piece = chess.QUEEN

        # Take-back support
        self.history         = []      # snapshots of state before each move
        self.takeback_used   = False   # only one take-back allowed per move

        # Start the clock for white
        self._start_clock()

    # ── Clock ──────────────────────────────────────────────────────

    def _start_clock(self):
        self._clock_start = time.time()

    def _stop_clock(self):
        if self._clock_start is None:
            return
        elapsed = time.time() - self._clock_start
        if self.chess_board.turn == chess.WHITE:
            self.white_time = max(0, self.white_time - elapsed)
        else:
            self.black_time = max(0, self.black_time - elapsed)
        self._clock_start = None

    def get_remaining_time(self):
        """Return current remaining time for both players, accounting for live elapsed."""
        white = self.white_time
        black = self.black_time
        if self._clock_start is not None:
            elapsed = time.time() - self._clock_start
            if self.chess_board.turn == chess.WHITE:
                white = max(0, white - elapsed)
            else:
                black = max(0, black - elapsed)
        return {'white': round(white, 1), 'black': round(black, 1)}

    def _check_flag(self):
        """Check if either player has run out of time."""
        times = self.get_remaining_time()
        if times['white'] <= 0:
            self.game_over = True
            self.result    = '0-1'
            print(f"  [CLOCK] {self.white_name} flagged. {self.black_name} wins.")
        elif times['black'] <= 0:
            self.game_over = True
            self.result    = '1-0'
            print(f"  [CLOCK] {self.black_name} flagged. {self.white_name} wins.")

    # ── Move processing ────────────────────────────────────────────

    def process_physical_move(self, new_board_state, promotion_piece=None):
        """
        Main entry point. Call this every time the board scan detects a change.
        
        new_board_state: the 64-element array from the latest reed switch scan
        promotion_piece: override the default queen promotion (optional)
        
        Returns: dict with result info for the phone app
        """
        if self.check_takeback(new_board_state):
            return self.apply_takeback()

        if self.game_over:
            return {'status': 'game_over', 'result': self.result}

        if self.desync:
            return {'status': 'desync', 'message': 'Board is desynced. Please resync.'}

        promo = promotion_piece or self.promotion_piece
        changes = detect_changes(self.state, new_board_state)
        move, updated_state = infer_move(
            self.state, changes, self.chess_board, promotion_piece=promo
        )

        if move is None:
            self.desync = True
            return {'status': 'desync', 'message': 'Illegal move detected.'}

        # Snapshot the current state before applying this move (for take-back).
        # move_uci is filled in now that the move has been inferred, but before
        # it is applied to the board.
        self.history.append({
            'board_state':     list(self.state),
            'chess_board_fen': self.chess_board.fen(),
            'turn':            self.chess_board.turn,
            'white_clock':     self.white_time,
            'black_clock':     self.black_time,
            'move_uci':        move.uci(),
        })
        # New accepted move resets take-back eligibility.
        self.takeback_used = False

        # Stop the current player's clock
        self._stop_clock()

        # Apply the move to the chess engine
        self.chess_board.push(move)
        self.state = updated_state
        self.move_history.append(move.uci())

        # Check for game over conditions
        if self.chess_board.is_checkmate():
            self.game_over = True
            self.result    = '0-1' if self.chess_board.turn == chess.WHITE else '1-0'
            winner = self.black_name if self.chess_board.turn == chess.WHITE else self.white_name
            print(f"  [CHECKMATE] {winner} wins!")
        elif self.chess_board.is_stalemate():
            self.game_over = True
            self.result    = '1/2-1/2'
            print("  [STALEMATE] Draw.")
        elif self.chess_board.is_insufficient_material():
            self.game_over = True
            self.result    = '1/2-1/2'
            print("  [DRAW] Insufficient material.")
        else:
            self._check_flag()
            if not self.game_over:
                self._start_clock()

        return self.get_sync_packet()

    # ── Take-back ──────────────────────────────────────────────────

    def check_takeback(self, new_board_state):
        """
        Return True if new_board_state exactly matches the board state that
        existed before the last move — i.e. the player physically returned the
        piece to its original square.
        """
        if len(self.history) < 1:
            return False
        if self.takeback_used:
            return False

        previous = self.history[-1]['board_state']
        if len(new_board_state) != len(previous):
            return False
        for current, prior in zip(new_board_state, previous):
            if current != prior:
                return False
        return True

    def apply_takeback(self):
        """
        Undo the last move by restoring the most recent snapshot.
        """
        snapshot = self.history.pop()

        self.state       = snapshot['board_state']
        self.white_time  = snapshot['white_clock']
        self.black_time  = snapshot['black_clock']
        self.chess_board = chess.Board(snapshot['chess_board_fen'])
        if self.move_history:
            self.move_history.pop()

        self.takeback_used = True

        return {
            "type":        "takeback",
            "fen":         self.chess_board.fen(),
            "turn":        snapshot['turn'],
            "white_clock": self.white_time,
            "black_clock": self.black_time,
        }

    def resync(self, fen):
        """
        Phone sends a corrected FEN to fix a desync.
        Resets the board to the provided position.
        """
        try:
            self.chess_board = chess.Board(fen)
            self.state       = fen_to_board(fen)
            self.desync      = False
            print(f"  [RESYNC] Board resynced to: {fen}")
            return True
        except Exception as e:
            print(f"  [RESYNC FAILED] {e}")
            return False

    # ── Sync packet — what the ESP32 broadcasts to any connecting phone ──

    def get_sync_packet(self):
        """
        Returns everything a newly connected phone needs to know.
        This is what the ESP32 sends immediately on BLE connection.
        """
        times = self.get_remaining_time()
        return {
            'fen':          self.chess_board.fen(),
            'turn':         'white' if self.chess_board.turn == chess.WHITE else 'black',
            'white_name':   self.white_name,
            'black_name':   self.black_name,
            'white_time':   times['white'],
            'black_time':   times['black'],
            'move_history': self.move_history,
            'move_count':   len(self.move_history),
            'game_over':    self.game_over,
            'result':       self.result,
            'desync':       self.desync,
            'in_check':     self.chess_board.is_check(),
        }


# ── Tests ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    from move_inference import apply_move_to_state

    def simulate_move(game, uci):
        """Helper: apply a UCI move physically and pass result to game state."""
        move        = chess.Move.from_uci(uci)
        new_state   = apply_move_to_state(game.state, move, game.chess_board)
        result      = game.process_physical_move(new_state)
        times       = game.get_remaining_time()
        print(f"  Move: {uci} | Turn: {result['turn']} | "
              f"W: {times['white']}s  B: {times['black']}s | "
              f"Check: {result['in_check']}")
        return result

    # ── Test 1: play a short game ──
    print("=== Test 1: short game ===")
    game = GameState("Belal", "Magnus", time_limit_seconds=300)

    simulate_move(game, "e2e4")
    simulate_move(game, "e7e5")
    simulate_move(game, "d1h5")   # queen to h5
    simulate_move(game, "b8c6")   # knight to c6
    simulate_move(game, "f1c4")   # bishop to c4
    simulate_move(game, "a7a6")
    result = simulate_move(game, "h5f7")   # scholar's mate

    print(f"\n  Game over: {game.game_over}")
    print(f"  Result: {game.result}")
    print(f"  Moves played: {game.move_history}")

    # ── Test 2: hot-swap simulation ──
    print("\n=== Test 2: phone hot-swap ===")
    game2  = GameState("Ali", "Sara", time_limit_seconds=600)
    simulate_move(game2, "e2e4")
    simulate_move(game2, "c7c5")

    print("\n  [Phone disconnects... new phone connects]")
    packet = game2.get_sync_packet()
    print(f"  Sync packet sent:")
    print(f"    FEN:     {packet['fen']}")
    print(f"    Turn:    {packet['turn']}")
    print(f"    Moves:   {packet['move_history']}")
    print(f"    W time:  {packet['white_time']}s")
    print(f"    B time:  {packet['black_time']}s")

    # ── Test 3: desync and resync ──
    print("\n=== Test 3: desync and resync ===")
    game3   = GameState(time_limit_seconds=300)
    fake    = deepcopy(game3.state)
    fake[0] = None   # artificially corrupt the state
    result  = game3.process_physical_move(fake)
    print(f"  Status after bad move: {result['status'] if 'status' in result else 'ok'}")

    game3.resync(chess.STARTING_FEN)
    print(f"  Desync flag after resync: {game3.desync}")