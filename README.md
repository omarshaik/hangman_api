# Hangman

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
 
 
 
## Game Description:
Hangman is a simple word guessing game. Each game begins with a random 'target'
word. 'Guesses' are sent to the `make_move` endpoint which will reply
with either: 'Your guess is correct!', 'Your guess is incorrect', 'you win', or 'game over' (if the maximum
number of attempts is reached).
Many different Hangman games can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`. Individual games are scored by the number of incorrect guesses (attempts) required to correctly guess the word.
Users are ranked by their winning percentage, and then by their number of wins in the case of ties.

## Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

## Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Optionally provide the number of incorrect guesses allowed (default = 5). Also adds a task to a task queue to update the average moves remaining
    for active games.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.

 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Cancel an ongoing game.

 - **get_game_history**
    - Path: 'game/history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForms.
    - Description: Return the game's history, move by move.

 - **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms.
    - Description: Returns all of an individual User's games, including ongoing and completed games.

 - **get_user_rankings**
    - Path: 'games/rankings'
    - Method: GET
    - Parameters: None
    - Returns: UserForms.
    - Description: Returns the user rankings as determined by each user's winning percent. Ties in winning_percent are broken by secondarily sorting by num of user wins.

 - **get_high_scores**
    - Path: 'scores/high'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database ordered by guesses, ascending.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get_active_game_count**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **UserForm**
    - Used to display user rankings (user_name, winning_percent)
 - **UserForms**
    - Multiple UserForm container.
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name, current_word_state, previous_guesses).
 - **GameForms**
    - Multiple GameForm container.
 - **GameHistoryForm**
    - Used to display game history (guess, result)
 - **GameHistoryForms**
    - Multiple GameHistoryForm container.
 - **NewGameForm**
    - Used to create a new game (user_name, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.