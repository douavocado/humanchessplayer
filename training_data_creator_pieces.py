#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 13:06:01 2020

@author: jx283
"""

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

def which_piece(board_pos, square):
    ''' Gets type of piece on certain square from position in format from
        board.position_list() '''
    if board_pos[square] == 7:
        return 'white_pawn'
    elif board_pos[square] == 8:
        return 'white_knight'
    elif board_pos[square] == 9:
        return 'white_bishop'
    elif board_pos[square] == 10:
        return 'white_rook'
    elif board_pos[square] == 11:
        return 'white_queen'
    elif board_pos[square] == 12:
        return 'white_king'
    elif board_pos[square] == 1:
        return 'black_pawn'
    elif board_pos[square] == 2:
        return 'black_knight'
    elif board_pos[square] == 3:
        return 'black_bishop'
    elif board_pos[square] == 4:
        return 'black_rook'
    elif board_pos[square] == 5:
        return 'black_queen'
    elif board_pos[square] == 6:
        return 'black_king'
    else:
        raise Exception("square is a blank space, unable to detect moved from piece")
    

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
    return moved_from , moved_to

PGN_DIR = 'PGNs/'
white_pawn_file = 'piece_models_to/white_pawn_tr.h5'
white_knight_file = 'piece_models_to/white_knight_tr.h5'
white_bishop_file = 'piece_models_to/white_bishop_tr.h5'
white_rook_file = 'piece_models_to/white_rook_tr.h5'
white_queen_file = 'piece_models_to/white_queen_tr.h5'
white_king_file = 'piece_models_to/white_king_tr.h5'
black_pawn_file = 'piece_models_to/black_pawn_tr.h5'
black_knight_file = 'piece_models_to/black_knight_tr.h5'
black_bishop_file = 'piece_models_to/black_bishop_tr.h5'
black_rook_file = 'piece_models_to/black_rook_tr.h5'
black_queen_file = 'piece_models_to/black_queen_tr.h5'
black_king_file = 'piece_models_to/black_king_tr.h5'

game_count = 0
for pgn_batch in os.listdir(PGN_DIR):
    pgn = open(PGN_DIR + pgn_batch)
    white_pawn = []
    white_knight = []
    white_bishop = []
    white_rook = []
    white_queen = []
    white_king = []
    black_pawn = []
    black_knight = []
    black_bishop = []
    black_rook = []
    black_queen = []
    black_king = []
    
    white_pawn_test = []
    white_knight_test = []
    white_bishop_test = []
    white_rook_test = []
    white_queen_test = []
    white_king_test = []
    black_pawn_test = []
    black_knight_test = []
    black_bishop_test = []
    black_rook_test = []
    black_queen_test = []
    black_king_test = []
    #while True:
    for i in range(1500):
        game = chess.pgn.read_game(pgn)
        
        try:
            print (game_count, game.headers['Date'])
        except AttributeError:
            break
        
        board = game.board()  # set the game board
        # for move in list(game.mainline_moves()):
        #     board.push(move)
        
        first = True
        for move in list(game.mainline_moves()):
            position1 = board.position_list()            
            
            one_hot_position = board.position_list_one_hot()
            board.push(move)
            position2 = board.position_list()
            
            piece_from, piece_to = piece_moved(position1, position2)
            
            save_file_tag = which_piece(position1, piece_from)
            if save_file_tag == 'white_pawn':
                white_pawn.append(one_hot_position)
                white_pawn_test.append(piece_to)
            elif save_file_tag == 'white_knight':
                white_knight.append(one_hot_position)
                white_knight_test.append(piece_to)
            elif save_file_tag == 'white_bishop':
                white_bishop.append(one_hot_position)
                white_bishop_test.append(piece_to)
            elif save_file_tag == 'white_rook':
                white_rook.append(one_hot_position)
                white_rook_test.append(piece_to)
            elif save_file_tag == 'white_queen':
                white_queen.append(one_hot_position)
                white_queen_test.append(piece_to)
            elif save_file_tag == 'white_king':
                white_king.append(one_hot_position)
                white_king_test.append(piece_to)
            
            elif save_file_tag == 'black_pawn':
                black_pawn.append(one_hot_position)
                black_pawn_test.append(piece_to)
            elif save_file_tag == 'black_knight':
                black_knight.append(one_hot_position)
                black_knight_test.append(piece_to)
            elif save_file_tag == 'black_bishop':
                black_bishop.append(one_hot_position)
                black_bishop_test.append(piece_to)
            elif save_file_tag == 'black_rook':
                black_rook.append(one_hot_position)
                black_rook_test.append(piece_to)
            elif save_file_tag == 'black_queen':
                black_queen.append(one_hot_position)
                black_queen_test.append(piece_to)
            elif save_file_tag == 'black_king':
                black_king.append(one_hot_position)
                black_king_test.append(piece_to)
            #position1 = position2
        
        
        game_count += 1
        
    
    # try:
    white_pawn = np.array(white_pawn)
    white_pawn_test = np.array(white_pawn_test)
    white_pawn_one_hot = np.zeros((white_pawn_test.size, 64))
    white_pawn_one_hot[np.arange(white_pawn_test.size), white_pawn_test] = 1
    white_knight = np.array(white_knight)
    white_knight_test = np.array(white_knight_test)
    white_knight_one_hot = np.zeros((white_knight_test.size, 64))
    white_knight_one_hot[np.arange(white_knight_test.size), white_knight_test] = 1
    white_bishop = np.array(white_bishop)
    white_bishop_test = np.array(white_bishop_test)
    white_bishop_one_hot = np.zeros((white_bishop_test.size, 64))
    white_bishop_one_hot[np.arange(white_bishop_test.size), white_bishop_test] = 1
    white_rook = np.array(white_rook)
    white_rook_test = np.array(white_rook_test)
    white_rook_one_hot = np.zeros((white_rook_test.size, 64))
    white_rook_one_hot[np.arange(white_rook_test.size), white_rook_test] = 1
    white_queen = np.array(white_queen)
    white_queen_test = np.array(white_queen_test)
    white_queen_one_hot = np.zeros((white_queen_test.size, 64))
    white_queen_one_hot[np.arange(white_queen_test.size), white_queen_test] = 1
    white_king = np.array(white_king)
    white_king_test = np.array(white_king_test)
    white_king_one_hot = np.zeros((white_king_test.size, 64))
    white_king_one_hot[np.arange(white_king_test.size), white_king_test] = 1
    
    black_pawn = np.array(black_pawn)
    black_pawn_test = np.array(black_pawn_test)
    black_pawn_one_hot = np.zeros((black_pawn_test.size, 64))
    black_pawn_one_hot[np.arange(black_pawn_test.size), black_pawn_test] = 1
    black_knight = np.array(black_knight)
    black_knight_test = np.array(black_knight_test)
    black_knight_one_hot = np.zeros((black_knight_test.size, 64))
    black_knight_one_hot[np.arange(black_knight_test.size), black_knight_test] = 1
    black_bishop = np.array(black_bishop)
    black_bishop_test = np.array(black_bishop_test)
    black_bishop_one_hot = np.zeros((black_bishop_test.size, 64))
    black_bishop_one_hot[np.arange(black_bishop_test.size), black_bishop_test] = 1
    black_rook = np.array(black_rook)
    black_rook_test = np.array(black_rook_test)
    black_rook_one_hot = np.zeros((black_rook_test.size, 64))
    black_rook_one_hot[np.arange(black_rook_test.size), black_rook_test] = 1
    black_queen = np.array(black_queen)
    black_queen_test = np.array(black_queen_test)
    black_queen_one_hot = np.zeros((black_queen_test.size, 64))
    black_queen_one_hot[np.arange(black_queen_test.size), black_queen_test] = 1
    black_king = np.array(black_king)
    black_king_test = np.array(black_king_test)
    black_king_one_hot = np.zeros((black_king_test.size, 64))
    black_king_one_hot[np.arange(black_king_test.size), black_king_test] = 1
    try:
        existing_train_df = pd.read_hdf(white_pawn_file, key='train')
        print('length of df so far white_pawn', len(existing_train_df))
        existing_test_df = pd.read_hdf(white_pawn_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(white_pawn)
    appended_test_df = pd.DataFrame(white_pawn_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(white_pawn_file, key='train')
    new_test_df.to_hdf(white_pawn_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(white_knight_file, key='train')
        print('length of df so far white_knight', len(existing_train_df))
        existing_test_df = pd.read_hdf(white_knight_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(white_knight)
    appended_test_df = pd.DataFrame(white_knight_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(white_knight_file, key='train')
    new_test_df.to_hdf(white_knight_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(white_bishop_file, key='train')
        print('length of df so far white_bishop', len(existing_train_df))
        existing_test_df = pd.read_hdf(white_bishop_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(white_bishop)
    appended_test_df = pd.DataFrame(white_bishop_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(white_bishop_file, key='train')
    new_test_df.to_hdf(white_bishop_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(white_rook_file, key='train')
        print('length of df so far white_rook', len(existing_train_df))
        existing_test_df = pd.read_hdf(white_rook_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(white_rook)
    appended_test_df = pd.DataFrame(white_rook_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(white_rook_file, key='train')
    new_test_df.to_hdf(white_rook_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(white_queen_file, key='train')
        print('length of df so far white_queen', len(existing_train_df))
        existing_test_df = pd.read_hdf(white_queen_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(white_queen)
    appended_test_df = pd.DataFrame(white_queen_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(white_queen_file, key='train')
    new_test_df.to_hdf(white_queen_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(white_king_file, key='train')
        print('length of df so far white_king', len(existing_train_df))
        existing_test_df = pd.read_hdf(white_king_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(white_king)
    appended_test_df = pd.DataFrame(white_king_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(white_king_file, key='train')
    new_test_df.to_hdf(white_king_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(black_pawn_file, key='train')
        print('length of df so far black_pawn', len(existing_train_df))
        existing_test_df = pd.read_hdf(black_pawn_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(black_pawn)
    appended_test_df = pd.DataFrame(black_pawn_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(black_pawn_file, key='train')
    new_test_df.to_hdf(black_pawn_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(black_knight_file, key='train')
        print('length of df so far black_knight', len(existing_train_df))
        existing_test_df = pd.read_hdf(black_knight_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(black_knight)
    appended_test_df = pd.DataFrame(black_knight_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(black_knight_file, key='train')
    new_test_df.to_hdf(black_knight_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(black_bishop_file, key='train')
        print('length of df so far black_bishop', len(existing_train_df))
        existing_test_df = pd.read_hdf(black_bishop_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(black_bishop)
    appended_test_df = pd.DataFrame(black_bishop_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(black_bishop_file, key='train')
    new_test_df.to_hdf(black_bishop_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(black_rook_file, key='train')
        print('length of df so far black_rook', len(existing_train_df))
        existing_test_df = pd.read_hdf(black_rook_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(black_rook)
    appended_test_df = pd.DataFrame(black_rook_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(black_rook_file, key='train')
    new_test_df.to_hdf(black_rook_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(black_queen_file, key='train')
        print('length of df so far black_queen', len(existing_train_df))
        existing_test_df = pd.read_hdf(black_queen_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(black_queen)
    appended_test_df = pd.DataFrame(black_queen_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(black_queen_file, key='train')
    new_test_df.to_hdf(black_queen_file, key='test')
    
    try:
        existing_train_df = pd.read_hdf(black_king_file, key='train')
        print('length of df so far black_king', len(existing_train_df))
        existing_test_df = pd.read_hdf(black_king_file, key='test')
    except:
        existing_train_df = pd.DataFrame()
        existing_test_df = pd.DataFrame()
    appended_train_df = pd.DataFrame(black_king)
    appended_test_df = pd.DataFrame(black_king_one_hot)
    new_train_df = pd.concat([existing_train_df, appended_train_df])
    new_test_df = pd.concat([existing_test_df, appended_test_df])
    new_train_df.to_hdf(black_king_file, key='train')
    new_test_df.to_hdf(black_king_file, key='test')
    # except:
    #     print(50*'-')
    #     print(50*'-')
    #     print('ERROR IN {}, GAME'.format(pgn_batch))
    #     print(50*'-')
    #     print(50*'-')