#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 13:38:27 2020

@author: jx283
"""

import pandas as pd
import numpy as np

PGN_DIR = 'PGNs/'
SAVE_FILE = 'piece_selector/training_data_midgame.h5'

def view_board_from_np(board, piece_moved):
    ''' Takes in board as an entry from the .h5 pandas dataframe and
        similarly the test result to return a graphic of piece moved '''
    output_board_one_hot = board
    
    square_one_hot = []
    squares = []
    for i, element in enumerate(output_board_one_hot):
        square_one_hot.append(element)
        if (i+1) % 12 == 0:
            squares.append(square_one_hot)
            square_one_hot = []

    builder = []
    for i, piece_one_hot in enumerate(squares):
        if piece_one_hot == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]:
            builder.append('.')
        elif piece_one_hot == [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]:
            builder.append('p')
        elif piece_one_hot == [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]:
            builder.append('n')
        elif piece_one_hot == [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]:
            builder.append('b')
        elif piece_one_hot == [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]:
            builder.append('r')
        elif piece_one_hot == [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]:
            builder.append('q')
        elif piece_one_hot == [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]:
            builder.append('k')
        elif piece_one_hot == [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]:
            builder.append('P')
        elif piece_one_hot == [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]:
            builder.append('N')
        elif piece_one_hot == [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]:
            builder.append('B')
        elif piece_one_hot == [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]:
            builder.append('R')
        elif piece_one_hot == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]:
            builder.append('Q')
        elif piece_one_hot == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]:
            builder.append('K')
        if (i+1) % 8 == 0:
            builder.append('\n')
        else:
            builder.append(' ')
    
    for i in range(64):
        if piece_moved[i] == 0:
            pass
        elif piece_moved[i] == 1:
            builder[2*i] = 'X'
    
    return (''.join(builder))


training_file_train_df = pd.read_hdf(SAVE_FILE, key='train')

training_file_test_df = pd.read_hdf(SAVE_FILE, key='test')

print(view_board_from_np(training_file_train_df.iloc[2],training_file_test_df.iloc[2]))
#print(training_file_test_df)