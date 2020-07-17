#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 13:27:06 2020

@author: jx283

This is a program which initiates a game between two engines, or engine and player
"""
import time
import gc
import datetime
import os

import chess
import chess.engine
import chess.pgn


from engine_1_1 import AtomicSamurai

from simplex_engine import Simplex
from gnu_engine import GNUChess
from gnu_bullet_engine import GNUChessBullet


import chess.svg

from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QApplication, QWidget

STOCKFISH = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")

class Game:
    ''' A game instance. Each inputted engine must have a
        update_board() function
        get_board() function
        make_move() function
        reset() function
        .resigned attribute
    '''
    def __init__(self, engine_1, engine_2, pos_fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', move_cap=None, time=None):
        self.white = engine_1
        self.black = engine_2
        self.display_board = chess.Board(pos_fen)
        if move_cap is None:
            self.move_cap = 100 # all games must end after 100 moves
        else:
            self.move_cap = move_cap
        # if time isn't None, then this is a timed game with each player getting (time) seconds
        if time is not None:
            self.white_time = time
            self.black_time = time
            self.timing = True
        else:
            self.white_time = None
            self.black_time = None
            self.timing = False
        self.starting_time = time
        
        self.stockfish = STOCKFISH
    
    def evaluate_result(self):
        ''' When this function is called we must have a game result depending
            on stockfish evaluation, regardless whether it is checkmate or not.
            If abs(eval) > 2 we have a non-draw result. '''
        eval_ = str(self.stockfish.analyse(self.display_board, chess.engine.Limit(time=5))["score"])
        try:
            eval_ = int(eval_)
        except ValueError:
            if eval_[1] == '-':
                eval_ = -10000
            else:
                eval_ = 10000
        if eval_ > 200:
            return '1-0'
        elif eval_ < -200:
            return '0-1'
        else:
            return '1/2-1/2'
        
    
    def play_game(self):
        ''' Plays one move on the board using specified engines. '''
        if self.display_board.is_game_over():
            return ['GAME_OVER', self.display_board.result()]
        elif self.display_board.fullmove_number > self.move_cap:
            result = self.evaluate_result()
            return ['GAME_OVER', result]
            
        if self.display_board.turn == chess.WHITE:
            player = self.white
        else:
            player = self.black
        
        player.update_board(self.display_board)
        # we parse in remaining time values as a dictionary
        time_dic = {'starting_time':self.starting_time, 'white_time': self.white_time, 'black_time': self.black_time}
        # start player clock
        start_time = time.time()
        player.make_move(time_dic=time_dic)
        finish_time = time.time()
        time_taken = finish_time - start_time
        if self.timing:
            if player == self.white:
                self.white_time -= time_taken
                if self.white_time < 0:
                    self.white.resigned = True
                    print ('White has timed out.')
            else:
                self.black_time -= time_taken
                if self.black_time < 0:
                    self.black.resigned = True
                    print ('Black has timed out.')
        
        
        # check if player has resigned/timed out
        if player.resigned:
            if player == self.white:
                result = '0-1'
            else:
                result = '1-0'
            return ['GAME_OVER', result]
        
        self.display_board = player.get_board().copy()
        
        print('White time: ', round(self.white_time,1), 'Black time: ', round(self.black_time,1))
        return ['STILL_PLAYING', None]
    
    def reset(self):
        ''' Resets the game. '''
        self.white.reset()
        self.black.reset()
        self.display_board = self.white.get_board().copy()
        if self.timing:
            self.white_time = self.starting_time
            self.black_time = self.starting_time
    
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setGeometry(100, 100, 600, 600)

        self.widgetSvg = QSvgWidget(parent=self)
        self.widgetSvg.setGeometry(10, 10, 560, 560)

        self.chessboard = chess.Board()

        self.chessboardSvg = chess.svg.board(self.chessboard).encode("UTF-8")
        self.widgetSvg.load(self.chessboardSvg)
    
    def update_board(self, fen):
        self.chessboard.set_fen(fen)
        self.chessboardSvg = chess.svg.board(self.chessboard).encode("UTF-8")
        self.widgetSvg.load(self.chessboardSvg)
        self.update()

SAVE_PGNS = 'Engine_games/'

if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    
    write_pgn=True
    
    # if we are priting the games, first clear the directories
    if write_pgn:
        for file in os.listdir('Engine_games/'):
            os.remove('Engine_games/'+file)
        for file in os.listdir('Mistakes'):
            os.remove('Mistakes/log.txt')
    
    white_wins = 0
    black_wins = 0
    game = Game(GNUChessBullet(), AtomicSamurai(playing_side=chess.BLACK), move_cap=None, time=60)
    # game = Game(GNUChess(),Simplex(), move_cap=30)
    for i in range(10):
        game_name = str(datetime.datetime.now())
        pgn_file = SAVE_PGNS + game_name + '.pgn'
        
        gc.collect()
        game.reset()
        
        while True:
            
            app.processEvents()
            a = game.play_game()
            if a[0] == 'GAME_OVER':
                # game has ended
                
                save_game = chess.pgn.Game.from_board(game.display_board)
                save_game.headers['Result'] = a[1]
                if a[1] == '1-0':
                    white_wins += 1
                elif a[1] == '0-1':
                    black_wins += 1
                else:
                    white_wins += 0.5
                    black_wins += 0.5
                
                save_game.headers['White'] = game.white.name
                save_game.headers['Black'] = game.black.name
                print(save_game)
                
                if write_pgn:
                    with open(pgn_file, 'a') as f:
                        f.write(str(save_game))
                        f.write('\n')
                        f.write('\n')
                        f.write('\n')
                
                break
            window.update_board(game.display_board.fen())
    
    print (white_wins, '-', black_wins)
    app.exec()
