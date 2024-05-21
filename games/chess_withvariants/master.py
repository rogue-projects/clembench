from clemgame.clemgame import GameMaster, GameBenchmark
from typing import List, Dict, Tuple
from clemgame import get_logger
import random,copy
from games.chess_withvariants.utils.board_functions import *
from games.chess_withvariants.instancegenerator import GAME_NAME
from games.chess_withvariants.players import ChessPlayer

logger = get_logger(__name__)


class Chess(GameMaster):
    """A game of chess between two players  
    """
    # We only need 2 players: white/black refers to pieces
    # 'programmatic' will be using our default(Stockfish)
    def __init__(self, experiment: Dict, player_backends: List[str]): 
        super().__init__(GAME_NAME, experiment, player_backends)
        # save experiment and player attributes that will be necessary later
        self.name = experiment['name']
        self.white = player_backends[0]
        self.black = player_backends[1]

        # initialise attributes that will be used for the evaluation scores
        self.aborted: bool = False
        self.lose: bool = False
        self.complete_turns: int = 0

    def setup(self, game_id: int, board: str, n_turns: int, initial_prompt: str) -> None:
        """Setup the episode (mandatory)."""

        self.n_turns = n_turns

        # instantiate both players
        self.white = ChessPlayer(self.white, 'w', board)
        self.black = ChessPlayer(self.black, 'b', board)

        # initialise game variables
        self.current_turn: int = 0
        self.game_id = game_id
        self.board = generateBoard(board)

        # initialise common metrics
        self.request_counts = [0] * (n_turns + 1)
        self.parsed_request_counts = [0] * (n_turns + 1)
        self.violated_request_counts = [0] * (n_turns + 1)

        # add initial prompts to each player's messages
        self.initiate(initial_prompt)

        # always log the details of the players in this format (see logdoc)
        self.log_players({
            'GM': 'Game master for FirstLast',
            'white': f'{self.white}',
            'black': f'{self.black}'
            })

        # log any additional keys that will be relevant for evaluation
        self.log_key('n_turns', n_turns)

    def initiate(self, initial_prompt: str) -> None:
        """Initialise the dialogue history (firstlast specific)."""
        # always call log_next_turn what a turn starts
        self.log_next_turn()

        # append the initial message of each player to their history
        # the value user means the message is from an interlocutor of the model
        if random.randint(0,1) ==0 :
            prompt_w = '' 
            prompt_b = initial_prompt
        else: 
            #TODO ADD FIRST MOVE AND UPDATE BOARD
            prompt_w = initial_prompt ##FIRST MOVE
            prompt_b = '' 
        self.white.history.append({'role': 'user', 'content': prompt_w})
        self.black.history.append({'role': 'user', 'content': prompt_b})
        
        # also log the messages as events for the transcriptions
        action = {'type': 'send message', 'content': prompt_w}
        self.log_event(from_='GM', to='w', action=action)
        action = {'type': 'send message', 'content': prompt_b}
        self.log_event(from_='GM', to='b', action=action)

    def play(self) -> None:
        """Play the game until the end (mandatory)."""
        # play the game
        while self.proceed():
            self.current_turn += 1
            # always call log_next_turn when a new turn starts
            self.log_next_turn()
            self.turn()
        
        if self.complete_turns == self.n_turns:
            # log a message informing that the game was successfuly played
            action = {'type': 'info', 'content': 'game successful'}
            self.log_event(from_='GM', to='GM', action=action)

        # log a final message saying that the game did came to an end
        action = {'type': 'info', 'content': 'end game'}
        self.log_event(from_='GM', to='GM', action=action)
        # log all temporary game variables that are needed for evaluation
        self.log_eval_assets()





    def proceed(self) -> None:
        """Check if the game loop should continue (firstlast specific)."""
        return (self.current_turn < self.n_turns
                and not self.aborted
                and not self.lose)

    def _append_utterance(self, utterance: str, player: str, role: str) -> None:
        """Add an utterance to the history of a player (firstlast specific)."""
        assert player in ('w', 'b')
        if player == 'w':
            self.white.history.append({'role': role, 'content': utterance})
        else:
            self.black.history.append({'role': role, 'content': utterance})

    @staticmethod
    def parse(utterance: str) -> Tuple[str, str]:
        """Check if the utterance is valid and return move,check(or checkmate)."""
        print(utterance)
        first_row = 'a'
        last_row = chr(ord(first_row) + 7)
        first_col='1'
        last_col = chr(ord(first_col) + 7)
        #Check for nonsensical moves 
        if   utterance[0] < first_row  or utterance[0] >last_row:
            return None,None
        if   utterance[2] < first_row  or utterance[2] >last_row:
            return None,None
        if   utterance[1] < first_col  or utterance[1] >last_col:
            return None,None
        if   utterance[3] < first_col  or utterance[3] >last_col:
            return None,None
        move =  utterance[0:3] 
        if  len(utterance) not in [10,14]:
            return None,None
        if len(utterance) == 10 and utterance[4:] == " check":
            return move,"check"
        if len(utterance) == 14 and utterance[4:] == " checkmate":
            return move,"checkmate"

        return None,None

    def _get_utterance(self, player: str) -> str:
        """Get utterance from a player and log it (firstlast specific)."""
        assert player in ('w', 'b')
        # make an API call (or get a programmatic response) from the player 
        if player == 'w':
            player_class = self.white
        else :
            player_class  = self.black
        prompt, raw_answer, answer = player_class (player_class .history,
                                                self.current_turn)
        # add API call to the records
        action = {'type': 'get message', 'content': answer}
        self.log_event(from_=player, to='GM', action=action,
                    call=(copy.deepcopy(prompt), raw_answer))
        # add reply to its own memory
        self._append_utterance(answer, player, 'assistant')

        # increase the number of API requests 
        self.request_counts[self.current_turn] += 1
        return answer


    def turn(self) -> None:
        """Perform a game turn, a single utterance by black or white."""
        try:
            last_move =  self.board.peek()
            print(last_move)
            cur_player ='w' if 'b'==board.color_at(last_move[2:4]) else 'b'
            next_player = 'b' if cur_player=='w' else 'w'
        except:
            cur_player = 'w'
            next_player = 'b'
        # get next player reply and add it to its history
        cur_move = self._get_utterance(next_player)
        
        # also add the reply to the transcript
        action = {'type': 'send message', 'content': cur_move}
        self.log_event(from_='GM', to=cur_turn, action=action)
        move,check = self.parse(cur_move)
        
        # add A's reply to B's history
        self._append_utterance(cur_move,cur_turn ,'user')

       
        board.push(move)

        # check if the game should be aborted or lost
        if not board.is_valid():
            # stop game
            return None

        self.complete_turns += 1


class ChessBenchmark(GameBenchmark):
    """Integrate the game into the benchmark run."""
    def __init__(self):
        super().__init__(GAME_NAME)

    # defines whether the game is single player or not
    def is_single_player(self):
        return False

    # add a description of your game
    def get_description(self):
        return "A simple game in which utterances must follow alphabetical rules."

    # copy this, replacing the name of the game master in the return statement
    def create_game_master(self,
                           experiment: Dict,
                           player_backends: List[str]
                           ) -> Chess:
        return Chess(experiment, player_backends)





