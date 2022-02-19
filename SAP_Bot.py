# SAP_Bot.py
import os
import discord
import math
import csv
import pandas as pd
from datetime import date
from datetime import datetime
from timeit import default_timer as timer
from csv import writer
from dotenv import load_dotenv
from discord.ext import commands
from IPython.display import display
from trueskill import Rating, rate, rate_1vs1

#load in the token secret
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

players = {}

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

def setPlayers(mode):

    global players

    # Fetch the data
    df_raw = pd.read_csv(f'ranking{mode}.csv')

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

        # print(f'game_id: {game_id} \ngame: {game}')

        # Now iterate over each player in a game
        for index, row in game.iterrows():

            # Create a game_ids array for zipping up
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

# 3.6666 + playersMode.get(player)[4] - 2 * playersMode.get(player)[5]
# 3.6666 + playersMode.get(player)[4] - 3 * playersMode.get(player)[5]
# 3.6666 + playersMode.get(player)[4] - (3 - (0.1 * min(10,playersMode.get(player)[0]))) * playersMode.get(player)[5]
    
    #create dictionary for player: games, rating1, rating2, rating3, mu, sigma
    playersMode = df_truerank.set_index('player_id').T.to_dict('list')
    for player in playersMode:
        playersMode.get(player)[0] = df_truerank['player_id'].value_counts()[player]
        playersMode.get(player)[1] = 3.6666 + playersMode.get(player)[4] - (3 - (0.1 * min(10,playersMode.get(player)[0])))* playersMode.get(player)[5]
        playersMode.get(player)[2] = 3.6666 + playersMode.get(player)[4] - 3 * playersMode.get(player)[5]
        playersMode.get(player)[3] = 3.6666 + playersMode.get(player)[4] - 2 * playersMode.get(player)[5]
    #sort players by their rating
    playersMode = {k: v for k, v in sorted(playersMode.items(), key=lambda item: item[1][1], reverse=True)}
    players[mode] = playersMode
    
    playersToCSV(players, mode)
    getPlayers(mode)
    
    return players

def playersToCSV(players, mode):
    df = pd.DataFrame.from_dict(players[mode], orient = 'index', columns = ['games', 'rating', 'mu', 'sigma', 'post_mu', 'post_sigma'])
    df.to_csv (f'rating{mode}.csv', index = True, header=True)
    return

def getPlayers(mode):
    global players
    df = pd.read_csv(f'rating{mode}.csv', header = 0, names = ['player_id', 'games', 'rating', 'mu', 'sigma', 'post_mu', 'post_sigma'])
    players[mode] = df.set_index('player_id').T.to_dict('list')
    return players

def ratePlayers(currentPlayers, mode):
    global players
    print(f'currentPlayers pre: {currentPlayers}')
    players = getPlayers(mode)
    trueskills = []
    ranks = []
    for player in currentPlayers:
        print(f'old player: {player} ::: {players[mode].get(player)}')
        #make rating objects of players' most recent mu and sigma
        try:
            trueskills.append(Rating(mu=players[mode].get(player)[4], sigma=players[mode].get(player)[5]))
        #if the player isn't in the dictionary:
        except Exception as e:
            print(f'error1: {e}')
            trueskills.append(Rating(mu=25, sigma=8.3333))
        ranks.append(currentPlayers.get(player))
    #get results from trueskill algorithm
    trueskills_tuples = [(x,) for x in trueskills]
    results = rate(trueskills_tuples, ranks=ranks)
    i=0
    for player in currentPlayers:
        mu = results[i][0].mu
        sigma = results[i][0].sigma
        #increment games by 1, set new rating, set old mu and sigma, set new mu and sigma
        try:
            players[mode][player] = [players[mode].get(player)[0]+1, 3.6666 + mu - (2 * sigma), players[mode].get(player)[4], players[mode].get(player)[5], mu, sigma]
        #if the player isn't in the dictionary yet:
        except Exception as e:
            print(f'error2: {e}')
            players[mode][player] = [1, 3.6666 + mu - (2 * sigma), 25.00, 8.3333, mu, sigma]
        i += 1
        print(f'new player: {player} ::: {players[mode].get(player)}')
    #sort the dictionary on rating
    players[mode] = {k: v for k, v in sorted(players[mode].items(), key=lambda item: item[1][1], reverse=True)}
    #save the dictionary to a csv file
    playersToCSV(players, mode)
    return players

def getGameID(mode):
    #open the file
    with open(f'ranking{mode}.csv','r') as file: 
        data = file.readlines()
        print(f'len data: {len(data)}')
        #return current game number as 0 if data is empty
        if len(data)==1:
            return 0
        #return latest value for game number
        return data[-1].split(',')[1]

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
async def members1(ctx):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        members = {}
        #create dictionary of member ids and their discord name (Donutseeds#7704 for example)
        for member in ctx.guild.members:
            members[member.id] = str(member)
        print(members)
    return members

#print all 1V1 players in the server
@bot.command()
async def players1V1(ctx):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        #print out the players dictionary
        print(players['1V1'])
    return

#print all FFA players in the server
@bot.command()
async def playersFFA(ctx):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        #print out the players dictionary
        print(players['FFA'])
    return

#return dictionary of member ids and member names
def getMembers(ctx):
    members={}
    #create dictionary of member ids and their discord display name (Donutseeds for example)
    for member in ctx.guild.members:
        members[member.id] = member
    return members

#submit new lobby results to spreadsheet
@bot.command()
async def submit(ctx, *message):
    #check that we're in the right channel
    if ctx.channel.id == 937998936269000704 or ctx.channel.id == 940007288012415106:
        #get name of user submitting
        author=ctx.author.name
        #get game mode
        message = list(message)
        if len(message) == 4:
            mode = '1V1'
        else:
            mode = 'FFA'
        print(f'list message: {message}\nmode: {mode}')
        #get current gameID
        gameID = int(getGameID(mode))+1
        #get the dictionary of member ids : display names
        members = getMembers(ctx)
        #check to see if formatting is valid
        today = date.today()
        try:
            #open csv file to append new data
            with open(f'ranking{mode}.csv', 'a', newline='') as ranking:
                writer_object = writer(ranking)
                #keep track of players in the submitted lobby
                currentPlayers={}
                #loop through each player in the lobby
                for i in range(0,len(message),2):
                    #get the discord id from the submitted ping
                    #when certain members use the search command, their message differs in length
                    if len(message[i][3:-1]) == 18:
                        username = f'{message[i][3:-1]}#'
                    else:
                        username = f'{message[i][2:-1]}#'
                    line = []
                    #add the name, gameID, placement, and date to the array
                    line.append(username)
                    line.append(gameID)
                    line.append(message[i+1])
                    line.append(today)
                    #add the current player's placement to the dictionary
                    currentPlayers[username] = message[i+1]
                    print(f'line to add: {line}')
                    #append line to csv file
                    writer_object.writerow(line)
                ranking.close()
            #update players
            ratePlayers(currentPlayers, mode)
            message = (f'```\n#  Player              Rating\n')
            i=1
            #return info on the rating change for players in the lobby
            for player in players[mode]:
                if player in currentPlayers:
                    #return the matching rank
                    message += (f'{i}   ')
                    #remove spaces from string the longer thier rank index is
                    for j in range(len(str(i))):
                        message = message[:-1]
                    #add username to the string
                    message += members.get(int(player[:-1])).display_name
                    #add spaces for proper allignment
                    for k in range(20 - len(members.get(int(player[:-1])).display_name)):
                        message += ' '
                    #get the new rating and calculate the change
                    rating = 100*players[mode].get(player)[1]
                    change = rating - 100*(3.6666 + players[mode].get(player)[2] - 2 * players[mode].get(player)[3])
                    #add change to the string
                    message += (f'{int(rating)}(')
                    if change > 0:
                        message += '+'
                    message += (f'{int(change)})\n')
                i+=1
        except Exception as e:
            #catch error
            print(f'error: {e}')
            #make pandas dataframe
            df = pd.read_csv(f'ranking{mode}.csv')
            #keep rows where gameID doesnt match input
            df = df[df['game_id'] != int(gameID)]
            #save csv without indexes
            df.to_csv(f'ranking{mode}.csv', index=False)
            #update players
            setPlayers(mode)
            await ctx.channel.send(f'Error submitting {mode} gameID {gameID}!')
            return   
        else:
            #get role to add/remove
            role0 = discord.utils.get(ctx.author.guild.roles, name = "Masters") #3000
            role1 = discord.utils.get(ctx.author.guild.roles, name = "Diamond") #2750
            role2 = discord.utils.get(ctx.author.guild.roles, name = "Platinum") #2500
            role3 = discord.utils.get(ctx.author.guild.roles, name = "Gold") #2250
            role4 = discord.utils.get(ctx.author.guild.roles, name = "Silver") #2000
            role5 = discord.utils.get(ctx.author.guild.roles, name = "Bronze") #1750
            unranked = discord.utils.get(ctx.author.guild.roles, name = "Unranked")
            roles = [role0, role1, role2, role3, role4, role5]
            #add high elo role if above 30, add mid elo role if above 27.5
            for player in currentPlayers:
                rating = max(
                    0 if players['1V1'].get(player) is None else players['1V1'].get(player)[1],
                    0 if players['FFA'].get(player) is None else players['FFA'].get(player)[1])
                if (0 if players['1V1'].get(player) is None else players['1V1'].get(player)[0]) < 10 and (0 if players['FFA'].get(player) is None else players['FFA'].get(player)[0]) < 10:
                    if unranked not in members.get(int(player[:-1])).roles:
                        print(f'added Unranked to {str(members.get(int(player[:-1])))}')
                        await members.get(int(player[:-1])).add_roles(unranked)
                    for role in roles:
                        if role in members.get(int(player[:-1])).roles:
                            print(f'removed {role.name} from {str(members.get(int(player[:-1])))}')
                            await members.get(int(player[:-1])).remove_roles(role)
                else:
                    if unranked in members.get(int(player[:-1])).roles:
                        print(f'removed Unranked from {str(members.get(int(player[:-1])))}')
                        await members.get(int(player[:-1])).remove_roles(unranked)
                    roleHigh = roles[min(5,max(0,math.ceil((30-rating)/2.5)))]
                    for role in roles:
                        if role == roleHigh:
                            if role not in members.get(int(player[:-1])).roles:
                                print(f'added {role.name} to {str(members.get(int(player[:-1])))}')
                                await members.get(int(player[:-1])).add_roles(role)
                        else:
                            if role in members.get(int(player[:-1])).roles:
                                print(f'removed {role.name} from {str(members.get(int(player[:-1])))}')
                                await members.get(int(player[:-1])).remove_roles(role)
            #confirmation message
            await ctx.channel.send(f'Thank you {author} for submitting {mode} gameID {gameID}!')
            await ctx.channel.send(f'{message}\n```')
            await editLeaderboard(ctx, mode)
    return

@bot.command()
async def setRoles(ctx, mode):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        mode = mode.upper()
        #get role to add/remove
        role0 = discord.utils.get(ctx.author.guild.roles, name = "Masters") #3000
        role1 = discord.utils.get(ctx.author.guild.roles, name = "Diamond") #2750
        role2 = discord.utils.get(ctx.author.guild.roles, name = "Platinum") #2500
        role3 = discord.utils.get(ctx.author.guild.roles, name = "Gold") #2250
        role4 = discord.utils.get(ctx.author.guild.roles, name = "Silver") #2000
        role5 = discord.utils.get(ctx.author.guild.roles, name = "Bronze") #1750
        unranked = discord.utils.get(ctx.author.guild.roles, name = "Unranked")
        roles = [role0, role1, role2, role3, role4, role5]
        #add highest elo role to each member
        for member in ctx.guild.members:
            rating = max(
                0 if players['1V1'].get(f'{member.id}#') is None else players['1V1'].get(f'{member.id}#')[1],
                0 if players['FFA'].get(f'{member.id}#') is None else players['FFA'].get(f'{member.id}#')[1])
            if (0 if players['1V1'].get(f'{member.id}#') is None else players['1V1'].get(f'{member.id}#')[0]) < 10 and (0 if players['FFA'].get(f'{member.id}#') is None else players['FFA'].get(f'{member.id}#')[0]) < 10:
                if unranked not in member.roles:
                    print(f'added Unranked to {str(member)}')
                    await member.add_roles(unranked)
                for role in roles:
                    if role in member.roles:
                        print(f'removed {role.name} from {str(member)}')
                        await member.remove_roles(role)
            else:
                if unranked in member.roles:
                    print(f'removed Unranked from {str(member)}')
                    await member.remove_roles(unranked)
                roleHigh = roles[min(5,max(0,math.ceil((30-rating)/2.5)))]
                print(f'{str(member)} highest role is {roleHigh}')
                for role in roles:
                    if role == roleHigh:
                        if role not in member.roles:
                            print(f'added {role.name} to {str(member)}')
                            await member.add_roles(role)
                    else:
                        if role in member.roles:
                            print(f'removed {role.name} from {str(member)}')
                            await member.remove_roles(role)
        print('roles set')
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
async def deleteGame(ctx, mode, gameID):
    #check to see if an admin is giving the command
    role = discord.utils.get(ctx.author.guild.roles, name = "Admin")
    if role in ctx.author.roles:
        #make pandas dataframe
        df = pd.read_csv(f'ranking{mode}.csv')
        #keep rows where gameID doesnt match input
        df = df[df['game_id'] != int(gameID)]
        #save csv without indexes
        df.to_csv(f'ranking{mode}.csv', index=False)
        #update players
        setPlayers(mode)
        await ctx.channel.send(f'{ctx.author} removed {mode} gameID {gameID}!')
        await editLeaderboard(ctx, mode)
    return

#check what rank a specified user is
@bot.command()
async def search(ctx, message):
    if ctx.channel.id == 938116070374510603 or ctx.channel.id == 940007288012415106:
        #get list of members
        members = getMembers(ctx)
        print(f'message: {message}')
        print(f'len message: {len(message[3:-1])}')
        #for some reason when certain members use the search command, their message differs in length
        if len(message[3:-1]) == 18:
            username = f'{message[3:-1]}#'
        else:
            username = f'{message[2:-1]}#'
        mode = '1V1'
        for key, dict in players.items():
            found = False
            i=1
            #check to see if any player in the system matches the user's name
            for player in dict:
                #check if searched player is in the system
                if player == username:
                    #return the matching rank and elo
                    message = (f'```\n#  Player              Rating\n{i}   ')
                    #account for length of index
                    for j in range(len(str(i))):
                        message = message[:-1]
                    #add player name to string
                    message += members.get(int(player[:-1])).display_name
                    #account for length of name
                    for j in range(20 - len(members.get(int(player[:-1])).display_name)):
                        message += ' '
                    #add player rating to string
                    message += (f'{int(100*dict.get(player)[1])}')
                    if dict.get(player)[0] < 10:
                        message += (f'    {int(10-dict.get(player)[0])} placement games remaining')
                    await ctx.channel.send(f'{mode}\n{message}```\n')
                    found = True
                    break
                i+=1
            #inform user if no match was found
            if not found:
                await ctx.channel.send(f'Could not find {members.get(int(username[:-1])).display_name} in the {mode} rankings')
            # with open(f'ranking{mode}.csv','r') as file: 
            #     data = file.readlines()
            #     #return current game number as 0 if data is empty
            #     if len(data)==1:
            #         return 0
            #     #return latest value for game number
            #     daaate = data[-1].split(',')[3]
            # dt_obj = datetime.strptime(daaate.strip(), '%Y-%m-%d')
            # print(f'time since game: {(datetime.now() - dt_obj).days}')
            mode = 'FFA'
    return

#check what rank a specified user is and give extended stats
@bot.command()
async def searchstats(ctx, message):
    if ctx.channel.id == 938116070374510603 or ctx.channel.id == 940007288012415106:
        #get name of specified user
        members = getMembers(ctx)
        print(f'message: {message}')
        print(f'len message: {len(message[3:-1])}')
        #when certain members use the search command, their message differs in length
        if len(message[3:-1]) == 18:
            username = f'{message[3:-1]}#'
        else:
            username = f'{message[2:-1]}#'
        mode = '1V1'
        for key, dict in players.items():
            found = False
            i=1
            #check to see if any player in the system matches the user's name
            for player in dict:
                if player == username:
                    #return the matching rank and elo
                    message = (f'```\n#  Player              Rating  μ     σ    games\n{i}   ')
                    #account for length of index
                    for j in range(len(str(i))):
                        message = message[:-1]
                    #add player name to string
                    message += members.get(int(player[:-1])).display_name
                    #account for length of player name
                    for j in range(20 - len(members.get(int(player[:-1])).display_name)):
                        message += ' '
                    #add player stats to string
                    games, rating, pre_mu, pre_sigma, mu, sigma = dict.get(player)
                    message += (f'{int(rating*100)}    ')
                    if len(str(int(rating*100))) == 3:
                        message += ' '
                    message += (f'{int(mu*100)}  {int(sigma*100)}  ')
                    if len(str(int(sigma*100))) == 2:
                        message += ' '
                    message += (f'{int(games)}')
                    if games < 10:
                        message += (f'    {int(10-games)} placement games remaining')
                    await ctx.channel.send(f'{mode}\n{message}\n```')
                    found = True
                    break
                i+=1
            #inform user if no match was found
            if not found:
                await ctx.channel.send(f'Could not find {members.get(int(username[:-1])).display_name} in the {mode} rankings')
            mode = 'FFA'
    return

@bot.command()
async def editLeaderboard(ctx, mode):
    #get list members
    members = getMembers(ctx)
    #get leaderboard channel
    channel = ctx.guild.get_channel(941904885752946730)
    #get the relevant message ids
    _ffa_id = 941906003442667590
    _1v1_id = 941906028260364288
    _ffa_stats_id = 941906054067937350
    _1v1_stats_id = 941906078625583114
    #get corresponding messages
    _ffa = await channel.fetch_message(_ffa_id)
    _ffa_stats = await channel.fetch_message(_ffa_stats_id)
    _1v1 = await channel.fetch_message(_1v1_id)
    _1v1_stats = await channel.fetch_message(_1v1_stats_id)
    #check if there is no data in the spreadsheet
    if getGameID(mode) == 0:
        message = (f'No data in the {mode} leaderboard')
    else:
        message = f'{mode}\n```\n#  Player              Rating\n'
        i=1
        #list off the first 10 players and their Elos
        for player in players[mode]:
            if players[mode].get(player)[0] < 10:
                continue
            message += (f'{i}   ')
            #account for length of index
            for j in range(len(str(i))):
                message = message[:-1]
            #add player name to string
            message += members.get(int(player[:-1])).display_name
            #account for length of player name
            for j in range(20 - len(members.get(int(player[:-1])).display_name)):
                message += ' '
            #add player rating to string
            message += (f'{int(100*players[mode].get(player)[1])}\n')
            #stop after printing the first 10 entries
            if i==10:
                break
            i+=1
        #edit content of appropriate message
        if mode == 'FFA':
            await _ffa.edit(content=f'{message}```')
        else:
            await _1v1.edit(content=f'{message}```')
        message = f'{mode}\n```\n#  Player              Rating  μ     σ    games\n'
        i=1
        #list off the first 10 players and their Elos plus stats
        for player in players[mode]:
            if players[mode].get(player)[0] < 10:
                continue
            message += (f'{i}   ')
            #account for length of index
            for j in range(len(str(i))):
                message = message[:-1]
            #add player name to string
            message += members.get(int(player[:-1])).display_name
            #account for length of player name
            for j in range(20 - len(members.get(int(player[:-1])).display_name)):
                message += ' '
            #add player stats to string
            games, rating, pre_mu, pre_sigma, mu, sigma = players[mode].get(player)
            message += (f'{int(rating*100)}    ')
            if len(str(int(rating*100))) == 3:
                message += ' '
            message += (f'{int(mu*100)}  {int(sigma*100)}  ')
            if len(str(int(sigma*100))) == 2:
                message += ' '
            message += (f'{int(games)}\n')
            #stop after first 10 entries
            if i==10:
                break
            i+=1
        #edit content of appropriate message
        if mode == 'FFA':
            await _ffa_stats.edit(content=f'{message}```')
        else:
            await _1v1_stats.edit(content=f'{message}```')
    return

setPlayers('1V1')
setPlayers('FFA')
bot.run(TOKEN)
