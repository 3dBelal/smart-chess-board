import chess

# ─── Piece constants ───────────────────────────────────────────────
# We store the board as a plain list of 64 strings.
# Empty squares are None. Piece strings match the chess library's symbols.
# Uppercase = white, lowercase = black  (e.g. 'K' = white king, 'q' = black queen)

def fen_to_board(fen_string):
    """
    Convert a FEN string into our 64-element board array.
    Index 0 = a1 (bottom-left), index 63 = h8 (top-right).
    """
    board = chess.Board(fen_string)
    state = []

    for rank in range(8):          # ranks 0–7 = rows 1–8
        for file in range(8):      # files 0–7 = columns a–h
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            if piece is None:
                state.append(None)
            else:
                state.append(piece.symbol())   # e.g. 'K', 'q', 'p', 'R'

    return state


def board_to_fen(state, turn='w', castling='KQkq', en_passant='-', half=0, full=1):
    """
    Convert our 64-element board array back into a FEN string.
    The extra parameters carry game metadata the ESP32 will also store.
    """
    board = chess.Board(fen=None)   # empty board
    board.clear()

    for idx, symbol in enumerate(state):
        if symbol is not None:
            file = idx % 8
            rank = idx // 8
            square = chess.square(file, rank)
            piece = chess.Piece.from_symbol(symbol)
            board.set_piece_at(square, piece)

    board.turn = chess.WHITE if turn == 'w' else chess.BLACK

    # Build and return full FEN
    fen = board.fen()
    return fen


def starting_board():
    """Return the board array for the standard chess starting position."""
    return fen_to_board(chess.STARTING_FEN)


def print_board(state):
    """Print the board to the terminal so we can see what's happening."""
    print()
    print("  a  b  c  d  e  f  g  h")
    for rank in range(7, -1, -1):   # print from rank 8 down to rank 1
        row = f"{rank + 1} "
        for file in range(8):
            piece = state[rank * 8 + file]
            row += f" {piece if piece else '.'} "
        print(row)
    print()


def square_index(file_letter, rank_number):
    """
    Convert human-readable square notation (e.g. 'e', 4) to array index.
    Useful for testing — lets us say square_index('e', 2) instead of remembering index 12.
    """
    file = ord(file_letter.lower()) - ord('a')   # 'a'=0, 'b'=1 ... 'h'=7
    rank = rank_number - 1                        # rank 1=0, rank 8=7
    return rank * 8 + file


def get_piece(state, file_letter, rank_number):
    """Get the piece at a square using chess notation like ('e', 2)."""
    return state[square_index(file_letter, rank_number)]


# ─── Quick test ────────────────────────────────────────────────────
if __name__ == "__main__":
    board = starting_board()
    print_board(board)

    print(f"Piece at e1: {get_piece(board, 'e', 1)}")   # should be 'K'
    print(f"Piece at e8: {get_piece(board, 'e', 8)}")   # should be 'k'
    print(f"Piece at e4: {get_piece(board, 'e', 4)}")   # should be None

    fen = board_to_fen(board)
    print(f"\nFEN: {fen}")