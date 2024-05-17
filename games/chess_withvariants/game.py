from typing import List, Dict, Tuple

from backends import Model, ModelSpec, get_model_for, load_model_registry



logger = get_logger(__name__)  # clem logging

import chess

from games.chess_withvariants.utils.board_functions import  board_to_text,matrix_to_fen,fen_to_matrix
from games.chess_withvariants.utils.board_functions import  get_path_stockfish_bin


#should check if the engine is there, if its not download it. 
#Also this is a GPL License so we have to credit the authors I think
# TODO : test if engine exists; download if not latest version, etc etc. Function for downloading should be implemented in utils/general.py

engine =  chess.engine.SimpleEngine.popen_uci(get_path_stockfish_bin)

class ChessPlayer(Player)
    def __init__(self, model_name: str, player: str, board: chess.Board):
        # always initialise the Player class with the model_name argument
        # if the player is a program and you don't want to make API calls to
        # LLMS, use model_name="programmatic"
        self.model_name: str = model_name
        self.player: str = player
        self.board: chess.Board = board
        
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
            message += str(self.board) + '\'
        else:
            result = engine.play(self.board, chess.engine.limit(time=0.1))
            board.push(result.move)
            message +=  result.move + '\n'
        # return a string whose first and last tokens start with the next letter     
        return message


class Chess(GameMaster):
    """A game of chess between two players  
    """
    # We only need 2 players: white/black refers to pieces
    # '' will be using our default(Stockfish)
    def __init__(self, experiment: Dict, white: str, black: str): 
        super().__init__(GAME_NAME, experiment, player_backends)
        # save experiment and player attributes that will be necessary later
        self.topic = experiment['name']
        self.white = white
        self.black = black
        self.board = experiment.

        # initialise attributes that will be used for the evaluation scores
        self.aborted: bool = False
        self.lose: bool = False
        self.complete_turns: int = 0

    def setup(self, first_letter: str, n_turns: int, prompt_player_a: str,
              prompt_player_b: str, game_id: int) -> None:
        """Setup the episode (mandatory)."""

        self.n_turns = n_turns

        # instantiate both players
        self.player_a = ChessPlayer(self.white, 'W', first_letter)
        self.player_b = Speaker(self.black, 'B', first_letter)

        # initialise game variables
        self.current_turn: int = 0
        self.current_letter: str = first_letter

        # initialise common metrics
        self.request_counts = [0] * (n_turns + 1)
        self.parsed_request_counts = [0] * (n_turns + 1)
        self.violated_request_counts = [0] * (n_turns + 1)

        # add initial prompts to each player's messages
        self.initiate(prompt_player_a, prompt_player_b)

        # always log the details of the players in this format (see logdoc)
        self.log_players({
            'GM': 'Game master for FirstLast',
            'Player 1': f'Player A: {self.model_a}',
            'Player 2': f'Player B: {self.model_b}'
            })

        # log any additional keys that will be relevant for evaluation
        self.log_key('n_turns', n_turns)




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
