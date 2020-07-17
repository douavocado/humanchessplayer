#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 15:09:10 2020

@author: jx283
"""

import chess
import chess.engine

GNU = chess.engine.SimpleEngine.popen_uci("/usr/local/bin/gnuchessu")

class GNUChess:
    ''' Engine with blitz elo ~2780 '''
    def __init__(self, board_fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        self.engine = GNU
        self.board = chess.Board(board_fen)
        self.name = 'GNU Chess'
        self.resigned = False
    
    def update_board(self, board):
        self.board = board.copy()
    
    def get_board(self):
        return self.board
    
    def make_move(self, time_dic=None):
        result = self.engine.play(self.board, chess.engine.Limit(time=1))
        self.board.push(result.move)
    
    def reset(self):
        self.board.clear()
        self.board.reset_board()
        self.board.set_castling_fen('KQkq')
        self.board.turn = chess.WHITE