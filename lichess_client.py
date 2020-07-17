#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 30 16:08:33 2020

@author: jx283
"""
import os
import pyautogui
import chess
import requests
import re
from bs4 import BeautifulSoup

from selenium import webdriver

from engine_1_1 import AtomicSamurai

import time
from playsound import playsound

USERNAME = 'Moment_of_Inertia'

class LichessClient:
    ''' Main class which interacts with Lichess. Plays and recieves moves. '''
    def __init__(self, url, side=None, time=None):
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
        
        self.board = chess.Board()
        self.engine = AtomicSamurai(playing_side=self.side)
        self.starting_time = starting_time
        self.last_fen = chess.STARTING_FEN
        
        
        
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
    
    def interact(self, click_from_x, click_from_y, click_to_x, click_to_y):
        ''' Function which does the clicking on the screen, and makes the moves. '''
        # if self.starting_time > 61:
        #     # first assert it is actually my move
        #     page = requests.get(self.url)
        #     fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
        #     if self.side == chess.WHITE:
        #         lookout = 'w'
        #     else:
        #         lookout = 'b'
        #     if len(fen_search) == 0:
        #         fen = chess.STARTING_FEN
        #     else:
        #         fen = fen_search[-1]
        #     if fen.split()[-5] == lookout:        
        #         pyautogui.click(click_from_x, click_from_y)
        #         time.sleep(0.1)
        #         pyautogui.click(click_to_x, click_to_y)
        #     else:
        #         pass
        # else:
        pyautogui.click(click_from_x, click_from_y)
        #time.sleep(0.1)
        pyautogui.click(click_to_x, click_to_y)

    def make_move(self):
        fen, white_time, black_time = self.get_next_move(self.last_fen)
        self.last_fen = fen
        self.board = chess.Board(fen)
        status = self.engine_moves(white_time, black_time)
        if status[0] != 'GAME_OVER':
            # execute move
            move_uci = status[1]
            click_from_x, click_from_y, click_to_x, click_to_y = self.find_clicks(move_uci)

            self.interact(click_from_x, click_from_y, click_to_x, click_to_y)
            return True # move successful
        else:
            return False

    def engine_moves(self, white_time, black_time):
        if self.board.is_game_over():
            return ['GAME_OVER', self.board.result()]
        
        self.engine.update_board(self.board)
        time_dic = {'starting_time':self.starting_time, 'white_time': white_time, 'black_time': black_time}
        move_uci_played = self.engine.make_move(time_dic=time_dic)
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
            while successful_request == False:
                # if self.starting_time > 60:
                #      time.sleep(self.starting_time/1000)
                page = requests.get(self.url)
                print(time.time())
                fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
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
            else:
                fen = fen_search[-1]
            
            if last_fen != fen and fen.split()[-5] == lookout:
                # we have found new updated fen
                return fen, white_time, black_time

URL = 'https://lichess.org/GlYCARuKJKOp'
client = LichessClient(URL, side=False)
while True:
    status = client.make_move()
    if status == False:
        break