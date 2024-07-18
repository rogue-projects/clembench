from clemgame.clemgame import GameMaster, GameBenchmark, GameScorer
from typing import List, Dict, Tuple
from clemgame import get_logger
import clemgame.metrics as ms
import random,copy
from games.chess_withvariants.utils.board_functions import *
from games.chess_withvariants.instancegenerator import GAME_NAME
from games.chess_withvariants.players import ChessPlayer
from games.chess_withvariants.utils.general import  get_path_stockfish_bin
import time
import numpy as np
import json 
import statistics 

logger = get_logger(__name__)

import re



class Chess(GameMaster):
    """A game of chess between two players  
    """
    # We only need 2 players: white/black refers to pieces
    # 'programmatic' will be using our default(Stockfish)
    def __init__(self, experiment: Dict, player_backends: List[str]): 
        super().__init__(GAME_NAME, experiment, player_backends)
        # save experiment and player attributes that will be necessary later
        self.name = GAME_NAME
        self.topic = experiment['name']
        if random.randint(0,1): 
            self.target_player = 'w'
            self.white_model = player_backends[0]
            self.black_model = player_backends[1]
        else: 
            self.target_player = 'b'
            self.white_model = player_backends[1]
            self.black_model = player_backends[0]
        self.max_prompt_retries = 4#7
        self.engine =  chess.engine.SimpleEngine.popen_uci(get_path_stockfish_bin())

        # initialise attributes that will be used for the evaluation scores
        self.aborted: bool = False
        self.checkmate: bool = False
        self.stalemate: bool = False
        self.winner: str = '' 
        self.winner_model: str = ''
        self.complete_turns: int = 0

    def setup(self, game_id: int, board: str, n_turns: int, initial_prompt: str, board_reminder: bool) -> None:
        """Setup the episode (mandatory)."""

        self.n_turns = n_turns


        # initialise game variables
        self.board_reminder = board_reminder
        self.current_turn: int = 0
        self.game_id = game_id
        #self.board = chess.variant.HordeBoard(fen=board)
        self.board = chess.Board(fen=board)
        # instantiate both players
        self.white = ChessPlayer(self.white_model, 'w', self.board)
        self.black = ChessPlayer(self.black_model, 'b', self.board)

        self.white_acc = [0.] * (n_turns + 1)
        self.black_acc = [0.] * (n_turns + 1)
        # initialise common metrics
        self.request_counts = [0] * (n_turns + 1)
        self.parsed_request_counts = [0] * (n_turns + 1)
        self.violated_request_counts = [0] * (n_turns + 1)
        self.parse_errors = [0] * (n_turns + 1)
        self.validity_errors = [0] * (n_turns + 1)
        self.retries = 0

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
        prompt_b = initial_prompt + f"\n You're playing black. The first move from white is:\n"

        self.white.history.append({'role': 'user', 'content': prompt_w})
        self.black.history.append({'role': 'user', 'content': prompt_b})
        
        # also log the messages as events for the transcriptions
        action = {'type': 'send message', 'content': prompt_w}
        self.log_event(from_='GM', to='w', action=action)
    

    def log_eval_assets(self) -> None:
        """Aux to log variables needed for scoring (firstlast specific)"""
        self.log_key('Played turns', self.current_turn)
        self.log_key('Complete turns', self.complete_turns)
        self.log_key("Parse errors", self.parse_errors)
        self.log_key("Validity errors", self.validity_errors)
        self.log_key(ms.METRIC_ABORTED, self.aborted)
        self.log_key(ms.METRIC_ABORTED, self.aborted)
        self.log_key("Winner", self.winner)
        self.log_key("Winner model", str(self.winner_model))
        self.log_key("Checkmate", self.checkmate)
        self.log_key("Stalemate", self.stalemate)
        self.log_key(ms.METRIC_REQUEST_COUNT, self.request_counts)
        self.log_key(ms.METRIC_REQUEST_COUNT_PARSED, self.parsed_request_counts)
        self.log_key(ms.METRIC_REQUEST_COUNT_VIOLATED, self.violated_request_counts)
        self.log_key("White acc", self.white_acc)
        self.log_key("Black acc", self.black_acc)
        self.log_key("Target player",self.target_player)
        self.log_key("Retries",self.retries)
        self.log_key("Board reminder",self.board_reminder)



    def play(self) -> None:
        """Play the game until the end (mandatory)."""
        # play the game

        while self.proceed():
            self.current_turn += 1
            # always call log_next_turn when a new turn starts
            self.log_next_turn()
            print(f'------STARTING TURN {self.current_turn}-------')
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
                and not self.checkmate
                and not self.stalemate)

    def _append_utterance(self, utterance: str, player: str, role: str) -> None:
        """Add an utterance to the history of a player """
        assert player in ('w', 'b')
        if player == 'w':
            self.white.history.append({'role': role, 'content': utterance})
        else:
            self.black.history.append({'role': role, 'content': utterance})

    @staticmethod
    def parse(utterance: str) -> bool:
        """Check if the utterance is valid and return move,check(or checkmate)."""
        pattern = re.compile(r'\b[a-h][1-8][a-h][1-8][nbrqNBRQ]?\b')
        return not(pattern.fullmatch(utterance) is None)

    def _get_utterance(self, player: str, parse_error=False, validity_error=False) -> str:
        """Get utterance from a player and log it (firstlast specific)."""
        assert player in ('w', 'b')
        # make an API call (or get a programmatic response) from the player 
        if player == 'w':
            player_class = self.white
        else :
            player_class  = self.black
        last_move = player_class.history[-1]['content']
        
        if  parse_error :
            # Add a message to history from the GM to the player
            msg = 'Your previous move was typed wrongly. Could you respond in the format "n3n4" to move the figure on position n3 to the position n4. Respond exclusively with the next move.'
            action = {'type': 'get message', 'content': msg}
            self.log_event(from_='GM', to=player, action=action)
            self._append_utterance(msg, player, 'user')
        elif  validity_error:
            msg = f'Your previous move was an illegal move that does not conform to how the figure in position "{last_move[:2]}" moves. Respond exclusively with the next move.'
            action = {'type': 'get message', 'content': msg}
            self.log_event(from_='GM', to=player, action=action)
            self._append_utterance(msg, player, 'user')
        elif  self.board_reminder and self.turn != 1:
            msg = f'The board looks like this:\n{self.board}\nNext move:\n {last_move}.'
            action = {'type': 'get message', 'content': msg}
            self.log_event(from_='GM', to=player, action=action)
            self._append_utterance(msg, player, 'user')

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
        

        # Figure out whose turn it is
        next_player = 'w'
        last_player = 'b'
        if (self.current_turn != 1):
            last_move =  self.board.peek()
            #print(f'LASTMOVE {last_move}')
            last_player ='b' if chess.BLACK==self.board.color_at(last_move.to_square) else 'w'
            next_player = 'b' if last_player=='w' else 'w'
        
        
        # get next player reply and add it to its history
        next_move = self._get_utterance(next_player)

        # check for the move
        while  not self.parse(next_move) \
                or not (chess.Move.from_uci(next_move) in self.board.legal_moves) :
            self.retries += 1 
            self.violated_request_counts[self.current_turn] += 1
            if self.retries >=  self.max_prompt_retries:
                self.aborted = True
                action = {'type': 'parse', 'content' : f'Ran out of reprompting attempts'} 
                self.log_event(from_='GM', to='GM', action=action)
                return None
            if not self.parse(next_move):
                self.parse_errors[self.current_turn] += 1
                action = {'type': 'parse', 'content' : f'"{next_move}" does not parse.'} 
                self.log_event(from_='GM', to='GM', action=action)
                next_move = self._get_utterance(next_player,parse_error=True)
            elif not (chess.Move.from_uci(next_move) in self.board.legal_moves) :
                self.validity_errors[self.current_turn] += 1
                action = {'type': 'parse', 'content' : f'"{next_move}" violates movement rules'} 
                self.log_event(from_='GM', to='GM', action=action)
                next_move = self._get_utterance(next_player,validity_error=True)

        # A player has committed to a correct move
        self.parsed_request_counts[self.current_turn] += 1
        # Calculate accuracy of move    
        limit = chess.engine.Limit(depth=10)
        infopre = self.engine.analyse(self.board, limit=limit)
        self.board.push(chess.Move.from_uci(next_move))
        infopost = self.engine.analyse(self.board, limit=limit)
        if next_player == 'w':
            cpscorepre = infopre.get("score").white().score()
            cpscorepost = infopost.get("score").white().score()
        else: 
            cpscorepre = infopre.get("score").black().score()
            cpscorepost = infopost.get("score").black().score()
        print(self.board)
        #print(self.board.is_checkmate()) 
        #print(self.board.is_stalemate()) 
        #print(infopre) 
        #print(infopost) 
        #print(cpscorepre) 
        #print(cpscorepost) 
        if not(cpscorepre is None or cpscorepost is None): 
            winchance_premove = 100 / (1 + np.exp(-0.00368208 * cpscorepre))
            winchance_postmove = 100 / (1 + np.exp(-0.00368208 * cpscorepost))
            
            acc = 103.1668 * np.exp(-0.04354 * (winchance_premove - winchance_postmove)) - 3.1669
            if next_player == 'w':
                self.white_acc[self.current_turn] = acc
            else: 
                self.black_acc[self.current_turn] = acc
        else: # Mates dont have a score
            if next_player == 'w':
                self.white_acc[self.current_turn] = -1
            else: 
                self.black_acc[self.current_turn] = -1

        
        # add A's reply to B's 
        # also add the reply to the transcript
        if self.current_turn ==1:
        #A bit of prompt magic, adding initial white move to the history of black prompt
            self.black.history[-1]['content'] += f'\n{next_move}'
            action = {'type': 'send message', 'content': self.black.history[-1]['content']}
            self.log_event(from_='GM', to='b', action=action)
        else :
            self._append_utterance(next_move,last_player,'user')
            action = {'type': 'send message', 'content': next_move}
            self.log_event(from_='GM', to=last_player, action=action)

        self.complete_turns += 1

        if self.board.is_checkmate():
            self.checkmate = True
            if self.board.outcome().winner == chess.BLACK:
                self.winner = 'b'
                self.winner_model = self.black_model
            else:
                self.winner = 'w'
                self.winner_model = self.white_model
            return None
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            self.stalemate = True
            self.winner = 'draw'
            return None


class ChessGameScorer(GameScorer):

    def __init__(self, name: str, experiment: Dict, game_instance: Dict):
        super().__init__(name, experiment,game_instance)
        self.experiment = experiment
        self.game_instance = game_instance
        """ Stores values of score computation """
        self.scores = {
            "turn scores": {},
            "episode scores": {},
        }

    """---------------------------"""
    """ LOGGING/WRITING FUNCTIONS """
    """---------------------------"""
    
    def store_scores(self, results_root: str, dialogue_pair: str, game_record_dir: str):
        self.store_results_file(self.scores, "scores.json",
                                dialogue_pair=dialogue_pair,
                                sub_dir=game_record_dir,
                                root_dir=results_root)


    def log_turn_score(self, turn_idx, score_name, score_value):
        if isinstance(score_value, bool):
            self.logger.warning(f"{self.name}: Score {score_name} value is boolean, this can break the eval!")
        if turn_idx not in self.scores["turn scores"]:
            self.scores["turn scores"][turn_idx] = {}
        if score_name in self.scores["turn scores"][turn_idx]:
            self.logger.warning(f"{self.name}: Score {score_name} overwritten at turn {turn_idx}!")
        self.scores["turn scores"][turn_idx][score_name] = score_value
        self.logger.info(f"{self.name}: Logged turn {turn_idx} score {score_name}={score_value}.")

    def log_episode_score(self, score_name, score_value):
        if score_name in self.scores["episode scores"]:
            self.logger.warning(f"{self.name}: Episode score {score_name} overwritten!")
        self.scores["episode scores"][score_name] = score_value
        self.logger.info(f"{self.name}: Logged episode score {score_name}={score_value}.")


    """----------------------------"""
    """ COMPUTING METRIC FUNCTIONS """
    """----------------------------"""

    def compute_scores(self, episode_interactions: Dict) -> None:
        self.score_turns(episode_interactions)
        self.score_game(episode_interactions)
    
    def get_target_turn_req_metrics(self, episode_interactions: Dict):
        """ 
        Support function to get ONLY the metrics from the one player that
        was set as target. Should be player_backends[0]
        """
        # turn 0 was only the initial prompts, so we disregard it here
        reqs = episode_interactions[ms.METRIC_REQUEST_COUNT][1:]
        p_reqs = episode_interactions[ms.METRIC_REQUEST_COUNT_PARSED][1:]
        v_reqs = episode_interactions[ms.METRIC_REQUEST_COUNT_VIOLATED][1:]
        parse_err = episode_interactions['Parse errors']
        val_err= episode_interactions['Validity errors']
        if episode_interactions['Target player'] == 'w':# we only want white
            reqs = reqs[::2]       
            p_reqs = p_reqs[::2]    
            v_reqs = v_reqs[::2]   
            parse_err= parse_err[::2]        
            val_err= val_err[::2]        
        else:  # we only want black
            reqs = reqs[1::2]      
            p_reqs = p_reqs[1::2] 
            v_reqs = v_reqs[1::2]
            parse_err= parse_err[1::2]        
            val_err= val_err[1::2]        
        limit = episode_interactions['Played turns']
        reqs = reqs[:limit]
        p_reqs= p_reqs[:limit]
        v_reqs = v_reqs[:limit]
        parse_err = parse_err[:limit]
        val_err = val_err[:limit]
        # accuracy metrics
        if episode_interactions['Target player'] == 'w':# we only want white
            acc = episode_interactions['White acc'][::2]
        else:
            acc = episode_interactions['Black acc'][1::2]
        return reqs,p_reqs,v_reqs,parse_err,val_err,acc


    def score_turns(self, episode_interactions: Dict) -> None:
        # response metrics
        reqs,p_reqs,v_reqs,parse_err,val_err,acc= self.get_target_turn_req_metrics(episode_interactions)
        played_turns = len(reqs)
        for turn in range(played_turns):
            self.log_turn_score(turn, ms.METRIC_REQUEST_COUNT, reqs[turn])
            self.log_turn_score(turn, ms.METRIC_REQUEST_COUNT_PARSED, p_reqs[turn])
            self.log_turn_score(turn, ms.METRIC_REQUEST_COUNT_VIOLATED, v_reqs[turn])
            self.log_turn_score(turn, "Parse errors", parse_err[turn])
            self.log_turn_score(turn, "Validity errors", val_err[turn])
            self.log_turn_score(turn, "Accuracy", acc[turn])


    def score_game(self, episode_interactions: Dict) -> None:
        reqs,p_reqs,v_reqs,parse_err,val_err,acc = self.get_target_turn_req_metrics(episode_interactions)
        aborted = int(episode_interactions[ms.METRIC_ABORTED])
        stalemate = int(episode_interactions["Stalemate"]) if not aborted else 0
        checkmate = int(episode_interactions["Checkmate"]) if not aborted else 0
        target_player = episode_interactions['Target player']
        success =  1 - aborted

        winner = episode_interactions['Winner']
        winner_model = episode_interactions['Winner model']
        lose = (winner==target_player) and not stalemate
        retries =  sum(parse_err)+ sum(val_err)

        #complete_turns = episode_interactions['Complete turns']
        parse_failrate = 1 if sum(reqs) == 0 else (sum(val_err)+sum(parse_err))/sum(reqs)
        val_failrate = 1 if sum(reqs) == 0 else sum(val_err)/sum(reqs)
        acc = [i for i in acc if not i  in [-1.,0.]]
        avg_acc = np.mean([i/max(acc) for i in acc])
        # Seems good enough until I care to make something better
        bench_list = [1.-parse_failrate,1.-val_failrate,avg_acc]
        #print(bench_list)
        bench_score = statistics.harmonic_mean(bench_list) if not aborted else 0.
        #print(type(bench_score))
        #print(bench_score)
        self.log_episode_score(ms.METRIC_ABORTED, aborted)
        self.log_episode_score(ms.METRIC_SUCCESS, success)
        self.log_episode_score(ms.METRIC_LOSE, lose)
        self.log_episode_score("Checkmate", checkmate)
        self.log_episode_score("Stalemate", stalemate)
        #self.log_episode_score("Target Player", target_player)
        #self.log_episode_score("Winner", winner)
        #self.log_episode_score("Winner model", winner_model)
        self.log_episode_score("Accuracy",avg_acc)
        #self.log_episode_score("Retries", retries)
        self.log_episode_score(ms.BENCH_SCORE, bench_score)
        self.log_episode_score(ms.METRIC_REQUEST_COUNT, sum(reqs))
        self.log_episode_score(ms.METRIC_REQUEST_COUNT_PARSED, sum(p_reqs))
        self.log_episode_score(ms.METRIC_REQUEST_COUNT_VIOLATED, sum(v_reqs))
        self.log_episode_score(ms.METRIC_REQUEST_SUCCESS, 0 if sum(reqs) == 0 else sum(p_reqs) / sum(reqs))
        self.log_episode_score("Parse Rate",1 - parse_failrate)
        self.log_episode_score("Validity Rate",1 - val_failrate)




class ChessBenchmark(GameBenchmark):
    """Integrate the game into the benchmark run."""
    def __init__(self):
        super().__init__(GAME_NAME)

    # defines whether the game is single player or not
    def is_single_player(self):
        return False

    # add a description of your game
    def get_description(self):
        return "Normal chess combined with randomized amount and position of figures. Player 1 is the one whose metrics will be returned."

    # copy this, replacing the name of the game master in the return statement
    def create_game_master(self,
                           experiment: Dict,
                           player_backends: List[str]
                           ) -> Chess:
        return Chess(experiment, player_backends)

    def create_game_scorer(self, experiment: Dict, game_instance: Dict) -> GameScorer:
        return ChessGameScorer(GAME_NAME,experiment=experiment, game_instance=game_instance)




