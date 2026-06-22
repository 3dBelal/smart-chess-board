import chess
from copy import deepcopy
from board_state import fen_to_board, board_to_fen, print_board
from move_detection import detect_changes, classify_change, index_to_square


def apply_move_to_state(state, chess_move, chess_board):
    new_state = deepcopy(state)
    from_idx  = chess_move.from_square
    to_idx    = chess_move.to_square

    if chess_move.promotion:
        piece = chess.Piece(chess_move.promotion, chess_board.turn)
        new_state[to_idx]   = piece.symbol()
        new_state[from_idx] = None

    elif chess_board.is_en_passant(chess_move):
        new_state[to_idx]   = new_state[from_idx]
        new_state[from_idx] = None
        captured_rank = to_idx + (-8 if chess_board.turn == chess.WHITE else 8)
        new_state[captured_rank] = None

    elif chess_board.is_castling(chess_move):
        new_state[to_idx]   = new_state[from_idx]
        new_state[from_idx] = None
        if chess_move.to_square == chess.G1:
            new_state[chess.F1] = new_state[chess.H1]
            new_state[chess.H1] = None
        elif chess_move.to_square == chess.C1:
            new_state[chess.D1] = new_state[chess.A1]
            new_state[chess.A1] = None
        elif chess_move.to_square == chess.G8:
            new_state[chess.F8] = new_state[chess.H8]
            new_state[chess.H8] = None
        elif chess_move.to_square == chess.C8:
            new_state[chess.D8] = new_state[chess.A8]
            new_state[chess.A8] = None

    else:
        new_state[to_idx]   = new_state[from_idx]
        new_state[from_idx] = None

    return new_state


def infer_move(state, changes, chess_board, promotion_piece=chess.QUEEN):
    kind     = classify_change(changes)
    vacated  = list(changes['vacated'])
    occupied = list(changes['occupied'])
    candidates = []

    for move in chess_board.legal_moves:
        from_sq = move.from_square
        to_sq   = move.to_square

        if kind == 'normal':
            if from_sq in vacated and to_sq in occupied:
                if move.promotion:
                    if move.promotion == promotion_piece:
                        candidates.append(move)
                else:
                    candidates.append(move)

        elif kind == 'castling':
            if chess_board.is_castling(move):
                if from_sq in vacated and to_sq in occupied:
                    candidates.append(move)

        elif kind == 'en_passant':
            if chess_board.is_en_passant(move):
                if from_sq in vacated and to_sq in occupied:
                    candidates.append(move)

    if len(candidates) == 1:
        move      = candidates[0]
        new_state = apply_move_to_state(state, move, chess_board)
        return move, new_state
    elif len(candidates) == 0:
        print("  [DESYNC] No legal move matches the detected change.")
        return None, None
    else:
        print(f"  [AMBIGUOUS] {len(candidates)} candidates: {candidates}")
        return None, None


if __name__ == "__main__":

    def run_test(name, fen, move_uci, promotion=chess.QUEEN):
        print(f"=== {name} ===")
        state       = fen_to_board(fen)
        chess_board = chess.Board(fen)
        expected    = chess.Move.from_uci(move_uci)

        after_state = apply_move_to_state(state, expected, chess_board)
        changes     = detect_changes(state, after_state)

        print(f"  Detected: {classify_change(changes)} — "
              f"vacated {[index_to_square(i) for i in changes['vacated']]} "
              f"occupied {[index_to_square(i) for i in changes['occupied']]}")

        inferred, new_state = infer_move(state, changes, chess_board, promotion_piece=promotion)

        if inferred:
            match = "✓ PASS" if inferred == expected else "✗ FAIL"
            print(f"  Inferred: {inferred}  {match}")
        print()

    run_test("Normal move — e2e4", chess.STARTING_FEN, "e2e4")

    run_test("Capture — exd5",
             "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",
             "e4d5")

    run_test("Castling — white kingside",
             "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
             "e1g1")

    run_test("En passant — exd6",
             "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3",
             "e5d6")

    run_test("Promotion — default queen",
             "8/4P3/8/8/8/8/8/4K2k w - - 0 1",
             "e7e8q")

    print("=== Desync — illegal move ===")
    state       = fen_to_board(chess.STARTING_FEN)
    chess_board = chess.Board(chess.STARTING_FEN)
    fake_change = {'vacated': {12}, 'occupied': {44}}
    infer_move(state, fake_change, chess_board)