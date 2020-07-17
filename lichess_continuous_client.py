#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  3 12:42:05 2020

@author: jx283

A more permanent client which does not need restarting.
"""
import os
import pyautogui
import random
import chess
import requests
import re
from bs4 import BeautifulSoup

from engine_1_3 import AtomicSamurai

import time

#USERNAME = 'gmdolmatov'
USERNAME = 'imcsabalogh'
#USERNAME = 'JXu2019'
#USERNAME = 'Moment_of_Inertia'

class GameFinder:
    ''' During idle phases, we are scanning a prticuar username to see if any active
        games are present, hence avoiding starting/restarting the script. '''
    def __init__(self, username):
        self.username = username
        self.client = LichessClient()
    
    def run(self):
        profile_url = 'https://lichess.org/@/'+self.username+'/playing'
        print('Status connected.')
        while True:
            r = requests.get(profile_url)
            playing = re.findall('Playing right now', r.text)
            if len(playing) > 0:
                # then the user is in a game
                print ('Found user game!')
                sound_file = "new_game_found.mp3"
                os.system("mpg123 " + sound_file)
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
    
    def __init__(self, url=None, side=None, time=None):
        if url is not None:
            self.url = url
            # getting player side and starting time
            page = requests.get(self.url)
            if time == None:
                starting_time = float(re.findall('\"initial\":(\d{1,3})', page.text)[0])
            else:
                starting_time = time
            if side is None:
                soup = BeautifulSoup(page.text, 'html.parser')
                white_username = soup.findAll("div", {"class": "player color-icon is white text"})[0].text.split()[0]
                if white_username == USERNAME:
                    self.side = chess.WHITE
                else:
                    self.side = chess.BLACK
            else:
                self.side = side
            self.starting_time = starting_time
            
        self.board = chess.Board()
        self.last_fen = chess.STARTING_FEN
        self.engine = AtomicSamurai()
        
    def set_game(self, url, side=None, time=None):
        ''' Once client has found game, sets up game parameters. '''
        self.url = url
        # getting player side and starting time
        page = requests.get(self.url)
        if time == None:
            starting_time = float(re.findall('\"initial\":(\d{1,3})', page.text)[0])
        else:
            starting_time = time
        if side is None:
            soup = BeautifulSoup(page.text, 'html.parser')
            white_username = soup.findAll("div", {"class": "player color-icon is white text"})[0].text.split()[0]
            if white_username == USERNAME:
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
        self.engine.bullet_threshold = random.randint(1,5) + 9 # threshold before engine goes into bullet mode
        
        
    def find_clicks(self, move_uci):
        ''' Given a move in uci form, find the click from and click to positions. '''
        start_x , start_y = 410, 180 # this represents top left square of chess board for calibration
        step = 57
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
    
    def interact(self, click_from_x, click_from_y, click_to_x, click_to_y, own_time):
        ''' Function which does the clicking on the screen, and makes the moves.
            For the first and last 10 seconds of own_time, the user plays to avoid suspicion. '''
        if self.starting_time > 61 and own_time > 10 and self.starting_time-own_time >7:
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
            if fen.split()[-5] == lookout:        
                pyautogui.click(click_from_x, click_from_y)
                #time.sleep(0.1)
                pyautogui.click(click_to_x, click_to_y)
            else:
                pass
        elif own_time > 10 and self.starting_time-own_time >7:
            pyautogui.click(click_from_x, click_from_y)
            #time.sleep(0.1)
            pyautogui.click(click_to_x, click_to_y)

    def make_move(self):
        fen, prev_move, prev_fen, white_time, black_time, game_end = self.get_next_move(self.last_fen)
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
        status = self.engine_moves(white_time, black_time, prev_fen, prev_move)
        if status[0] != 'GAME_OVER':
            # execute move
            move_uci = status[1]
            click_from_x, click_from_y, click_to_x, click_to_y = self.find_clicks(move_uci)
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

    def get_next_move(self, last_fen):
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
                    page = requests.get(self.url, timeout=0.5)
                except requests.exceptions.Timeout:
                    # too many requests
                    print('Timeout')
                    sound_file = "alert.mp3"
                    os.system("mpg123 " + sound_file)
                    continue  
                
                fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text) 
                prev_move = re.findall('uci\":\"(.{3,5})\"', page.text)
                if len(prev_move) == 0:
                    prev_move = False
                else:
                    prev_move = prev_move[-1]
                
                result_search = re.findall('Result', page.text)
                if len(result_search) > 0:
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
                    print('too many requests, trying again')
                    sound_file = "alert.mp3"
                    os.system("mpg123 " + sound_file)
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
                return '','','','','', game_end
            
            if last_fen != fen and fen.split()[-5] == lookout:
                # we have found new updated fen
                return fen, prev_move, prev_fen, white_time, black_time, game_end

URL = 'https://lichess.org/GlYCARuKJKOp'
finder = GameFinder(USERNAME)
finder.run()
