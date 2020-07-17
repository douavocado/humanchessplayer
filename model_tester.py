#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 16:25:25 2020

@author: jx283
"""
import numpy as np
from tensorflow.keras.models import load_model

# loading piece_selector model
opening_selector = load_model('piece_selector_models/piece_selector_opening.h5')
midgame_selector = load_model('piece_selector_models/piece_selector_midgame.h5')
endgame_selector = load_model('piece_selector_models/piece_selector_endgame.h5')

move_from_piece = load_model('piece_move_from_models/white_pawn_model.h5')

move_to_piece = load_model('piece_move_to_models/white_bishop_model.h5')


def make_board():
    next_pos = ['r', '.', 'b', 'q', 'k', 'b', 'n', 'r',
                'p', 'p', '.', '.', 'p', 'p', 'p', 'p',
                '.', '.', 'n', '.', '.', '.', '.', '.',
                '.', '.', 'p', 'p', '.', '.', '.', '.',
                '.', '.', '.', '.', 'P', '.', '.', '.',
                '.', 'P', '.', '.', '.', '.', '.', '.',
                'P', '.', 'P', 'P', '.', 'P', 'P', 'P',
                'R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']

    return next_pos

def convert_input():
    next_position = make_board()
    input_board = []
    for input_square in next_position:
        if input_square == '.':
            input_board.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif input_square == 'p':
            input_board.extend([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif input_square == 'n':
            input_board.extend([0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif input_square == 'b':
            input_board.extend([0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        elif input_square == 'r':
            input_board.extend([0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0])
        elif input_square == 'q':
            input_board.extend([0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])
        elif input_square == 'k':
            input_board.extend([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0])
        elif input_square == 'P':
            input_board.extend([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
        elif input_square == 'N':
            input_board.extend([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        elif input_square == 'B':
            input_board.extend([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0])
        elif input_square == 'R':
            input_board.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0])
        elif input_square == 'Q':
            input_board.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0])
        elif input_square == 'K':
            input_board.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
    return np.reshape(np.array(input_board), (1, 8, 8, 12))

def convert_position_prediction(output_board_one_hot):
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

    return (''.join(builder))


def move_from(output_one_hot):
    board_position = make_board()
    builder = []
    for i, e in enumerate(output_one_hot):
        # print(e)
        if e == 0:
            builder.append(board_position[i])
        else:
            builder.append(str(e))
        if (i+1) % 8 == 0:
            builder.append('\n')
        else:
            builder.append(' ')
    return ''.join(builder)

def predict(model):
    board_input = convert_input().astype(float)
    # board_input = np.array(board_input).reshape(1, 8, 8, 12)
    prediction = model.predict(board_input)
    
    move = sorted(prediction[0])

    output_board_one_hot = []
    for i in prediction[0]:
        if i == move[-1]:
            output_board_one_hot.append(1)
        elif i == move[-2]:
            output_board_one_hot.append(2)
        elif i == move[-3]:
            output_board_one_hot.append(3)
        elif i == move[-4]:
            output_board_one_hot.append(4)
        elif i == move[-5]:
            output_board_one_hot.append(5)
        elif i == move[-6]:
            output_board_one_hot.append(6)
        elif i == move[-7]:
            output_board_one_hot.append(7)
        else:
            output_board_one_hot.append(0)

    print(move_from(output_board_one_hot))
    
predict(move_to_piece)
    