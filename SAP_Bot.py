# SAP_Bot.py
import os
import random
from webbrowser import get
import discord
from csv import writer
import pandas as pd
from dotenv import load_dotenv
from discord.ext import commands
from IPython.display import display
from trueskill import Rating, rate

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

    #create dictionary
    players = {}

    #fill dictionary with player ids and their post mu
    for i in range(len(df_truerank)):
        players[df_truerank['player_id'].iloc[i]] = [df_truerank['post_mu'].iloc[i],df_truerank['post_sigma'].iloc[i]]

    #sort and display the dictionary
    players = {k: v for k, v in sorted(players.items(), key=lambda item: item[1][0], reverse=True)}   
    print(players)

    # #make an array for a weighted raffle
    # raffle = []

    # #fill array with weighted tickets for players
    # for player in players:
    #     for i in range(int(players.get(player))*int(players.get(player))):
    #         raffle.append(player)

    # #display raffle winner
    # print("raffle winner: " + random.choice(raffle))

    return players

#give proper intents for bot to detect members
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

#print all members in the server
@bot.command()
async def members(ctx):
    if ctx.author.id == 292116181312339969:
        for member in ctx.guild.members:
            print(member)
            print(member.id)
    return

# @bot.event()
# async def on_reaction_add(reaction, user):
#     if reaction.message.channel.id == 937998936269000704:
#         embed = reaction.embeds[0]
#         emoji = reaction.emoji
#         await reaction.message.channel.send_message('{} has added {} to the message: {}'.format(user.name, reaction.emoji, reaction.message.content))

#     return

#submit new lobby results to spreadsheet
@bot.command()
async def submit(ctx, *message):
    #check that we're in the right channel
    if ctx.channel.id == 937998936269000704:
        #get name of user submitting
        username=ctx.author.name
        #get current gameID
        gameID = int(getGameID())+1
        #check to see if formatting is valid
        try:
            await ctx.channel.send(f'Thank you {username} for submitting gameID {gameID}!')
            #convert tuple to list
            message = list(message)
            print(message)
            #open csv file to append new data
            with open('ranking.csv', 'a', newline='') as f_object:
                writer_object = writer(f_object)
                #keep track of players in the lobby
                currentPlayers=[]
                for line in message:
                    line = line.split(':')
                    currentPlayers.append(line[0])
                    #put gameID into second position
                    line.insert(1,gameID)
                    print(line)
                    #append line to csv file
                    writer_object.writerow(line)
                f_object.close()
        except:
            #catch error
            await ctx.channel.send(f'Error submitting gameID {gameID}!')
        #add/remove role to members above/below 30 elo threshold
        players = getPlayers()
        for player in currentPlayers:
            #match the player name with their member object
            for member in ctx.guild.members:
                if member.name.lower().startswith(player.lower()):
                    #get role to add/remove
                    role = discord.utils.get(ctx.author.guild.roles, name = "High Elo Gamer")
                    if players.get(player)[0]<3000:
                        await member.remove_roles(role)
                    else:
                        await member.add_roles(role)
    return

@bot.command()
async def replace(ctx, nameOld, nameNew):
    if ctx.author.id == 292116181312339969:
        # reading the CSV file
        with open("ranking.csv", "r") as text:

            #join() method combines all contents of 
            # csvfile.csv and formed as a string
            text = ''.join([i for i in text]) 
            
            # search and replace the contents
            text = text.replace(nameOld, nameNew)
            
            # output.csv is the output file opened in write mode
            x = open("ranking.csv","w")
            
            # all the replaced text is written in the output.csv file
            x.writelines(text)
            x.close()
    return

# #check what rank user is
# @bot.command()
# async def myrank(ctx):
#     #get name of user submitting
#     username=ctx.author.name.replace(" ","")
#     players = getPlayers()
#     i=1
#     #check to see if any player in the system matches the user's name
#     for player in players:
#         if player == username:
#             #return the matching rank and elo
#             await ctx.channel.send(f'{i}:{username}-{players.get(username)}')
#             return
#         i+=1
#     #inform user if no match was found
#     await ctx.channel.send(f'Could not find {username} in the rankings')
#     return

# @bot.command()
# async def deleteGameID(ctx, message):
#     gameID = message
#     with open('ranking.csv', 'a', newline='') as f_object:
#         writer_object = writer(f_object)
#         for line in message:
#             line = line.split(':')
#             #put gameID into second position
#             line.insert(1,gameID)
#             print(line)
#             #append line to csv file
#             writer_object.writerow(line)
#         f_object.close()
#     return

#check what rank a specified user is
@bot.command()
async def search(ctx, message):
    #get name of specified user
    username=message
    players = getPlayers()
    i=1
    #check to see if any player in the system matches the user's name
    for player in players:
        if player == username:
            #return the matching rank and elo
            playerRank = (f'```\n#  Player       Rating\n{i}   ')
            for j in range(len(str(i))):
                playerRank = playerRank[:-1]
            playerRank += player
            for j in range(13 - len(player)):
                playerRank += ' '
            mu, sigma = players.get(player)
            playerRank += (f'{int(100*players.get(player)[0])}\n```')
            await ctx.channel.send(playerRank)
            return
        i+=1
    #inform user if no match was found
    await ctx.channel.send(f'Could not find {username} in the rankings')
    return

#check what rank a specified user is and give extended stats
@bot.command()
async def searchstats(ctx, message):
    #get name of specified user
    username=message
    players = getPlayers()
    i=1
    #check to see if any player in the system matches the user's name
    for player in players:
        if player == username:
            #return the matching rank and elo
            playerRank = (f'```\n#  Player       μ      σ\n{i}   ')
            for j in range(len(str(i))):
                playerRank = playerRank[:-1]
            playerRank += player
            for j in range(13 - len(player)):
                playerRank += ' '
            mu, sigma = players.get(player)
            playerRank += (f'{int(mu*100)}  {int(round(sigma, 1)*10)}\n```')
            await ctx.channel.send(playerRank)
            return
        i+=1
    #inform user if no match was found
    await ctx.channel.send(f'Could not find {username} in the rankings')
    return

#check top 5 players on the leaderboard
@bot.command()
async def leaderboard(ctx):
    if getGameID() == 0:
        await ctx.channel.send('No data in the leaderboard')
    players = getPlayers()
    message = '```\n#  Player       Rating\n'
    i=1
    #list off the first 5 players and their Elos
    for player in players:
        message += (f'{i}   ')
        for j in range(len(str(i))):
                message = message[:-1]
        message += player
        for j in range(13 - len(player)):
            message += ' '
        message += (f'{int(100*players.get(player)[0])}\n')
        if i==10:
            break
        i+=1
    await ctx.channel.send(message + '\n```')
    return

#check top 5 players on the leaderboard and give extended stats
@bot.command()
async def leaderboardstats(ctx):
    if getGameID() == 0:
        await ctx.channel.send('No data in the leaderboard')
    players = getPlayers()
    message = '```\n#  Player       μ      σ\n'
    i=1
    #list off the first 5 players and their Elos
    for player in players:
        message += (f'{i}   ')
        for j in range(len(str(i))):
                message = message[:-1]
        message += player
        for j in range(13 - len(player)):
            message += ' '
        mu, sigma = players.get(player)
        message += (f'{int(mu*100)}  {int(round(sigma, 1)*10)}\n')
        if i==10:
            # await ctx.channel.send(message + '\n```')
            # return
            break
        i+=1
    await ctx.channel.send(message + '\n```')
    return

bot.run(TOKEN)
