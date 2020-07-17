#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 30 11:32:43 2020

@author: jx283
"""

import chess
import chess.engine

GNU = chess.engine.SimpleEngine.popen_uci("/usr/local/bin/gnuchessu")

class GNUChessBullet:
    ''' Engine with bullet elo ~2780, plays bullet. '''
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
        result = self.engine.play(self.board, chess.engine.Limit(time=0.3))
        self.board.push(result.move)
    
    def reset(self):
        self.board.clear()
        self.board.reset_board()
        self.board.set_castling_fen('KQkq')
        self.board.turn = chess.WHITE