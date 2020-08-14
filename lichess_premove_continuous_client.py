#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 11:57:08 2020

@author: jx283

A more permanent client which does not need restarting.

This continuous client also supports premoving.
"""
import os
import pyautogui
import random
import chess
import requests
import re
from bs4 import BeautifulSoup
import configparser

from engine_1_5 import AtomicSamurai

import time

config = configparser.ConfigParser()
config.read('config.ini')

STEP = float((config['DEFAULT']['step']))
START_X = int(config['DEFAULT']['start_x']) + STEP/2
START_Y = int(config['DEFAULT']['start_y']) + STEP/2



class GameFinder:
    ''' During idle phases, we are scanning a particuar username to see if any active
        games are present, hence avoiding starting/restarting the script. '''
    def __init__(self, username, shadow_mode=False, log=True):
        self.username = username
        self.client = LichessClient(username, shadow_mode=shadow_mode, log=log)
    
    def run(self):
        profile_url = 'https://lichess.org/@/'+self.username+'/playing'
        # now see if username was valid or not
        r = requests.get(profile_url)
        valid = re.findall(r"<h1>404<\/h1><div><strong>Page not found!<\/strong>", r.text)
        if len(valid) > 0:
            raise Exception('Username not found: ' + self.username + '. Please make sure the spelling is correct (case sensitive)')
        print('Status connected.')
        while True:
            r = requests.get(profile_url)
            playing = re.findall('Playing right now', r.text)
            if len(playing) > 0:
                # then the user is in a game
                print ('Found user game!')
                sound_file = "new_game_found.mp3"
                os.system("mpg123 -q " + sound_file)
                soup = BeautifulSoup(r.text, 'html.parser')
                game_url = 'https://lichess.org' + soup.findAll("a", {"class": "game-row__overlay"})[0]['href']
                
                self.client.set_game(game_url)
                while True:
                    status = self.client.make_move()
                    if status == False:
                        break
            else:
                time.sleep(1)

class LichessClient:
    ''' Main class which interacts with Lichess. Plays and recieves moves. Called
        every instance of a game. '''
    
    def __init__(self, username, log=True, shadow_mode=False, url=None, side=None, time=None):
        self.username = username
        if url is not None:
            self.url = url
            # getting player side and starting time
            page = requests.get(self.url)
            if time == None:
                starting_time = float(re.findall('\"initial\":(\d{1,4})', page.text)[0])
            else:
                starting_time = time
            if side is None:
                soup = BeautifulSoup(page.text, 'html.parser')
                white_username = soup.findAll("div", {"class": "player color-icon is white text"})[0].text.split()[0]
                if white_username == self.username:
                    self.side = chess.WHITE
                else:
                    self.side = chess.BLACK
            else:
                self.side = side
            self.starting_time = starting_time
        
        self.premoved = False
        self.board = chess.Board()
        self.last_fen = chess.STARTING_FEN
        self.engine = AtomicSamurai(log=log, shadow=shadow_mode)
        self.shadow = shadow_mode
        
    def set_game(self, url, side=None, time=None):
        ''' Once client has found game, sets up game parameters. '''
        self.url = url
        # getting player side and starting time
        page = requests.get(self.url)
        if time == None:
            starting_time = float(re.findall('\"initial\":(\d{1,4})', page.text)[0])
        else:
            starting_time = time
        if side is None:
            soup = BeautifulSoup(page.text, 'html.parser')
            white_username = soup.findAll("div", {"class": "player color-icon is white text"})[0].text.split()[0]
            if white_username == self.username:
                self.side = chess.WHITE
            else:
                self.side = chess.BLACK
        else:
            self.side = side
        
        self.starting_time = starting_time
        self.engine.side = self.side
        self.engine.blunder_prone = False # when true, the engine is prone to make a human like error
        self.engine.resigned = False # indicates whether engine has resigned
        self.engine.time_scramble_mode = False # when this is on, engine will make moves as fast as possible
        self.engine.resign_threshold = random.randint(1,10) + 30 # number of moves the engine must play before resigning
        self.engine.bullet_threshold = random.randint(1,5) + 10 # threshold before engine goes into bullet mode
        self.engine.premove_mode = False
        self.engine.big_material_take = False
        self.engine.mate_in_one = False
        self.engine.shadow = self.shadow
        self.engine.move_times = []
        self.engine.prev_own_move = None
        
    def find_clicks(self, move_uci):
        ''' Given a move in uci form, find the click from and click to positions. '''
        start_x , start_y = START_X, START_Y # this represents top left square of chess board for calibration
        step = STEP
        move_obj = chess.Move.from_uci(move_uci)
        from_square = move_obj.from_square
        to_square = move_obj.to_square
        if self.side == chess.WHITE:
            # a1 square is bottom left
            rank_fr = chess.square_rank(from_square)
            file_fr = chess.square_file(from_square)
            click_from_x = start_x + file_fr*step
            click_from_y = start_y + (7-rank_fr)*step
            
            rank_to = chess.square_rank(to_square)
            file_to = chess.square_file(to_square)
            click_to_x = start_x + file_to*step
            click_to_y = start_y + (7-rank_to)*step
        else:
            # a1 square is top right
            rank_fr = chess.square_rank(from_square)
            file_fr = chess.square_file(from_square)
            click_from_x = start_x + (7-file_fr)*step
            click_from_y = start_y + rank_fr*step
            
            rank_to = chess.square_rank(to_square)
            file_to = chess.square_file(to_square)
            click_to_x = start_x + (7-file_to)*step
            click_to_y = start_y + rank_to*step
        return click_from_x, click_from_y, click_to_x, click_to_y
    
    def interact(self, click_from_x, click_from_y, click_to_x, click_to_y, own_time, premove=False):
        ''' Function which does the clicking on the screen, and makes the moves. '''
        if premove and self.shadow == False:
            #print('yes i made premove')
            # pyautogui.moveTo(click_from_x, click_from_y)
            # pyautogui.dragTo(click_to_x, click_to_y, 0.2, button='left')
            pyautogui.click(click_from_x, click_from_y, button='left')
            pyautogui.click(click_to_x, click_to_y, button='left')
        else:
            if self.starting_time < 16 or own_time < 15 and self.shadow == False:
                if self.engine.big_material_take == True or self.engine.mate_in_one == True:
                    # opposition just hung a big piece or next move is mate in on
                    # delay for a bit to simulate the surprise/intrigue by a human player
                    time.sleep(random.randint(10,15)*self.starting_time/1500)
                else:
                    if random.random() <0.01:
                        time.sleep(random.randint(1,2)/1.5)
                    else:
                        time.sleep(random.randint(1,10)/1000)
                pyautogui.click(click_from_x, click_from_y, button='left')
                pyautogui.click(click_to_x, click_to_y, button='left')
                # pass
                
            elif self.starting_time > 61 and own_time > 10 and self.starting_time-own_time >7:
                # first assert it is actually my move
                page = requests.get(self.url)
                fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
                if self.side == chess.WHITE:
                    lookout = 'w'
                else:
                    lookout = 'b'
                if len(fen_search) == 0:
                    fen = chess.STARTING_FEN
                else:
                    fen = fen_search[-1]
                if fen == self.last_fen:
                    if self.shadow == True:
                        pyautogui.click(click_from_x, click_from_y, button='right')
                        pyautogui.click(click_to_x, click_to_y, button='right')
                    else:
                        if self.engine.big_material_take == True or self.engine.mate_in_one == True:
                            # opposition just hung a big piece or next move is mate in one
                            # print('hung big piece!')
                            # print(self.board)
                            time.sleep(random.randint(18,28)*self.starting_time/1000)
                        pyautogui.click(click_from_x, click_from_y, button='left')
                        pyautogui.click(click_to_x, click_to_y, button='left')
                else:
                    print('Detected human interference!, passing move for now...')
            elif own_time > 10 and self.starting_time-own_time > 3:
                if self.shadow == True:
                    pyautogui.click(click_from_x, click_from_y, button='right')
                    pyautogui.click(click_to_x, click_to_y, button='right')
                else:
                    if self.engine.big_material_take == True or self.engine.mate_in_one == True:
                        # opposition just hung a big piece or next move is mate in one
                        # print('hung big piece!')
                        # print(self.board)
                        time.sleep(random.randint(18,28)*self.starting_time/1000)
                    elif self.engine.obvious_move == True:
                        pass
                    else:
                        x = random.random()
                        if x < 0.6:
                            pass
                        elif x <0.95:
                            time.sleep(x/5)
                        else:
                            if own_time > 15 and own_time > 45:
                                time.sleep(random.randint(0,1) + random.random())
                    pyautogui.click(click_from_x, click_from_y, button='left')
                    pyautogui.click(click_to_x, click_to_y, button='left')
                

    def make_move(self):
        fen, prev_move, prev_fen, white_time, black_time, game_end, premove = self.get_next_move(self.last_fen, premove=True)
        if self.side == chess.WHITE:
            own_time = white_time
        else:
            own_time = black_time
        
        if game_end == True:
            # game has ended
            print('Detected game has ended.')
            return False
        
        self.last_fen = fen
        self.board = chess.Board(fen)
        if premove is not None:
            self.premoved = True
            # we have made a premove, and thus must play it
            # pre move should be in uci format
            click_from_x, click_from_y, click_to_x, click_to_y = self.find_clicks(premove)
            self.interact(click_from_x, click_from_y, click_to_x, click_to_y, own_time, premove=True)
            return True # move successful
        
        
        
        status = self.engine_moves(white_time, black_time, prev_fen, prev_move)
        if status[0] != 'GAME_OVER':
            # execute move
            move_uci = status[1]
            click_from_x, click_from_y, click_to_x, click_to_y = self.find_clicks(move_uci)
            #print('execute normal move ' + move_uci)
            self.interact(click_from_x, click_from_y, click_to_x, click_to_y, own_time)
            return True # move successful
        else:
            return False

    def engine_moves(self, white_time, black_time, prev_fen, prev_move):
        if self.board.is_game_over():
            return ['GAME_OVER', self.board.result()]
        
        self.engine.update_board(self.board)
        time_dic = {'starting_time':self.starting_time, 'white_time': white_time, 'black_time': black_time}
        move_uci_played = self.engine.make_move(time_dic=time_dic, prev_fen=prev_fen, prev_move=prev_move)
        # check if player has resigned/timed out
        if self.engine.resigned:
            if self.side == chess.WHITE:
                result = '0-1'
            else:
                result = '1-0'
            return ['GAME_OVER', result]
        
        self.board = self.engine.get_board().copy()
        return ['STILL_PLAYING', move_uci_played]

    def get_next_move(self, last_fen, premove=False):
        ''' Given a playing side, wait till the last fen updated is new and that
            it is the playing side's turn. '''
        if self.side == chess.WHITE:
            lookout = 'w'
        else:
            lookout = 'b'
                
        while True:
            successful_request = False
            game_end = False
            while successful_request == False:
                if self.starting_time > 60:
                      time.sleep(self.starting_time/1000)
                
                try:
                    page = requests.get(self.url, timeout=0.25)
                except requests.exceptions.Timeout:
                    # too many requests
                    print('Request fetching timed out, trying again...')
                    sound_file = "alert.mp3"
                    os.system("mpg123 -q " + sound_file)
                    continue  
                
                fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text) 
                prev_move = re.findall('uci\":\"(.{3,5})\"', page.text)
                if len(prev_move) == 0:
                    prev_move = False
                else:
                    prev_move = prev_move[-1]
                
                result_search = re.findall('Result', page.text)
                abort_search = re.findall('aborted after', page.text)
                if len(result_search) > 0 or len(abort_search) > 0:
                    # game has ended
                    game_end = True
                    successful_request = True
                    break
                try:
                    white_time = float(re.findall('white\":(\d{1,4}\.\d{1,2})', page.text)[0])
                    black_time = float(re.findall('black\":(\d{1,4}\.\d{1,2})', page.text)[0])
                    successful_request = True
                    break
                except IndexError:
                    # too many requests
                    print('Request fetching timed out, trying again...')
                    sound_file = "alert.mp3"
                    os.system("mpg123 -q " + sound_file)
                    continue         
                    
            if len(fen_search) == 0:
                fen = chess.STARTING_FEN
                # for obvious move purposes, we want the last move also
                prev_fen = False
            else:
                fen = fen_search[-1]
                if len(fen_search) > 1:
                    prev_fen = fen_search[-2]
                else:
                    prev_fen = False
            
            if game_end == True:
                return '','','','','', game_end, None
            
            if last_fen != fen and fen.split()[-5] == lookout:
                # we have found new updated fen
                self.premoved = False # reset premove
                #print('make normal move')
                return fen, prev_move, prev_fen, white_time, black_time, game_end, None
            elif last_fen != fen and premove == True and self.premoved == False:
                # i.e. opponent hasn't moved but we have moved
                # first thing we do is check for premove. We assume at this stage that
                # we have just made a move, so it is the opposition move at this point
                # print('get premove')
                move = self.engine.get_premove(fen)
                if move is not None:
                    return fen, prev_move, prev_fen, white_time, black_time, game_end, move

# URL = 'https://lichess.org/GlYCARuKJKOp'