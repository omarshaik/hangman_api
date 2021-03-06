# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, UserForms, GameHistoryForms
from utils import *

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
HIGH_SCORES_REQUEST = endpoints.ResourceContainer(number_of_results=messages.IntegerField(1))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        game = Game.new_game(user.key, request.attempts)

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Hangman!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game.game_over:
            return game.to_form('Game already over!')
        guess = request.guess.lower()
        # Check for invalid inputs and raise an exception as necessary
        made_illegal_move = False
        if not guess.isalpha():
          msg = 'Please enter a letter or word.'
          made_illegal_move = True
        elif game.previous_guesses is not None and guess in game.previous_guesses.split(",") :
          msg = 'You have already guessed that. Choose again.'
          made_illegal_move = True
        elif len(guess) > len(game.target):
          msg = 'Your guess had too many letters in it.'
          made_illegal_move = True

        if made_illegal_move:
          game.history.append({'guess': guess, 'result': msg})
          game.put()
          raise endpoints.BadRequestException(msg)

        if guess == game.target:
          msg = 'You guessed correctly! You win!'
          game.current_word_state = game.target
          game.history.append({'guess': guess, 'result': msg})
          game.put()
          game.end_game(True)
          return game.to_form(msg)

        if guess in game.target:
          indices = find(game.target, guess)
          new_state = ""
          for idx, char in enumerate(game.current_word_state):
            if idx in indices:
              new_state += guess
            else:
              new_state += char
          game.current_word_state = new_state
          msg = "You guessed correctly!"
          if game.current_word_state == game.target:
            msg += ' You win!'
            game.history.append({'guess': guess, 'result': msg})
            game.put()
            game.end_game(True)
            return game.to_form(msg)
        else:
          msg = "You guessed incorrectly."
          game.attempts_remaining -= 1

        if not game.previous_guesses or len(game.previous_guesses) == 0:
          game.previous_guesses = guess
        else:
          game.previous_guesses +=  "," + guess
        msg += " Here's the current state of the word: %s" % game.current_word_state
        if game.attempts_remaining < 1:
          msg += ' Game over!'
          game.history.append({'guess': guess, 'result': msg})
          game.put()
          game.end_game(False)
          return game.to_form(msg)
        else:
          game.history.append({'guess': guess, 'result': msg})
          game.put()
          return game.to_form(msg)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        """Cancel an ongoing game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
          raise endpoints.NotFoundException('Game not found!')
        if game.game_over:
            return game.to_form('This game is already over!')
        game.game_over = True
        game.key.delete()
        return game.to_form("The game was deleted!")

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForms,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return the game's history, move by move."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
          if game.history:
            return game.history_to_form()
          else:
            raise endpoints.NotFoundException('This game has no history yet!')
        else:
          raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's games, including ongoing and completed games."""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        games = Game.query(Game.user == user.key)
        return GameForms(items=[game.to_form("") for game in games])

    @endpoints.method(response_message=UserForms,
                      path='games/rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Returns the user rankings as determined by each user's winning percent. 
        Ties in winning_percent are broken by secondarily sorting by num of user wins.
        """
        users = User.query().order(-User.winning_percent, -User.wins)
        if not users:
            raise endpoints.NotFoundException('There are no users!')
        return UserForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=HIGH_SCORES_REQUEST,
                      response_message=ScoreForms,
                      path='scores/high',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return high scores."""
        if request.number_of_results > 0:
          scores = Score.query().order(Score.guesses).fetch(request.number_of_results)
        else:
          scores = Score.query().order(Score.guesses)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                        for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([HangmanApi])
