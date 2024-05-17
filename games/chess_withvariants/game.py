from typing import List, Dict, Tuple

from backends import Model, ModelSpec, get_model_for, load_model_registry



logger = get_logger(__name__)  # clem logging

import chess

from games.chess_withvariants.utils.board_functions import  board_to_text,matrix_to_fen,fen_to_matrix
from games.chess_withvariants.utils.board_functions import  get_path_stockfish_bin

class ChessPlayerBot(Player):
    def __init__(self, model_name: str, player: str, board: chess.Board):
        # always initialise the Player class with the model_name argument
        # if the player is a program and you don't want to make API calls to
        # LLMS, use model_name="programmatic"
        super().__init__(model_name)
        self.player: str = player
        self.board: chess.Board = board
        #should check if the engine is there, if its not download it. 
        #Also this is a GPL License so we have to credit the authors I think
        # TODO : test if engine exists; download if not latest version, etc etc. Function for downloading should be implemented in utils/general.py
        self.engine: SimpleEngine =  chess.engine.SimpleEngine.popen_uci(get_path_stockfish_bin)
        #We will store the board 
        
        # a list to keep the dialogue history
        self.history: List = []

    # implement this method as you prefer, with these same arguments
    def _custom_response(self, messages, turn_idx) -> str:
        """Return a mock message with the suitable letter and format."""
        # get the first letter of the content of the last message
        # messages is a list of dictionaries with messages in openai API format
        message = "" 
        if (turn_idx == 1 and self.player == 'w'):
            #We should print the board    
            message += "We are playing this chess with this board.\n"
            message += str(self.board) + '\'
        else:
            result = self.engine.play(self.board, chess.engine.limit(time=0.1))
            board.push(result.move)
            message +=  result.move + '\n'
        # return a string whose first and last tokens start with the next letter     
        return message


class Chess:
    """A game of chess between two players  
    """

    def __init__(self, game_instance: Dict, player_models: Tuple[Model]):
        self.player_models = player_models
        self.game_id = game_instance['game_id']
        self.max_turns = game_instance['max_turns']
        self.current_turn: int = 1
        initial_prompt = game_instance['player_2_initial_prompt']


    def proceeds(self):
        return self.current_turn <= self.max_turns

    def answerer_turn(self):
        _messages, _response_type, utterance = \
            self.answerer(self.messages, self.current_turn)
        self.messages.append({"role": "assistant", "content": utterance})
        self.current_turn += 1
        self.questioner.replied = True
        self.answerer.current_contribution = utterance

    def questioner_turn(self):
        """Adds the utterance that was typed on slurk to the messages."""
        utterance = self.questioner.get_current_message()
        self.messages.append({"role": "user", "content": utterance})
