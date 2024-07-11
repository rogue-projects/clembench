import chess
import chess.variant
# https://github.com/official-stockfish/Stockfish/blob/master/src/types.h#L192-L196
# Hardcoded to have a standarized test
piece_values = {
    'p': 208,
    'n': 781,
    'b': 825,
    'r': 1276,
    'q': 2538
}

# We want our games to not allow Castling 
fenWithoutBoard= 'w - - 0 1'
baseBoard = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'


##TODO: TEST
def generateBoard(board=baseBoard):
    """
        Returns the standard  board configuration without castling. 
        Useful as a baseline.
    """
    return f'{board} {fenWithoutBoard}'


def board_to_text(board):
    text=""
    for row in board:
        for val in row:
            if val is None:
               text.append('. ') 
            else:
               text.append(f'{val} ') 

    return board_to_text

#Utility functions

def matrix_to_fen(board):
    """
    Convert an 8x8 matrix representing the board to FEN (Forsyth-Edwards Notation).
    """
    fen = ""
    empty_count = 0
    
    for row in board:
        for square in row:
            if square is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    fen += str(empty_count)
                    empty_count = 0
                fen += square
        if empty_count > 0:
            fen += str(empty_count)
            empty_count = 0
        fen += '/'
    
    return fen.rstrip('/')


def fen_to_matrix(fen):
    """
    Convert FEN (Forsyth-Edwards Notation) to an 8x8 matrix representing the board.
    """
    board = [[None] * 8 for _ in range(8)]
    fen_parts = fen.split()
    ranks = fen_parts[0].split('/')
    
    for i, rank in enumerate(ranks):
        file_index = 0
        for char in rank:
            if char.isdigit():
                file_index += int(char)
            else:
                board[7 - i][file_index] = char
                file_index += 1
                
    return board

