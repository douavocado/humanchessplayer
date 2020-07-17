#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 20:42:52 2020

@author: jx283

Given a pgn file, this program will read the game and analyse it.
"""
import os

import chess
import chess.engine
import chess.pgn

STOCKFISH = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")

def calculate_loss(board, move):
    ''' Given a certain move in uci in a position, calculate how far from perfect
        the move is from the best move. '''
    best_move = STOCKFISH.analyse(board, chess.engine.Limit(depth=20), multipv=1)
    
    info = best_move[0]
    # extracting information from analysis info returned by stockfish
    best_move_uci = str(info['pv'][0])
    evaluation_str = str(info['score'])
    
    # see if the evaluation is some sort of mating eval for example #-2
    # would mean would receive mate from opposition in 2 plies
    try:
        eval_score = int(evaluation_str)
    except ValueError:
        # mating sequence received
        mate_in = int(str(info['score'])[2:])
        if str(info['score'])[1] == '-':
            # we are recieving mate in the variation
            # give a very negative evaluation, with more negative the more
            # immediate the mate
            eval_score = (mate_in-50)*100
            
        elif str(info['score'])[1] == '+':
            # we are giving mate in this variation
            eval_score = (50-mate_in)*100
            
        else:
            raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
            
    best_move_eval = eval_score      
    # now calculate the value of the move
    move_obj = chess.Move.from_uci(move)
    analysis = STOCKFISH.analyse(board, chess.engine.Limit(depth=20), multipv=1, root_moves = [move_obj])
    
    info = analysis[0]
    # extracting information from analysis info returned by stockfish
    move_uci = str(info['pv'][0])
    evaluation_str = str(info['score'])
    
    # see if the evaluation is some sort of mating eval for example #-2
    # would mean would receive mate from opposition in 2 plies
    try:
        eval_score = int(evaluation_str)
    except ValueError:
        # mating sequence received
        mate_in = int(str(info['score'])[2:])
        if str(info['score'])[1] == '-':
            # we are recieving mate in the variation
            # give a very negative evaluation, with more negative the more
            # immediate the mate
            eval_score = (mate_in-50)*100
            
        elif str(info['score'])[1] == '+':
            # we are giving mate in this variation
            eval_score = (50-mate_in)*100
            
        else:
            raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
    eval_diff = best_move_eval - eval_score
    if eval_diff < 0:
        eval_diff = 0
    
    return eval_diff

def get_eval_from_pos(board):
    ''' Returns absolute integer value i.e. a negative score means the position
        favours black. '''
    info = STOCKFISH.analyse(board, chess.engine.Limit(time=1))
    evaluation_str = str(info["score"])
    # see if the evaluation is some sort of mating eval for example #-2
    # would mean would receive mate from opposition in 2 plies
    try:
        eval_score = int(evaluation_str)
    except ValueError:
        # mating sequence received
        mate_in = int(str(info['score'])[2:])
        if str(info['score'])[1] == '-':
            # we are recieving mate in the variation
            # give a very negative evaluation, with more negative the more
            # immediate the mate
            eval_score = (mate_in-50)*100
            
        elif str(info['score'])[1] == '+':
            # we are giving mate in this variation
            eval_score = (50-mate_in)*100
            
        else:
            raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
    if board.turn == chess.WHITE:
        eval_score = eval_score
    else:
        eval_score = -eval_score
    
    return eval_score

def evaluate_game(game):
    ''' Takes in a chess.Game() instance and plays through all the moves,
        keeping track of the evaluation at each position in the form of an
        ordered list. '''
    evals = []
    board = game.board()
    turn = board.turn
    
    eval_score = get_eval_from_pos(board)
    evals.append(eval_score)
    
    # iterate through all moves and evaluate the score for one second
    move_number = 1
    for move in game.mainline_moves():
        print('ply: ', move_number, '.', board.san(move))
        board.push(move)
        eval_score = get_eval_from_pos(board)
        evals.append(eval_score)
        move_number += 1
    
    return evals

def identify_mistakes(moves, eval_list, side):
    ''' Given a list of moves and an evaluation list, the function
        goes through the game, identifies mistakes and returns as dictionary
        with key the board fen before the mistake, and the mistake move in 
        uci form. '''
    
    mistake_markers = [] # the indices at which we identify the mistakes
    total_centipawn_loss = 0
    move_no = 0
    whites_move = True
    for i in range(len(eval_list)):
        if i == 0:
            continue
        if whites_move and side == chess.WHITE:
            move_no += 1
            if eval_list[i] - eval_list[i-1] < 100: # have a white mistake
                mistake_markers.append(i-1)
            total_centipawn_loss += max(0, eval_list[i-1] - eval_list[i])
        elif not whites_move and side == chess.BLACK:
            move_no += 1
            if eval_list[i] - eval_list[i-1] > 100: # have a black mistake
                mistake_markers.append(i-1)
            total_centipawn_loss += max(0, eval_list[i] - eval_list[i-1])
        
        if whites_move == True:
            whites_move = False
        else:
            whites_move = True
    
    return_dic = {}
    board = chess.Board()
    for mistake_index in mistake_markers:
        board.reset()
        for i in range(mistake_index):
            board.push(moves[i])
        return_dic[board.fen()] = moves[mistake_index].uci()
    
    avg_centipawn_loss = round(total_centipawn_loss/move_no)
    
    return return_dic, avg_centipawn_loss

MISTAKE_LOG = 'Mistakes/log.txt'
        
if __name__ == '__main__':
    for file in os.listdir('Engine_games/'):
        pgn = open("Engine_games/" + file)
        
        game = chess.pgn.read_game(pgn)
        # try:
        #     if game.headers['Result'] != '1-0':
        #         continue
        # except:
        #     continue
        eval_list = evaluate_game(game)
        
        mistake_positions, avg_loss = identify_mistakes(list(game.mainline_moves()), eval_list, chess.BLACK)
        with open(MISTAKE_LOG, 'a') as f:
            f.write('\n')
            f.write(str(mistake_positions))
            f.write('Average centipawn loss: '+ str(avg_loss))
            f.write('\n')