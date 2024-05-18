from clemgame.clemgame import GameMaster, GameBenchmark
from typing import List, Dict, Tuple


GAME_NAME='chess_withvariants'


class FirstLastGameBenchmark(GameBenchmark):
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
                           ) -> GameMaster:
        return Chess(experiment, player_backends)
