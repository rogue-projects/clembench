from clemgame.clemgame import GameMaster, GameBenchmark
from typing import List, Dict, Tuple
from clemgame import get_logger
import clemgame.metrics as ms
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
        self.white_model = player_backends[0]
        self.black_model = player_backends[1]

        # initialise attributes that will be used for the evaluation scores
        self.aborted: bool = False
        self.lose: bool = False
        self.complete_turns: int = 0

    def setup(self, game_id: int, board: str, n_turns: int, initial_prompt: str) -> None:
        """Setup the episode (mandatory)."""

        self.n_turns = n_turns


        # initialise game variables
        self.current_turn: int = 0
        self.game_id = game_id
        self.board = chess.Board(fen=board,chess960=True)
        
        # instantiate both players
        self.white = ChessPlayer(self.white_model, 'w', self.board)
        self.black = ChessPlayer(self.black_model, 'b', self.board)

        # initialise common metrics
        self.request_counts = [0] * (n_turns + 1)
        self.parsed_request_counts = [0] * (n_turns + 1)
        self.violated_request_counts = [0] * (n_turns + 1)

        # add initial prompts to each player's messages
        self.initiate(initial_prompt)

        # always log the details of the players in this format (see logdoc)
        self.log_players({
            'GM': 'Game master for Chess',
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
        prompt_w = initial_prompt + f"\n You're playing white."
        prompt_b = initial_prompt + f"\n You're playing black."
        if str(self.white_model) == str('programmatic'):
            move = self._get_utterance('w')
            prompt_b +=  f"\n First move from white was {move}."

        self.white.history.append({'role': 'user', 'content': prompt_w})
        self.black.history.append({'role': 'user', 'content': prompt_b})
        
        # also log the messages as events for the transcriptions
        action = {'type': 'send message', 'content': prompt_w}
        self.log_event(from_='GM', to='w', action=action)
        action = {'type': 'send message', 'content': prompt_b}
        self.log_event(from_='GM', to='b', action=action)
    

    def log_eval_assets(self) -> None:
        """Aux to log variables needed for scoring (firstlast specific)"""
        self.log_key('Played turns', self.current_turn)
        self.log_key('Complete turns', self.complete_turns)
        self.log_key(ms.METRIC_ABORTED, self.aborted)
        self.log_key(ms.METRIC_LOSE, self.lose)
        self.log_key(ms.METRIC_REQUEST_COUNT, self.request_counts)
        self.log_key(ms.METRIC_REQUEST_COUNT_PARSED, self.parsed_request_counts)
        self.log_key(ms.METRIC_REQUEST_COUNT_VIOLATED, self.violated_request_counts)


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
        """Add an utterance to the history of a player """
        assert player in ('w', 'b')
        if player == 'w':
            self.white.history.append({'role': role, 'content': utterance})
        else:
            self.black.history.append({'role': role, 'content': utterance})

    @staticmethod
    def parse(utterance: str) -> Tuple[str, str]:
        """Check if the utterance is valid and return move,check(or checkmate)."""
        #print(utterance)
        if len(utterance) < 4:
            return None,None
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
        prompt, raw_answer, answer = player_class(player_class.history,self.current_turn)
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
        #print('-----TURN-----')
        try:
            last_move =  self.board.peek()
            print(f'LASTMOVE {last_move}')
            #print(f'LASTMOVE {type(last_move)}')
            #print(f'SQUARE {last_move.to_square}')
            print(f'self.board\n{self.board}')
            cur_player ='b' if chess.BLACK==self.board.color_at(last_move.to_square) else 'w'
            next_player = 'b' if cur_player=='w' else 'w'
        except:
            cur_player = 'b'
            next_player = 'w'
        
        # get next player reply and add it to its history
        next_move = self._get_utterance(next_player)
        print(f'NEXTMOVE {next_move}')
        
        # add A's reply to B's history
        self._append_utterance(next_move,next_player,'user')
        
        # also add the reply to the transcript
        action = {'type': 'send message', 'content': next_move}
        self.log_event(from_='GM', to=cur_player, action=action)
        move,check = self.parse(next_move)
        
        if move is None:
            return  None
        #print(f'move {next_move}') 
        self.board.push(chess.Move.from_uci(move))

        # check if the game should be aborted or lost
        if not board.is_valid():
            # stop game
            return None

        self.complete_turns += 1




    def compute_scores(self, episode_interactions: Dict) -> None:
        """Compute episode-level and turn-level scores (mandatory)."""
        played_turns = episode_interactions['Played turns']
        complete_turns = episode_interactions['Complete turns']
        # turn 0 was only the initial prompts, so we disregard it here
        reqs = episode_interactions[ms.METRIC_REQUEST_COUNT][1:]
        p_reqs = episode_interactions[ms.METRIC_REQUEST_COUNT_PARSED][1:]
        v_reqs = episode_interactions[ms.METRIC_REQUEST_COUNT_VIOLATED][1:]
        n_turns = len(reqs)

        for turn in range(0, played_turns):
            self.log_turn_score(turn, ms.METRIC_REQUEST_COUNT, reqs[turn])
            self.log_turn_score(turn, ms.METRIC_REQUEST_COUNT_PARSED, p_reqs[turn])
            self.log_turn_score(turn, ms.METRIC_REQUEST_COUNT_VIOLATED, v_reqs[turn])

        aborted = int(episode_interactions[ms.METRIC_ABORTED])
        lose = int(episode_interactions[ms.METRIC_LOSE]) if not aborted else 0
        success =  1 - lose if not aborted else 0
        bench_score = complete_turns / n_turns if not aborted else np.nan
        
        self.log_episode_score(ms.METRIC_ABORTED, aborted)
        self.log_episode_score(ms.METRIC_LOSE, lose)
        self.log_episode_score(ms.METRIC_SUCCESS, success)
        self.log_episode_score(ms.METRIC_REQUEST_COUNT, sum(reqs))
        self.log_episode_score(ms.METRIC_REQUEST_COUNT_PARSED, sum(p_reqs))
        self.log_episode_score(ms.METRIC_REQUEST_COUNT_VIOLATED, sum(v_reqs))
        self.log_episode_score(ms.METRIC_REQUEST_SUCCESS, sum(p_reqs) / sum(reqs))
        self.log_episode_score(ms.BENCH_SCORE, bench_score)




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





