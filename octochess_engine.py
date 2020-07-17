#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 11:51:10 2020

@author: jx283

binary is incompatible?
"""

import chess
import chess.engine

OCTO = chess.engine.SimpleEngine.popen_uci("/usr/games/octochess")

class OctoChess:
    ''' Engine with blitz elo ~2750 '''
    def __init__(self, board_fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        self.engine = OCTO
        self.board = chess.Board(board_fen)
        self.name = 'OctoChess'
    
    def update_board(self, board):
        self.board = board.copy()
    
    def get_board(self):
        return self.board
    
    def make_move(self):
        result = self.engine.play(self.board, chess.engine.Limit(time=1))
        self.board.push(result.move)