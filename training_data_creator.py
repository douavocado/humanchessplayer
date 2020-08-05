#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 17 16:13:00 2020

@author: jx283
"""
import os
import chess
import chess.pgn
import pandas as pd
import numpy as np

'''
each position is a 768-element list of numbers(each element can be from 1-12 for each of the pieces * 64 elements) indicating what piece is in the square
blank square:  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
'p':           [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
'n':           [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
'b':           [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
'r':           [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
'q':           [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
'k':           [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
'P':           [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
'N':           [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
'B':           [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
'R':           [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
'Q':           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
'K':           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
'''


def position_list_one_hot(self):
    '''method added to the python-chess library for faster
    conversion of board to one hot encoding. Resulted in 100%
    increase in speed by bypassing conversion to fen() first.
    '''
    builder = []
    builder_append = builder.append
    for square in chess.SQUARES_180:
        mask = chess.BB_SQUARES[square]

        if not self.occupied & mask:
            builder.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif bool(self.occupied_co[chess.WHITE] & mask):
            if self.pawns & mask:
                builder.extend([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
            elif self.knights & mask:
                builder.extend([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
            elif self.bishops & mask:
                builder.extend([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0])
            elif self.rooks & mask:
                builder.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0])
            elif self.queens & mask:
                builder.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0])
            elif self.kings & mask:
                builder.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
        elif self.pawns & mask:
            builder.extend([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif self.knights & mask:
            builder.extend([0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif self.bishops & mask:
            builder.extend([0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif self.rooks & mask:
            builder.extend([0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0])
        elif self.queens & mask:
            builder.extend([0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])
        elif self.kings & mask:
            builder.extend([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0])

    return builder


def position_list(self):
    '''same as position_list_one_hot except this is converts pieces to
    numbers between 1 and 12. Used for piece_moved function'''
    builder = []
    builder_append = builder.append
    for square in chess.SQUARES_180:
        mask = chess.BB_SQUARES[square]

        if not self.occupied & mask:
            builder_append(0)
        elif bool(self.occupied_co[chess.WHITE] & mask):
            if self.pawns & mask:
                builder_append(7)
            elif self.knights & mask:
                builder_append(8)
            elif self.bishops & mask:
                builder_append(9)
            elif self.rooks & mask:
                builder_append(10)
            elif self.queens & mask:
                builder_append(11)
            elif self.kings & mask:
                builder_append(12)
        elif self.pawns & mask:
            builder_append(1)
        elif self.knights & mask:
            builder_append(2)
        elif self.bishops & mask:
            builder_append(3)
        elif self.rooks & mask:
            builder_append(4)
        elif self.queens & mask:
            builder_append(5)
        elif self.kings & mask:
            builder_append(6)

    return builder

chess.BaseBoard.position_list_one_hot = position_list_one_hot
chess.BaseBoard.position_list = position_list

def piece_moved(position1, position2):
    '''Main data conversion function.
    step 1: checks the difference between two positions and returns a list
            of the affected squares.
    step 2: checks whether it is a normal move (only two squares affected), or
            en passant (3 squares affected) or castling (4 squares affected)
            step 2a: If castling, the square moved from is where the king was
                     in the beginning of the turn. Square moved to is where
                     the king is at the end of the turn.
            step 2b: If en passant, square moved from is where the pawn was
                     at the beginning of the turn. Moved to is where the pawn
                     is at the end of the turn.
    step 3: Returns two ints with the square moved from, and square moved to
    '''
    affected_squares = []
    for i in range(64):  # Step 1
        if position1[i] != position2[i]:
            affected_squares.append(i)
    if len(affected_squares) > 2:  # Step 2
        for square in affected_squares:
            if position1[square] == 12 or position1[square] == 6:  # Step 2a
                moved_from = square
            if position2[square] == 12 or position2[square] == 6:
                moved_to = square
            if position1[square] == 0:  # Step 2b
                if position2[square] == 1:
                    moved_to = square
                    for square in affected_squares:
                        if position1[square] == 1:
                            moved_from = square
                elif position2[square] == 7:
                    moved_to = square
                    for square in affected_squares:
                        if position1[square] == 7:
                            moved_from = square
    else:
        if position2[affected_squares[0]] == 0:
            moved_from, moved_to = affected_squares[0], affected_squares[1]
        else:
            moved_from, moved_to = affected_squares[1], affected_squares[0]
    return moved_from #, moved_to

PGN_DIR = 'PGNs/'
SAVE_FILE = 'piece_selector/training_data_midgame_fics.h5'

game_count = 0
for pgn_batch in os.listdir(PGN_DIR):
    print (pgn_batch)
    pgn = open(PGN_DIR + pgn_batch)
    train_input, moved_from = [], []
    #while True:
    for i in range(700):
        game = chess.pgn.read_game(pgn)
        
        try:
            print (game_count, game.headers['Date'])
        except AttributeError:
            break
        
        try:
            board = game.board()  # set the game board
        except ValueError:
            # some sort of variant issue
            continue
        for move in list(game.mainline_moves())[:30]:
            board.push(move)
        
        for move in list(game.mainline_moves())[30:80]: # middlegame
            if board.turn: #if it's white's turn
                dummy_board_before = board.copy()
            else:
                board.push(move)
                continue
                #dummy_board_before = board.mirror()
            position1 = dummy_board_before.position_list()
            one_hot_position = dummy_board_before.position_list_one_hot()
            # if board.turn == chess.WHITE:
            #     one_hot_position.append(0)
            # else:
            #     one_hot_position.append(1)
            train_input.append(one_hot_position)
            board.push(move)

            # if board.turn == chess.WHITE:
            #     one_hot_position.append(0)
            # else:
            #     one_hot_position.append(1)
            
            if board.turn: #if it's white's turn
                dummy_board_after = board.mirror()
            else:
                dummy_board_after = board.copy()
            position2 = dummy_board_after.position_list()
            piece_from = piece_moved(position1, position2)
            moved_from.append(piece_from)
            # position1 = position2
        
        game_count += 1
        
    
    # try:
    position = np.array(train_input)
    moved_from = np.array(moved_from)
    moved_from_one_hot = np.zeros((moved_from.size, 64))
    moved_from_one_hot[np.arange(moved_from.size), moved_from] = 1
    try:
        existing_train_df = pd.read_hdf(SAVE_FILE, key='train')
        print('length of df so far', len(existing_train_df))
        existing_test_df = pd.read_hdf(SAVE_FILE, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(position)
    appended_test_df = pd.DataFrame(moved_from_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(SAVE_FILE, key='train')
    new_test_df.to_hdf(SAVE_FILE, key='test')
    # except:
    #     print(50*'-')
    #     print(50*'-')
    #     print('ERROR IN {}, GAME'.format(pgn_batch))
    #     print(50*'-')
    #     print(50*'-')