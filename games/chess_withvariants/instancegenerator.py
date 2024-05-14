"""
Randomly generate templates for the private/shared game.

Creates files in ./instances and ./requests
"""
from tqdm import tqdm

import re
import random
import chess


from clemgame.clemgame import GameInstanceGenerator

GAME_NAME = "chess"
N_INSTANCES= 2 #Let's start small
SEED = 123

# https://github.com/official-stockfish/Stockfish/blob/master/src/types.h#L192-L196
# Hardcoded to have a standarized test
piece_values = {
    'p': 208,
    'n': 781,
    'b': 825,
    'r': 1276,
    'q': 2538
}

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




class ChessGameInstanceGenerator(GameInstanceGenerator):
    """
        FEN stands for Forsyth-Edwards Notation. These are the general rules that define a board:
        Default board is:
            'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        Where: 
            "w" ->  White's turn
            "KQkq" ->   Castling available  on white(KQ) on  King (K) and Queen(Q) side.
                        Castling available  on black(kq) on  King (q) and Queen(q) side.
            "-" ->  No enpassant
            "0" ->  Number of half-moves
            "1" ->  Number of full-moves (begins at 1).
        
        We want to generate the following combinations of games:
            - Normal game (baseline for an easy test)
            - Chess puzzles
            - Randomized (with fairness) starting position of figures.
            - Randomized (with fairness) starting figures.
            - Combination of last 2 methods (which opens exponentially different generations).

    """
    # We want our games to not allow Castling 
    fenWithoutBoard= ' w - 0 1'
    baseBoard = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'

    def __init__(self, game_name):
        super().__init__(game_name)
        self.game_name = game_name

    def on_generate(self):
        #Dont need this one; we will generate each Board in a different manner
        #self.experiment_config = self.load_json("resources/config.json")
        #self.instance_utils = InstanceUtils(self.experiment_config, self.game_name)
        experiment = self.add_experiment('baseline')
        instance = self.add_game_instance(experiment,0)
        instance['board']= self.generateBoard()


   
    ###UNTESTED FUNCTION
    def evaluateBoardFair(board):
        """
        Check if the values of pieces on either side is fair or not
        """
        error_quotient=0.1
        w_value = 0
        b_value = 0
        for row in board:
            for piece in row:
                if piece is None:
                    continue
                elif piece.isUpper():
                    w_value += piece_values[piece.lower()]
                elif piece.isLower():
                    b_value += piece_values[piece]
        allowed_error= max(b_value,w_value)*error_quotient
        if  b_value < w_value:
            return b_value+allowed_error >= w_value
        else:
            return  w_value +allowed_error >= b_value

    ###UNTESTED FUNCTION
    def randomPiece():
        """ Returns a random piece """
        piece_options= piece_values.keys()
        return piece_options[random.randint(0,len(piece_options)]
    

    ###UNTESTED FUNCTION
    def randomBoard(piece_amount=16):
        """
        Generates a random board with pieceAmount pieces per player. Follows a set of rules for  avoiding unfair configurations: 
        - The king must always be in the farthest row from the center.
        - The amount of pieces per side must be equal. 
        - Pieces in the board will be filled from the farthest row to the center, putting pieces as far from the center rows as possible.
        """
        boardL = 8
        board =  [['Q']*boardL for _ in range(boardL)]
        if pieceAmount > 24:
            raise 'Too many pieces!!'
        while !evaluateBoardFair(board): 
            board =  [[None]*boardL for _ in range(boardL)]
            board[0][random.randint(0,boardL-1)]='k' 
            board[-1][random.randint(0,boardL-1)]='K' 
            # PENDING TO TEST THIS
            pieces_added = 0
            row = 0 
            col = 0
            while pieces_added < piece_amount:
                board[row][col] = randomPiece() 
                row+=1
                if row == boardL: 
                    row =0
                    col +=1
                pieces_added+=1
            pieces_added = 0
            row = -1 
            col = -1
            while pieces_added < piece_amount:
                board[row][col] = randomPiece() 
                row+= -1
                if - row == boardL : 
                    row = -1
                    col += -1
                pieces_added+=1
        return board


    def generateBoard(board=baseBoard):
        """
            Returns the standard  board configuration without castling. 
            Useful as a baseline.
        """
        return chess.Board(fen=f'{board} {fenWithoutBoard}')
   
    def create_prompt(self, board: chess.Board):
        return f"Your initial board is {board_to_text(boad)}. Let's play a game where you give me the next move in the UCI notation."


        

if __name__ == "__main__":
   ChessGameInstanceGenerator(GAME_NAME).generate()
