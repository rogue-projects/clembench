from typing import List, Dict, Tuple

from backends import Model, ModelSpec, get_model_for, load_model_registry


import chess

from games.chess_withvariants.utils.board_functions import  board_to_text,matrix_to_fen,fen_to_matrix,generateBoard
from games.chess_withvariants.utils.general import  get_path_stockfish_bin

from clemgame.clemgame import GameMaster,Player


#should check if the engine is there, if its not download it. 
#Also this is a GPL License so we have to credit the authors I think
# TODO : test if engine exists; download if not latest version, etc etc. Function for downloading should be implemented in utils/general.py


class ChessPlayer(Player):
    def __init__(self, model_name: str, player: str, board: chess.Board):
        # always initialise the Player class with the model_name argument
        # if the player is a program and you don't want to make API calls to
        # LLMS, use model_name="programmatic"
        self.model_name: str = model_name
        self.player: str = player
        self.board: chess.Board = board
        self.engine =  None if model_name != 'programmatic' else chess.engine.SimpleEngine.popen_uci(get_path_stockfish_bin())

        # a list to keep the dialogue history
        self.history: List = []

    def _custom_response(self, messages, turn_idx) -> str:
        """Return a message with the next move(message) iff we are using a bot model."""
        if (self.model_name != "programmatic" ):
            raise PlayerResponseRequestError("Requesting bot responde from model" )
        message = "" 
        if (turn_idx == 1 and self.player == 'w'):
            #We should print the board    
            message += "Board:\n"
            message += str(self.board) + '\n'
        else:
            result = engine.play(self.board, chess.engine.limit(time=0.1))
            board.push(result.move)
            message +=  result.move + '\n'
        # return a string whose first and last tokens start with the next letter     
        return message


