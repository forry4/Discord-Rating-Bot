# Discord-Rating-Bot
Discord bot with various utilities

Integrates Microsoft's TrueSkill algorithm with Discord's REST API to allow users to submit results from games, view leaderboards, search for users, organize ranked lobbies, and more.

Game Submission:
!submit allows for game submissions with error catching for improper formatting and automatic detection for game type. Users receive information about post-lobby standings, rating changes, and are automatically assigned roles based of visual skill rating.

Leaderboards:
Leaderboards for different game types are updated automatically after each game submission, with minimum requirements for users to appear on leaderboards. Displays both standard leaderboard as well as one with additional stats (mu, sigma, games played)

Automatic Role Detection:
Roles for your skill rating are automatically assigned after game submissions given a minimum number of games for placements have been completed. The Ranked role can also be self-assigned by users by reacting to the pinned message in the #role-select channel

Ranked Quality Assurance:
Ranked matches only count if two players are within a small enough elo range to ensure the system is not abused by strong players always winning against much weaker ones.

Fast Elo Calculation:
Upon sartup, the code will run through the full csv of every game id to sequentially calculate mu and sigma for every player after every game. Additional csv files with mu and sigma data are stored for quick calculation post game submission.

See https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/ for more info on Microsoft's TrueSkill algorithm.
