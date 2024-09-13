# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 15:51:15 2024

@author: xusem
"""

import os
import pyautogui
import random
import chess
import requests
import re
from bs4 import BeautifulSoup
import configparser
from requests_html import HTMLSession
import cv2
import numpy as np
import ctypes

from engine_1_5 import AtomicSamurai

import time


def is_capslock_on():
    return True if ctypes.WinDLL("User32.dll").GetKeyState(0x14) else False


config = configparser.ConfigParser()
config.read('config.ini')

STEP = float((config['DEFAULT']['step']))
START_X = int(config['DEFAULT']['start_x']) + STEP/2
START_Y = int(config['DEFAULT']['start_y']) + STEP/2


def scrape_move_change(side):
    im = pyautogui.screenshot('last_board.png', region=(int(START_X-STEP/2),int(START_Y-STEP/2), int(8*STEP), int(8*STEP)))
    image = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    return get_move_change(image, bottom=side)

def get_move_change(image, bottom='w'):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    board_width, board_height = image.shape[:2]
    tile_width = board_width/8
    tile_height = board_height/8
    epsilon = 5
    if bottom == 'w':
        row_dic = {0:'8',1:'7',2:'6',3:'5',4:'4',5:'3',6:'2',7:'1'}
        column_dic = {0:'a',1:'b',2:'c',3:'d',4:'e',5:'f',6:'g',7:'h'}
    else:
        row_dic = {0:'1',1:'2',2:'3',3:'4',4:'5',5:'6',6:'7',7:'8'}
        column_dic = {0:'h',1:'g',2:'f',3:'e',4:'d',5:'c',6:'b',7:'a'}
    
    detected = []
    
    for i in range(64):
        column_i = i%8
        row_i = i // 8
        pixel_x = int(tile_width*column_i + epsilon)
        pixel_y = int(tile_height*row_i + epsilon)
        rgb = image[pixel_y, pixel_x, :]
        if (rgb == [59,155,143]).all() or (rgb == [145, 211, 205]).all():
            detected.append(column_dic[column_i]+row_dic[row_i])
    if len(detected) == 0:
        # print("Did not detect any move changes, returning None")
        return None
    elif len(detected) != 2:
        # print("Unexpectedly found {} detected change squares: {}".format(len(detected), detected))
        return None
    else:
        return [detected[0]+detected[1], detected[1] + detected[0]]


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
                    status = self.client.update()
                    if status == False:
                        break
            else:
                time.sleep(1)

class LichessClient:
    ''' Main class which interacts with Lichess. Plays and recieves moves. Called
        every instance of a game. '''
    
    def __init__(self, username, log=True, shadow_mode=False, url=None, side=None, t=None):
        self.username = username
        self.session = HTMLSession()
        if url is not None:
            self.url = url
            # getting player side and starting time
            
            page = self.session.get(url)
            # page = requests.get(self.url)
            
            if t == None:
                starting_time = float(re.findall('\"initial\":(\d{1,4})', page.text)[0])
            else:
                starting_time = t
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
        self.temp_shadow = self.shadow
        self.berserk = False
        self.last_scrape_time = 0        

    def update(self):
        ''' The main update step for the lichess client. We have two ways of looking
            for updates, one through screenshots, other through scraping.
            
            We do not want to scrape too much, because it is both time consuming and
            arouses suspicion. However scraping at a rate of twice per second should
            be slow enough. twice per second is not fast enough for bullet segments,
            so we should resort to scraping only when screenshots fail us. '''
        
        # update steps we need to go through
        # get time info, fen (board) info, prev fen (board) info, previous move made
        # whether the game has ended
        
        # first check whether we are entitled to a scrape
        if time.time() - self.last_scrape_time >0.5:
            if self.scrape() == False:
                return False
        # now check for updates via screenshot method. We shall spend a time of
        # min (5 secs, 1/10 of remaining time) doing this before resorting to scraping
        tries = 0
        tries_cap = min(80, int(self.own_time*8))
        got_update = None
        while got_update is None and tries < tries_cap:
            if self.side == chess.WHITE:
                bottom = "w"
            else:
                bottom = "b"
            
            got_update = scrape_move_change(bottom)
            tries += 1
        
        if got_update is None:
            # print("Didn't find change through screen shots, defaulting to scraping")
            if self.scrape() == False:
                return False
        else:
            moves = [chess.Move.from_uci(x) for x in got_update]
            if moves[0] in self.board.legal_moves:
                self.prev_fen = self.board.fen()
                self.board.push(moves[0])
                self.fen = self.board.fen()
                self.prev_move = moves[0].uci()
                # print("Found move from screenshots: {}".format(got_update[0]))
                
            elif moves[1] in self.board.legal_moves:
                self.prev_fen = self.board.fen()
                self.board.push(moves[1])
                self.fen = self.board.fen()
                self.prev_move = moves[1].uci()
                # print("Found move from screenshots: {}".format(got_update[1]))
                
            elif (got_update[0] == self.prev_move) or (got_update[1] == self.prev_move):
                #print("Found update move but has already been registered, skipping...")
                pass
            else:
                #print("Found move from screenshot but didn't make sense, resorting to scraping.")
                if self.scrape() == False:
                    return False
        
        # now play move/premove whatever is required
        if self.side == chess.WHITE:
            lookout = "w"
        else:
            lookout = "b"
        
        current_turn = self.fen.split()[-5]
        if current_turn == lookout:
            # then it is our turn
            self.engine_play_move()
        else:
            # it is not our turn, look for premoves
            if self.premove_fen != self.fen:
                self.premove()
    
    def premove(self):
        move_uci = self.engine.get_premove(self.fen)
        if move_uci is not None:
            click_from_x, click_from_y, click_to_x, click_to_y = self.find_clicks(move_uci)
            #print('execute normal move ' + move_uci)
            self.interact(click_from_x, click_from_y, click_to_x, click_to_y, self.own_time)
            self.premove_fen = self.fen
    
    def engine_play_move(self):
        self.engine.update_board(self.board)
        if self.berserk == True:
            starting_t = self.starting_time/2
        else:
            starting_t = self.starting_time
        time_dic = {'starting_time':starting_t, 'white_time': self.white_time, 'black_time':self.black_time}
        move_uci = self.engine.make_move(time_dic=time_dic, prev_fen=self.prev_fen, prev_move=self.prev_move)
        if move_uci is None:
            # this means we have resigned
            print("Game is too lost, resigning")
            time.sleep(3)
            click_from_x, click_from_y, click_to_x, click_to_y = self.resign()
        else:
            click_from_x, click_from_y, click_to_x, click_to_y = self.find_clicks(move_uci)
        #print('execute normal move ' + move_uci)
        successful = self.interact(click_from_x, click_from_y, click_to_x, click_to_y, self.own_time)
        
        if successful:
            self.board = self.engine.get_board().copy()
            self.prev_move = move_uci
            self.prev_fen = self.fen
            self.fen = self.board.fen()
    
    def resign(self):
        return START_X + 12.5*STEP, START_Y + 5.4*STEP, START_X + 12.5*STEP, START_Y + 5.4*STEP
    
    def scrape(self):
        page = self.session.get(self.url)
        # first check whether game has ended or not
        result_search = re.findall('Result', page.text)
        abort_search = re.findall('aborted after', page.text)
        if len(result_search) > 0 or len(abort_search) > 0:
            # game has ended
            return False
        
        # next get and update time info
        self.white_time = float(re.findall('white\":(\d{1,4}\.\d{1,2})', page.text)[0])
        self.black_time = float(re.findall('black\":(\d{1,4}\.\d{1,2})', page.text)[0])
        if self.side == chess.WHITE:
            self.own_time = self.white_time
        else:
            self.own_time = self.black_time
        
        # now get board information
        fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
        
        if len(fen_search) == 0:
            self.fen = chess.STARTING_FEN
            # for obvious move purposes, we want the last move also
            self.prev_fen = False            
        else:
            if self.fen != fen_search[-1]:
                self.fen = fen_search[-1]
            if len(fen_search) > 1:
                self.prev_fen = fen_search[-2]
            else:
                self.prev_fen = False
        self.board = chess.Board(self.fen)
        # previous move
        prev_move_search = re.findall('uci\":\"(.{3,5})\"', page.text)
        if len(prev_move_search) == 0:
            self.prev_move = False
        else:
            self.prev_move = prev_move_search[-1]
        
        self.last_scrape_time = time.time()
    
    def set_game(self, url, side=None, t=None):
        ''' Once client has found game, sets up game parameters. '''
        self.url = url
        # getting player side and starting time
        page = self.session.get(url)
        # page = requests.get(self.url)
        if t == None:
            starting_time = float(re.findall('\"initial\":(\d{1,4})', page.text)[0])
        else:
            starting_time = t
        if side is None:
            soup = BeautifulSoup(page.text, 'html.parser')
            white_username = soup.findAll("div", {"class": "player color-icon is white text"})[0].text.split()[0]
            if white_username == self.username:
                self.side = chess.WHITE
            else:
                self.side = chess.BLACK
        else:
            self.side = side
        
        fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
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
        
        self.last_caps_status = is_capslock_on()
        self.last_check_caps_lock = time.time()
        self.prev_fen = prev_fen
        self.fen = fen
        self.board = chess.Board(fen)        
        berserk_search = re.findall(rf'\"username\"\:\"{self.username}\".{{110,180}}\"berserk\"\:true', page.text)
        if len(berserk_search) > 0:
            print('Detected berserk! New starting time: ', self.starting_time/2)
            self.berserk = True
        else:
            self.berserk = False
            
        self.white_time = float(re.findall('white\":(\d{1,4}\.\d{1,2})', page.text)[0])
        self.black_time = float(re.findall('black\":(\d{1,4}\.\d{1,2})', page.text)[0])
        if self.side == chess.WHITE:
            self.own_time = self.white_time
        else:
            self.own_time = self.black_time
        self.starting_time = starting_time
        self.temp_shadow = self.shadow
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
        self.engine.own_time = starting_time
        self.engine.opp_time = starting_time
        self.engine.quick_move = False
        self.engine.win_percentage = 50
        self.engine.king_dang = 0
        self.engine.fens.clear()
        self.last_scrape_time = time.time()
        self.premove_fen = None
        self.prev_move = False
        
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
        # if override key is pressed, then continue
        # if in premove mode, checking for capslock takes alot of time, so we only check for caps lock every two seconds
        if own_time > 10:
            self.last_check_caps_lock = time.time()
            self.last_caps_status = is_capslock_on()
            if self.last_caps_status:                
                return False
        else:
            time_now = time.time()
            if time_now - self.last_check_caps_lock > 2:
                self.last_check_caps_lock = time_now
                self.last_caps_status = is_capslock_on()
            if self.last_caps_status:
                return False
        # click somewhere blank to reset the mouse click
        pyautogui.click(START_X+7.6*STEP, START_Y+3.5*STEP, button='left')
        if self.berserk:
            starting_t = self.starting_time/2
        else:
            starting_t = self.starting_time
        if premove and self.temp_shadow == False:
            #print('yes i made premove')
            # pyautogui.moveTo(click_from_x, click_from_y)
            # pyautogui.dragTo(click_to_x, click_to_y, 0.2, button='left')
            pyautogui.click(click_from_x, click_from_y, button='left')
            pyautogui.click(click_to_x, click_to_y, button='left')
        else:
            if starting_t < 16 or own_time < 15 and self.temp_shadow == False:
                if self.engine.big_material_take == True or self.engine.mate_in_one == True:
                    # opposition just hung a big piece or next move is mate in on
                    # delay for a bit to simulate the surprise/intrigue by a human player
                    time.sleep(random.randint(10,15)*self.starting_time/1000)
                else:
                    #pass
                    if random.random() <0.01:
                        time.sleep(random.randint(1,2)/1.5)
                    else:
                        time.sleep(random.randint(20,100)/1000)
                pyautogui.click(click_from_x, click_from_y, button='left')
                pyautogui.click(click_to_x, click_to_y, button='left')
                # pass
                
            elif starting_t > 61 and own_time > 10 and starting_t-own_time >7:
                # first assert it is actually my move
                # page = requests.get(self.url)
                page = self.session.get(self.url)
                fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
                if self.side == chess.WHITE:
                    lookout = 'w'
                else:
                    lookout = 'b'
                if len(fen_search) == 0:
                    fen = chess.STARTING_FEN
                else:
                    fen = fen_search[-1]
                if fen == self.fen:
                    if self.temp_shadow == True:
                        pyautogui.click(click_from_x, click_from_y, button='right')
                        pyautogui.click(click_to_x, click_to_y, button='right')
                    else:
                        if self.engine.big_material_take == True or self.engine.mate_in_one == True:
                            # opposition just hung a big piece or next move is mate in one
                            # print('hung big piece!')
                            # print(self.board)
                            time.sleep(random.randint(15,30)*self.starting_time/1000)
                        pyautogui.click(click_from_x, click_from_y, button='left')
                        pyautogui.click(click_to_x, click_to_y, button='left')
                else:
                    print('Detected human interference!, passing move for now...')
            elif own_time > self.engine.bullet_threshold and starting_t-own_time > 3:
                if self.temp_shadow == True:
                    pyautogui.click(click_from_x, click_from_y, button='right')
                    pyautogui.click(click_to_x, click_to_y, button='right')
                else:
                    if self.engine.big_material_take == True or self.engine.mate_in_one == True:
                        # opposition just hung a big piece or next move is mate in one
                        # print('hung big piece!')
                        # print(self.board)
                        time.sleep(random.randint(15,30)*self.starting_time/1000)
                    elif self.engine.quick_move == True:
                        if random.random() < 0.7:
                            wait_time = max(0.05, 0.2+np.random.randn()/8)
                        else:
                            wait_time = max(0.05, 0.7+np.random.randn()/6)
                            time.sleep(random.randint(5,35)/100)
                    else:
                        if self.engine.long_think:
                            time.sleep(4+3*random.random())
                        else:
                            if random.random() < 0.8:
                                wait_time = max(0.05, 0.8+np.random.randn()/4)
                            elif random.random() < 0.8:
                                wait_time = max(0.05, 1.5+np.random.randn()/2)
                            else:
                                if own_time > 20:
                                    wait_time = max(0.05, 7+np.random.randn()*2)
                                else:
                                    wait_time = max(0.05, 3+np.random.randn())
                            time.sleep(wait_time)
                    pyautogui.click(click_from_x, click_from_y, button='left')
                    pyautogui.click(click_to_x, click_to_y, button='left')
        return True

# URL = 'https://lichess.org/GlYCARuKJKOp'