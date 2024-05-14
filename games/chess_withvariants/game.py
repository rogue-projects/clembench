from typing import List, Dict, Tuple

from backends import Model, ModelSpec, get_model_for, load_model_registry



logger = get_logger(__name__)  # clem logging






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
