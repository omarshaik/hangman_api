"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

words = 'ant baboon badger bat bear beaver camel cat clam cobra cougar coyote crow deer dog donkey duck eagle ferret fox frog goat goose hawk lion lizard llama mole monkey moose mouse mule newt otter owl panda parrot pigeon python rabbit ram rat raven rhino salmon seal shark sheep skunk sloth snake spider stork swan tiger toad trout turkey turtle weasel whale wolf wombat zebra'.split()

class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    wins = ndb.IntegerProperty(required=True, default=0)
    losses = ndb.IntegerProperty(required=True, default=0)
    winning_percent = ndb.FloatProperty(required=True, default=0.0)

    def to_form(self):
        return UserForm(user_name=self.name, winning_percent=self.winning_percent)

class Game(ndb.Model):
    """Game object"""
    target = ndb.StringProperty(required=True)
    current_word_state = ndb.StringProperty(required=True)
    previous_guesses = ndb.StringProperty()
    history = ndb.JsonProperty()
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True, default=5)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')

    @classmethod
    def new_game(cls, user, attempts):
        """Creates and returns a new game"""
        targ = random.choice(words)
        word_state = ""
        for char in targ:
            word_state += "-"
        game = Game(user=user,
                    target=targ,
                    current_word_state=word_state,
                    previous_guesses="",
                    history=[],
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    game_over=False)
        game.put()
        return game

    def history_to_form(self):
        moves = []
        for move in self.history:
            guess = move["guess"]
            result = move["result"]
            game_history_form = GameHistoryForm(guess=guess, result=result)
            moves.append(game_history_form)

        return GameHistoryForms(moves=moves)

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.message = message
        form.current_word_state = self.current_word_state
        form.previous_guesses = self.previous_guesses
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=self.attempts_allowed - self.attempts_remaining)
        score.put()
        # Update the user's wins or losses total
        user = self.user.get()
        if won:
            user.wins += 1
        else:
            user.losses += 1
        user.winning_percent = user.wins/float(user.wins + user.losses)
        user.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guesses = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guesses=self.guesses)

class UserForm(messages.Message):
    """UserForm for outbound user information"""
    user_name = messages.StringField(1, required=True)
    winning_percent = messages.FloatField(2, required=True)

class UserForms(messages.Message):
    """Return multiple UserForms"""
    items = messages.MessageField(UserForm, 1, repeated=True)

class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)
    current_word_state = messages.StringField(6, required=True)
    previous_guesses = messages.StringField(7, required=False)

class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)

class GameHistoryForm(messages.Message):
    guess = messages.StringField(1, required=True)
    result = messages.StringField(2, required=True)

class GameHistoryForms(messages.Message):
    moves = messages.MessageField(GameHistoryForm, 1, repeated=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    attempts = messages.IntegerField(4, default=5)

class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)

class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)

class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
