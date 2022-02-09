# SAP_Bot.py
import os
import discord
import pandas as pd
from csv import writer
from dotenv import load_dotenv
from discord.ext import commands
from IPython.display import display
from trueskill import Rating, rate

#load in the token secret
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

def getGameID():
    #open the file
    with open('ranking.csv','r') as file: 
        data = file.readlines()
        #return current game number as 0 if data is empty
        if len(data)==1:
            return 0
        #return latest value for game number
        return data[-1].split(',')[1]

def getPlayers():
    # Fetch the data
    df_raw = pd.read_csv('ranking.csv')

    # Create a holding DataFrame for our TrueRank
    df_truerank_columns = ['game_id', 'player_id', 'position', 'mu', 'sigma', 'post_mu', 'post_sigma']
    df_truerank = pd.DataFrame(columns=df_truerank_columns)

    # Use a sample of 10000
    df = df_raw.tail(10000)

    # Group by the game_id
    games = df.groupby('game_id')

    # Now iterate the games
    for game_id, game in games:
        # Setup lists so we can zip them back up at the end
        trueskills = []    
        player_ids = []
        game_ids = []  
        mus = []    
        sigmas = []
        post_mus = []
        post_sigmas = []

        # Now iterate over each player in a game
        for index, row in game.iterrows():

            # Create a game_ids arary for zipping up
            game_ids.append(game_id)

            # Now push the player_id onto the player_ids array for zipping up
            player_ids.append(row['player_id'])

            # Get the players last game, hence tail(1)
            filter = (df_truerank['game_id'] < game_id) & (df_truerank['player_id'] == row['player_id'])                            
            df_player = df_truerank[filter].tail(1)

            # If there isnt a game then just use the TrueSkill defaults
            if (len(df_player) == 0):
                mu = 25
                sigma = 8.333
            else:
                # Otherwise get the mu and sigma from the players last game
                row = df_player.iloc[0]
                mu = row['post_mu']
                sigma = row['post_sigma']

            # Keep lists of pre mu and sigmas
            mus.append(mu)
            sigmas.append(sigma)

            # Now create a TrueSkull Rating() class and pass it into the trueskills dictionary
            trueskills.append(Rating(mu=mu, sigma=sigma))

        # Use the positions as ranks, they are 0 based so -1 from all of them
        ranks = [x - 1 for x in list(game['position'])]

        # Create tuples out of the trueskills array
        trueskills_tuples = [(x,) for x in trueskills]

        try:
            # Get the results from the TrueSkill rate method
            results = rate(trueskills_tuples, ranks=ranks)

            # Loop the TrueSkill results and get the new mu and sigma for each player
            for result in results:
                post_mus.append(round(result[0].mu, 2))
                post_sigmas.append(round(result[0].sigma, 2))        
        except:
            # If the TrusSkill rate method blows up, just use the previous 
            # games mus and sigmas
            post_mus = mus
            post_sigmas = sigmas

        # Change the positions back to non 0 based
        positions = [x + 1 for x in ranks]

        # Now zip together all our lists 
        data = list(zip(game_ids, player_ids, positions, mus, sigmas, post_mus, post_sigmas))

        # Create a temp DataFrame the same as df_truerank and add data to the DataFrame
        df_temp = pd.DataFrame(data, columns=df_truerank_columns)

        # Add df_temp to our df_truerank
        df_truerank = df_truerank.append(df_temp)

    #display the dataframe
    display(df_truerank)

    #create dictionary for player: 0, Rating, Games, 0, Mu, Sigma
    players = df_truerank.set_index('player_id').T.to_dict('list')
    for player in players:
        players.get(player)[0] = 0
        players.get(player)[1] = 3.6666 + players.get(player)[4] - 2 * players.get(player)[5]
        players.get(player)[2] = df_truerank['player_id'].value_counts()[player]
        players.get(player)[3] = 0
    players = {k: v for k, v in sorted(players.items(), key=lambda item: item[1][1], reverse=True)}

    print(players)

    return players

players = {}

def setPlayers():
    global players
    players = getPlayers()

setPlayers()

#give proper intents for bot to detect members
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

#confirm bot connection
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

#gives role to users who react
@bot.event
async def on_raw_reaction_add(payload):
    message_id = payload.message_id
    #check users are reacting to certain message
    if message_id == 938584658105466921:
        #get the id of the server
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g : g.id == guild_id, bot.guilds)
        #see if users reacted with certain emote
        if payload.emoji.name == 'monkey':
            #set the role to be added as 'Ranked'
            role = discord.utils.get(guild.roles, name='Ranked')
        else:
            role = discord.utils.get(guild.roles, name=payload.emoji.name)
        #if we got a role from the previous step, add it
        if role is not None:
            #get the id of the member that reacted
            member = discord.utils.find(lambda m : m.id == payload.user_id, guild.members)
            if member is not None:
                #add the role to the member
                await member.add_roles(role)
                print((f'{role} added to {member}'))
            else:
                print("member not found")
        else:
            print("role not found")
    return

#removes role to users who un-react
@bot.event
async def on_raw_reaction_remove(payload):
    message_id = payload.message_id
    #check users are reacting to certain message
    if message_id == 938584658105466921:
        #get the id of the server
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g : g.id == guild_id, bot.guilds)
        #see if users reacted with certain emote
        if payload.emoji.name == 'monkey':
            #set the role to be added as 'Ranked'
            role = discord.utils.get(guild.roles, name='Ranked')
        else:
            role = discord.utils.get(guild.roles, name=payload.emoji.name)
        #if we got a role from the previous step, add it
        if role is not None:
            #get the id of the member that reacted
            member = discord.utils.find(lambda m : m.id == payload.user_id, guild.members)
            if member is not None:
                #remove the role from the member
                await member.remove_roles(role)
                print((f'{role} removed from {member}'))
            else:
                print("member not found")
        else:
            print("role not found")
    return

#print all members in the server
@bot.command()
async def members(ctx):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        members = {}
        #create dictionary of member ids and their discord name (Donutseeds#7704 for example)
        for member in ctx.guild.members:
            members[member.id] = str(member)
        print(members)
    return members

#print all members in the server
@bot.command()
async def players1(ctx):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        #print out the players dictionary
        # players = getPlayers()
        print(players)
    return

#return dictionary of member ids and member names
def getMembers(ctx):
    members={}
    #create dictionary of member ids and their discord display name (Donutseeds for example)
    for member in ctx.guild.members:
        members[member.id] = member.display_name
    return members

#submit new lobby results to spreadsheet
@bot.command()
async def submit(ctx, *message):
    #check that we're in the right channel
    if ctx.channel.id == 937998936269000704 or ctx.channel.id == 940007288012415106:
        #get name of user submitting
        author=ctx.author.name
        #get current gameID
        gameID = int(getGameID())+1
        # players = getPlayers()
        #check to see if formatting is valid
        try:
            #convert tuple to list
            message = list(message)
            print(f'list message: {message}')
            #get the dictionary of member ids : display names
            members = getMembers(ctx)
            #open csv file to append new data
            with open('ranking.csv', 'a', newline='') as ranking:
                writer_object = writer(ranking)
                #keep track of players in the submitted lobby
                currentPlayers={}
                #loop through each player in the lobby
                for i in range(0,len(message),2):
                    #get the discord id from the submitted ping
                    #when certain members use the search command, their message differs in length
                    if len(message[i][3:-1]) == 18:
                        username = f'{message[i][3:-1]}#'
                        print(f'18: {username}')
                    else:
                        username = f'{message[i][2:-1]}#'
                        print(f'not 18: {username}')
                    print(f'username: {username}')
                    line = []
                    #add the name, gameID, and placement to the array
                    line.append(username)
                    line.append(gameID)
                    line.append(message[i+1])
                    #add the current player's rating (prior to this submission) to the dictionary
                    try:
                        currentPlayers[username] = [players.get(username)[1],0]
                    #if this is their first game, give them a base rating (1200)
                    except:
                        currentPlayers[username] = [3.6666+25-2*8.3333,0]
                    print(line)
                    #append line to csv file
                    writer_object.writerow(line)
                ranking.close()
            #update players
            setPlayers()
            #confirmation message
            await ctx.channel.send(f'Thank you {author} for submitting gameID {gameID}!')
        except Exception as e:
            #catch error
            print(e)
            #make pandas dataframe
            df = pd.read_csv('ranking.csv')
            #keep rows where gameID doesnt match input
            df = df[df['game_id'] != int(gameID)]
            #save csv without indexes
            df.to_csv('ranking.csv', index=False)
            #update players
            setPlayers()
            await ctx.channel.send(f'Error submitting gameID {gameID}!')
            return
        print(f'updated players: {players}')
        for player in currentPlayers:
            #set the current players new rating after the lobby
            print(f'old : new {currentPlayers.get(player)[0]} : {players.get(player)[1]}')
            currentPlayers.get(player)[1] = players.get(player)[1]
        #sort the list of current players by their new rating
        currentPlayers = {k: v for k, v in sorted(currentPlayers.items(), key=lambda item: item[1][1], reverse=True)} 
        print(f'currentPlayers: {currentPlayers}')
        playerRank = (f'```\n#  Player              Rating\n')
        i=1
        #return info on the rating change for players in the lobby
        for player in players:
            if player in currentPlayers:
                print(f'player: {player}')
                print(players.get(str(player)))
                #return the matching rank
                playerRank += (f'{i}   ')
                #remove spaces from string the longer thier rank index is
                for j in range(len(str(i))):
                    playerRank = playerRank[:-1]
                #add username to the string
                playerRank += members.get(int(player[:-1]))
                #add spaces for proper allignment
                for k in range(20 - len(members.get(int(player[:-1])))):
                    playerRank += ' '
                #get the new rating and calculate the change
                rating = 100*currentPlayers.get(player)[1]
                change = rating - 100*currentPlayers.get(player)[0]
                #add change to the string
                playerRank += (f'{int(rating)}(')
                if change > 0:
                    playerRank += '+'
                playerRank += (f'{int(change)})\n')                  
            i+=1
        await ctx.channel.send(f'{playerRank}\n```')
        #add/remove role to members above/below 30 elo threshold
        for player in currentPlayers:
            #match the player name with their member object
            for member in ctx.guild.members:
                if member.id == int(player[:-1]):
                    #get role to add/remove
                    role1 = discord.utils.get(ctx.author.guild.roles, name = "High Elo Gamer")
                    role2 = discord.utils.get(ctx.author.guild.roles, name = "Mid Elo Gamer")
                    #add high elo role if above 30, add mid elo role if above 27.5
                    if players.get(player)[1]<30:
                        await member.remove_roles(role1)
                        if players.get(player)[1]<27.5:
                            await member.remove_roles(role2)
                        else:
                            await member.add_roles(role2)
                    else:
                        await member.remove_roles(role2)
                        await member.add_roles(role1)
                    break
    return

#command to replace certain cells in the excel spreadsheet; change the function as necessary
@bot.command()
async def replaceAll(ctx):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        # reading the CSV file
        with open("ranking.csv", "r") as text:
            #combines file into a string
            text = ''.join([i for i in text]) 
            # search and replace the contents
            for member in ctx.guild.members:
                if str(member).strip() in text:
                    text = text.replace((str(member)), f"{member.id}#")
            # write to output file
            x = open("ranking.csv","w")
            x.writelines(text)
            x.close()
    return

#replace an occurence in the spreadsheet with different text
@bot.command()
async def replace(ctx, nameOld, nameNew):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        # reading the CSV file
        with open("ranking.csv", "r") as text:
            #combines file into a string
            text = ''.join([i for i in text]) 
            # search and replace the contents
            text = text.replace(nameOld, nameNew)
            # write to output file
            x = open("ranking.csv","w")
            x.writelines(text)
            x.close()
    return

#remove a game from the spreadsheet
@bot.command()
async def deleteGame(ctx, gameID):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        #make pandas dataframe
        df = pd.read_csv('ranking.csv')
        #keep rows where gameID doesnt match input
        df = df[df['game_id'] != int(gameID)]
        #save csv without indexes
        df.to_csv('ranking.csv', index=False)
        #update players
        setPlayers()
        await ctx.channel.send(f'{ctx.author} removed gameID {gameID}!')
    return

#check what rank a specified user is
@bot.command()
async def search(ctx, message):
    #get list of members
    members = getMembers(ctx)
    print(f'len message: {len(message[3:-1])}')
    #for some reason when certain members use the search command, their message differs in length
    if len(message[3:-1]) == 18:
        username = f'{message[3:-1]}#'
        print(f'18: {username}')
    else:
        username = f'{message[2:-1]}#'
        print(f'not 18: {username}')
    #update list of players
    # players = getPlayers()
    i=1
    #check to see if any player in the system matches the user's name
    for player in players:
        #check if searched player is in the system
        if player == username:
            #return the matching rank and elo
            playerRank = (f'```\n#  Player              Rating\n{i}   ')
            #account for length of index
            for j in range(len(str(i))):
                playerRank = playerRank[:-1]
            #add player name to string
            playerRank += members.get(int(player[:-1]))
            #account for length of name
            for j in range(20 - len(members.get(int(player[:-1])))):
                playerRank += ' '
            #add player rating to string
            playerRank += (f'{int(100*players.get(player)[1])}\n```')
            await ctx.channel.send(playerRank)
            return
        i+=1
    #inform user if no match was found
    await ctx.channel.send(f'Could not find {members.get(int(username[:-1]))} in the rankings')
    return

#check what rank a specified user is and give extended stats
@bot.command()
async def searchstats(ctx, message):
    #get name of specified user
    members = getMembers(ctx)
    print(f'len message: {len(message[3:-1])}')
    #when certain members use the search command, their message differs in length
    if len(message[3:-1]) == 18:
        username = f'{message[3:-1]}#'
        print(f'18: {username}')
    else:
        username = f'{message[2:-1]}#'
        print(f'not 18: {username}')
    #update list of players
    # players = getPlayers()
    i=1
    #check to see if any player in the system matches the user's name
    for player in players:
        if player == username:
            #return the matching rank and elo
            playerRank = (f'```\n#  Player              Rating  μ     σ    games\n{i}   ')
            #account for length of index
            for j in range(len(str(i))):
                playerRank = playerRank[:-1]
            #add player name to string
            playerRank += members.get(int(player[:-1]))
            #account for length of player name
            for j in range(20 - len(members.get(int(player[:-1])))):
                playerRank += ' '
            #add player stats to string
            index, rating, games, blah, mu, sigma = players.get(player)
            playerRank += (f'{int(rating*100)}    {int(mu*100)}  {int(sigma*100)}  {games}\n```')
            await ctx.channel.send(playerRank)
            return
        i+=1
    #inform user if no match was found
    await ctx.channel.send(f'Could not find {members.get(int(username[:-1]))} in the rankings')
    return

#check top 10 players on the leaderboard
@bot.command()
async def leaderboard(ctx):
    #check if there is no data in the spreadsheet
    if getGameID() == 0:
        await ctx.channel.send('No data in the leaderboard')
    #get list of players and members
    # players = getPlayers()
    members = getMembers(ctx)
    message = '```\n#  Player              Rating\n'
    i=1
    #list off the first 10 players and their Elos
    for player in players:
        message += (f'{i}   ')
        #account for length of index
        for j in range(len(str(i))):
            message = message[:-1]
        #add player name to string
        message += members.get(int(player[:-1]))
        #account for length of player name
        for j in range(20 - len(members.get(int(player[:-1])))):
            message += ' '
        #add player rating to string
        message += (f'{int(100*players.get(player)[1])}\n')
        #stop after printing the first 10 entries
        if i==10:
            break
        i+=1
    await ctx.channel.send(message + '\n```')
    return

#check top 10 players on the leaderboard and give extended stats
@bot.command()
async def leaderboardstats(ctx):
    #check if there is no data in the spreadsheet
    if getGameID() == 0:
        await ctx.channel.send('No data in the leaderboard')
    #get list of players and members
    # players = getPlayers()
    members = getMembers(ctx)
    message = '```\n#  Player              Rating  μ     σ    games\n'
    i=1
    #list off the first 10 players and their Elos
    for player in players:
        message += (f'{i}   ')
        #account for length of index
        for j in range(len(str(i))):
            message = message[:-1]
        #add player name to string
        message += members.get(int(player[:-1]))
        #account for length of player name
        for j in range(20 - len(members.get(int(player[:-1])))):
            message += ' '
        #add player stats to string
        index, rating, games, blah, mu, sigma = players.get(player)
        message += (f'{int(rating*100)}    {int(mu*100)}  {int(sigma*100)}  {games}\n')
        #stop after first 10 entries
        if i==10:
            break
        i+=1
    await ctx.channel.send(message + '\n```')
    return

bot.run(TOKEN)
