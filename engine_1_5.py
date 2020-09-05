#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 22:35:01 2020

@author: jx283

This is the first version of the human chess engine. Here we utilize 
all individual piece models that predict where it moves to.

we are not using the piece move from models, we use the piece selector model
when the engine is blunder prone

This engine took 2 days to be banned, and has account handle DrActuallyMe

---------------------------------------------------------------------------
v1_2

This version updates the bullet side of the engine, and sharpens up moves including
takebacks.

---------------------------------------------------------------------------
v1_3

we improve the engine further by modelling move probabilities in order to best
predict human blunder prone moves during longer time controls

also we introduce in this version 'efficient mobility' to better model
circumstances in which the human blunders.

-----------------------------------------------
v1_4

In this version we seek to teach the engine how to premove on takebacks, particularly
in bullet games. In the future we look to implement this also in the last 10
seconds of the game, or in speed mode also for general moves and not just takebacks.

This helps with the variation of move times in general during bullet games.
Also implemented premoving in the last 10 seconds of game.

gmdolmatov and imcsabalogh got banned after 4 and 3 days respectively, after implementing
ultrabullet.

------------------------------------------------------------
v1_5

In this version we must severely handicap the ultrabullet mode/ premove mode,
as to reduce engine suspicion
"""
import datetime
import time
import psutil

from scipy.stats import chi2

import chess
import chess.engine

import numpy as np
from tensorflow.keras.models import load_model

import random
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

RAW_PATH = r'{}'.format(config['DEFAULT']['path'])
SEARCH_WIDTH = int(config['DEFAULT']['difficulty'])

# load all models

# loading piece_selector model
# opening_selector = load_model('piece_selector_models/piece_selector_opening.h5')
midgame_selector = load_model('piece_selector_models/piece_selector_midgame_lichess.h5')
# endgame_selector = load_model('piece_selector_models/piece_selector_endgame.h5')

# piece_selectors = {'opening': opening_selector,
#                    'midgame': midgame_selector,
#                    'endgame': endgame_selector}

pawn_model = load_model('piece_move_to_models/white_pawn_model.h5')
knight_model = load_model('piece_move_to_models/white_knight_model.h5')
bishop_model = load_model('piece_move_to_models/white_bishop_model.h5')
rook_model = load_model('piece_move_to_models/white_rook_model.h5')
queen_model = load_model('piece_move_to_models/white_queen_model.h5')
king_model = load_model('piece_move_to_models/white_king_model.h5')

e_pawn_model = load_model('piece_move_to_models/endgame_white_pawn.h5')
e_knight_model = load_model('piece_move_to_models/endgame_white_knight.h5')
e_bishop_model = load_model('piece_move_to_models/endgame_white_bishop.h5')
e_rook_model = load_model('piece_move_to_models/white_rook_model.h5')
e_queen_model = load_model('piece_move_to_models/endgame_white_queen.h5')
e_king_model = load_model('piece_move_to_models/endgame_white_king.h5')

m_pawn_model = load_model('piece_move_to_models/midgame_white_pawn.h5')
m_knight_model = load_model('piece_move_to_models/midgame_white_knight.h5')
m_bishop_model = load_model('piece_move_to_models/midgame_white_bishop.h5')
m_rook_model = load_model('piece_move_to_models/white_rook_model.h5')
m_queen_model = load_model('piece_move_to_models/white_queen_model.h5')
m_king_model = load_model('piece_move_to_models/midgame_white_king.h5')

move_to_models = {chess.PAWN: pawn_model,
                  chess.KNIGHT: knight_model,
                  chess.BISHOP: bishop_model,
                  chess.ROOK: rook_model,
                  chess.QUEEN: queen_model,
                  chess.KING: king_model}

#move_to models for the endgame_only
e_move_to_models = {chess.PAWN: e_pawn_model,
                  chess.KNIGHT: e_knight_model,
                  chess.BISHOP: e_bishop_model,
                  chess.ROOK: e_rook_model,
                  chess.QUEEN: e_queen_model,
                  chess.KING: e_king_model}

m_move_to_models = {chess.PAWN: m_pawn_model,
                  chess.KNIGHT: m_knight_model,
                  chess.BISHOP: m_bishop_model,
                  chess.ROOK: m_rook_model,
                  chess.QUEEN: m_queen_model,
                  chess.KING: m_king_model}

STOCKFISH = chess.engine.SimpleEngine.popen_uci(RAW_PATH)
LOG_FILE = r'Engine_Logs/log_' + str(datetime.datetime.now()) + '.txt'

# value of each piece, used in engine.check_obvious for takebacks
points_dic = {chess.PAWN: 2,
              chess.KNIGHT: 20,
              chess.BISHOP: 20.5,
              chess.ROOK: 35.5,
              chess.QUEEN: 55,
              chess.KING: 0}
# danger value of each piece to the king
danger_dic = {chess.PAWN: 15,
              chess.KNIGHT: 10,
              chess.BISHOP: 10.5,
              chess.ROOK: 35.5,
              chess.QUEEN: 55,
              chess.KING: 0}
# protective value of each piece to the king
prot_dic = {chess.PAWN: 40,
              chess.KNIGHT: 20,
              chess.BISHOP: 20.5,
              chess.ROOK: 25.5,
              chess.QUEEN: 55,
              chess.KING: 0}
# a different value dictionary for checking en_pris
p_dic = {chess.PAWN: 1,
              chess.KNIGHT: 3,
              chess.BISHOP: 3,
              chess.ROOK: 5,
              chess.QUEEN: 9,
              chess.KING: 100}

def is_open_file(board, file):
    ''' Given a position, returns either +2: file is semi open for white, -2:
        file is semi open for black, 0: file is closed or True: file is fully open. '''
    
    bb_dic = {0:chess.BB_FILE_A,
              1:chess.BB_FILE_B,
              2:chess.BB_FILE_C,
              3:chess.BB_FILE_D,
              4:chess.BB_FILE_E,
              5:chess.BB_FILE_F,
              6:chess.BB_FILE_G,
              7:chess.BB_FILE_H}
    
    white_pawn_true = False
    black_pawn_true = False
    
    for square in chess.SquareSet(bb_dic[file]):
        if board.piece_type_at(square) == chess.PAWN:
            if board.color_at(square) == chess.WHITE:
                white_pawn_true = True
            elif board.color_at(square) == chess.BLACK:
                black_pawn_true = True
    
    if white_pawn_true:
        if black_pawn_true:
            return 0
        else:
            return -2
    else:
        if black_pawn_true:
            return 2
        else:
            return True

def is_locked_file(board, file):
    ''' Given a position, check if a given file is pawn locked. '''
    bb_dic = {0:chess.BB_FILE_A,
              1:chess.BB_FILE_B,
              2:chess.BB_FILE_C,
              3:chess.BB_FILE_D,
              4:chess.BB_FILE_E,
              5:chess.BB_FILE_F,
              6:chess.BB_FILE_G,
              7:chess.BB_FILE_H}
    dummy_board = board.copy()
    dummy_board.turn = chess.WHITE
    legal_moves_from_sq_white = [move.from_square for move in dummy_board.legal_moves]
    dummy_board.turn = chess.BLACK
    legal_moves_from_sq_black = [move.from_square for move in dummy_board.legal_moves]
    
    pawn_true = False
    white_pawn_true = False
    black_pawn_true = False
    for square in chess.SquareSet(bb_dic[file]):
        if board.piece_type_at(square) == chess.PAWN:
            pawn_true = True
            if board.color_at(square) == chess.WHITE:
                if square in legal_moves_from_sq_white:
                    white_pawn_true = True
            elif board.color_at(square) == chess.BLACK:
                if square in legal_moves_from_sq_black:
                    black_pawn_true = True
    
    if white_pawn_true == False and black_pawn_true == False and pawn_true == True:
        return True
    else:
        return False

def king_danger(board, side, phase):
    ''' Returns a score for the king danger for a side. '''
    king_danger = 0
    
    king_sq = list(board.pieces(chess.KING, side))[0]
    area_range_file_from = max(0, chess.square_file(king_sq)-2)
    area_range_file_to = min(7, chess.square_file(king_sq)+2)
    area_range_rank_from = max(0, chess.square_rank(king_sq)-3)
    area_range_rank_to = min(7, chess.square_rank(king_sq)+3)
    
    for file_i in range(area_range_file_from, area_range_file_to+1):
        for rank_i in range(area_range_rank_from, area_range_rank_to+1):
            square = chess.square(file_i, rank_i)
            squares_from_k = chess.square_distance(square, king_sq)
            for attacker_sq in board.attackers(not side, square):
                king_danger += (4 - squares_from_k)*danger_dic[board.piece_type_at(attacker_sq)]
            
            for defender_sq in board.attackers(side, square):
                king_danger -= (4 - squares_from_k)/1.5*prot_dic[board.piece_type_at(defender_sq)]
    
    # deal with open files in opening and midgame
    if phase != 'endgame':
        for file_i in range(max(0, chess.square_file(king_sq)-1), min(7, chess.square_file(king_sq)+1) + 1):
            open_ = is_open_file(board, file_i)
            if open_ == True:
                king_danger += 500
            elif side == chess.WHITE and open_ == +2:
                king_danger += 400
            elif side == chess.BLACK and open_ == -2:
                king_danger += 400
    
    # does the opposition have her queen?
    king_danger += len(board.pieces(chess.QUEEN, not side))*300
    
    return king_danger

def is_weird_move(board, phase, move, obvious_move, king_dang):
    ''' Given a chess.Move object, and the phase of the game, return whether
        a move looks 'weird' or computer like. Mainly concerns rook and queen moves. '''
    # if move is by far the obvious move it is not weird
    if move.uci() == obvious_move:
        return False
    # if the move is a rook move on the base rank, punish rook moves which
    # 'squash' each other
    
    square_from = move.from_square
    square_to = move.to_square
    side = board.color_at(square_from)
    if side is None:
        # not a valid move
        raise Exception('Not a valid move from square when calculating weirdness.')
    if board.piece_type_at(square_from) == chess.ROOK:
        if chess.square_rank(square_from) == 0 and side == chess.WHITE:
            if square_to == chess.E1 and square_from != chess.F1 and board.piece_type_at(chess.F1) == chess.ROOK and board.color_at(chess.F1) == side:
                return True
            elif square_to == chess.B1 and square_from != chess.A1 and board.piece_type_at(chess.A1) == chess.ROOK and board.color_at(chess.A1) == side:
                return True
        elif chess.square_rank(square_from) == 7 and side == chess.BLACK:
            if square_to == chess.E8 and square_from != chess.F8 and board.piece_type_at(chess.F8) == chess.ROOK and board.color_at(chess.F8) == side:
                return True
            elif square_to == chess.B8 and square_from != chess.A8 and board.piece_type_at(chess.A8) == chess.ROOK and board.color_at(chess.A8) == side:
                return True
        
        # if the move is a rook move to the 2nd or third rank and it's not the obvious move
        open_ = is_open_file(board, chess.square_file(square_to))
        if chess.square_rank(square_to) in [1,2] and side == chess.WHITE and phase != 'endgame' and open_ != True:
            return True
        elif chess.square_rank(square_to) in [5,6] and side == chess.BLACK and phase != 'endgame' and open_ != True:
            return True
        
        # if the move is a rook move to a completely closed file
        if is_locked_file(board, chess.square_file(square_to)) == True:
            return True
        
    # if the move is a gueen move onto the back rank in the opening
    elif board.piece_type_at(square_from) == chess.QUEEN and phase != 'endgame':
        if chess.square_rank(square_to) == 0 and side == chess.WHITE:
            return True
        elif chess.square_rank(square_to) == 7 and side == chess.BLACK:
            return True
    
    # if the move is a king move to a random square when king safety is good
    elif board.piece_type_at(square_from) == chess.KING and king_dang < 400:
        return True
    
    return False

def is_quiet_move(board, move):
    ''' Given a chess.Move object, check if is a quiet move or not i.e. a human
        would play quickly without thinking. '''
    # check the move does not capture anything
    if board.color_at(move.to_square) == (not board.turn):
        return False
    # check it does not attack anything
    prev_fen = board.fen()
    dummy_board = board.copy()
    dummy_board.push(move)
    fen = dummy_board.fen()
    if new_attacked(prev_fen, fen, (not board.turn))[0]:
        return False
    
    # next check that the move itself does not place of it's own pieces in en pris
    if new_attacked(prev_fen, fen, board.turn)[0]:
        return False
    
    return True

def new_attacked(prev_fen, fen, color):
    ''' Determines whether with the last move the opposition has introduced a new threat, i.e.
        placed our piece in en pris when it wasn't previously. '''
    before_board = chess.Board(prev_fen)
    before_map = {}
    for sq in before_board.piece_map():
        if before_board.color_at(sq) == color:
            before_map[sq] = is_en_pris(before_board, sq)[0]
    
    new_threatened = {}
    after_board = chess.Board(fen)
    for sq in after_board.piece_map():
        if after_board.color_at(sq) == color:
            new_state = is_en_pris(after_board, sq)[0]
            try:
                if new_state == True and before_map[sq] == False:
                    new_threatened[p_dic[after_board.piece_type_at(sq)]] = sq
            except KeyError:
                # the previously en pris piece has moved away
                continue
    if len(new_threatened) > 0:
        # return the square with the highest piece threatened
        return True, new_threatened[sorted(new_threatened)[-1]]
    else:
        return False, None

def calculate_complexity(board):
    ''' Inspired by formula used by lucaschess, given a chess.Board() instance
        it calculates the complexity (usually between 0 and 100) of the position.
        The formulat used is:
            
            complexity = gmo * mov * pie * mat / (400 * own_mat)
        
        where gmo is the number of good moves
        move is the number of legal moves
        pie is the number of pieces (including kings and pawns)
        mat is the material count of both sides
        own_mat is sum of material belonging to side to move
        '''
    
    mov = board.legal_moves.count()
    
    pie = len(board.piece_map())
    
    mat = 0
    own_mat = 0
    for square, piece in board.piece_map().items():
        if piece.piece_type == chess.PAWN:
            mat += 1
            if piece.color == board.turn:
                own_mat += 1
        elif piece.piece_type == chess.KNIGHT:
            mat += 3.1
            if piece.color == board.turn:
                own_mat += 3.1
        elif piece.piece_type == chess.BISHOP:
            mat += 3.5
            if piece.color == board.turn:
                own_mat += 3.5
        elif piece.piece_type == chess.ROOK:
            mat += 5.5
            if piece.color == board.turn:
                own_mat += 5.5
        elif piece.piece_type == chess.QUEEN:
            mat += 9.9
            if piece.color == board.turn:
                own_mat += 9.9
        elif piece.piece_type == chess.KING:
            mat += 3
            if piece.color == board.turn:
                own_mat += 3
    
    # now need to work out the number of good moves, at most 100 centipawns
    # worst than best move
    analysis = STOCKFISH.analyse(board, chess.engine.Limit(depth=4), multipv=18)

    evals = []
    for info in analysis:
        # extracting information from analysis info returned by stockfish
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
                eval_score = (mate_in-100)*50
                
            elif str(info['score'])[1] == '+':
                # we are giving mate in this variation
                eval_score = (100-mate_in)*50
                
            else:
                raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
        evals.append(eval_score)
    evals.sort()
    best_eval = evals[-1]
    if best_eval > 350: # when winning by alot
        cutoff = best_eval / 2
    elif best_eval > 200:
        cutoff  = 150
    else:
        cutoff = 100
    good_evals = [x for x in evals if x +cutoff > best_eval]
    
    gmo = len(good_evals)
    
    # self.log += 'gmo, mov, pie, mat, own_mat, best_eval: ' + str(gmo) + ';'+ str(mov) + ';' + str(pie) + ';' + str(mat) + ';' + str(own_mat) + ';' + str(best_eval) + '\n'
    complexity = gmo * mov * pie * mat / (400 * own_mat ) 
    
    
    # added metric form lucas chess: Efficient mobility
    eff_mob = (gmo-1)*100/mov
    
    # self.log += 'Time taken to calculate complexity and eff_mob: ' + str(time_finish - time_start) + '\n'
    
    return complexity, eff_mob

def is_en_pris(cboard, square):
    ''' Takes in a chess.Board() instance and works out whether the attacked 
        piece is en pris. Also gives a score on how much the piece is en pris by,
        namely a higher score means a greater material loss/gain. '''
    board = cboard.copy()
    
    square_color = board.color_at(square)
    if square_color is None:
        # mentioned square is empty
        return False, 0
    
    sum_ = p_dic[board.piece_type_at(square)]
    next_ = sum_
    while True:
        try:
            temp_dic = {p_dic[board.piece_type_at(sq)] : sq for sq in board.attackers(not square_color, square)}
            next_ = min(temp_dic)
        except ValueError: # empty sequence
            sum_ -= next_
            if sum_ > 0:
                return True, sum_
            else:
                return False, sum_
        board.push(chess.Move(temp_dic[next_], square))
        sum_ -= next_
        if sum_ > 0:
            return True, sum_ # the piece is en pris
        try:
            temp_dic = {p_dic[board.piece_type_at(sq)] : sq for sq in board.attackers(square_color, square)}
            next_ = min(temp_dic)
        except ValueError: # empty sequence
            sum_ += next_
            if sum_ > 0:
                return True, sum_
            else:
                return False, sum_
        board.push(chess.Move(temp_dic[next_], square))
        sum_ += next_
        if sum_ < 0:
            return False, sum_ # the piece is not en pris

def phase_of_game(board):
    ''' Takes in a chess.Board() instance and returns opening, midgame, endgame
        depending on what phase of the game the board position is. '''
    # count minor and major pieces on the board
    min_maj_pieces = 0
    for square in chess.SQUARES:
        if board.piece_type_at(square) is not None: # square is occupied
            if board.piece_type_at(square) != chess.PAWN and board.piece_type_at(square) != chess.KING:
                min_maj_pieces += 1
    if min_maj_pieces < 6:
        return 'endgame'
    elif min_maj_pieces < 11:
        return 'midgame'
    else:
        # see if back rank is sparse
        white_br = 0
        black_br = 0
        for square in chess.SquareSet(chess.BB_RANK_1):
            if board.color_at(square) == chess.WHITE:
                white_br += 1
        if white_br < 5:
            return 'midgame'
        
        for square in chess.SquareSet(chess.BB_RANK_8):
            if board.color_at(square) == chess.BLACK:
                black_br += 1
        if black_br < 5:
            return 'midgame'
        
        # otherwise, it is the opening
        return 'opening'
            
    

def convert_square_to_uci(from_square, to_square, mirror=False):
    ''' Returns a uci string from two indexes: move_from, move_to. 
        The square notation is in terms of chess.SQUARES i.e. a1=0 etc. '''
    
    if mirror:
        return chess.square_name(chess.square_mirror(from_square)) + chess.square_name(chess.square_mirror(to_square))
    else:
        return chess.square_name(from_square) + chess.square_name(to_square)

def convert_board_one_hot(board):
    ''' Convert's a chess.Board() instance to be one-hot encoded, ready to
        pass into the models. '''
    board_str = str(board).replace('\n', ' ').split(' ')
    
    input_board = []
    for input_square in board_str:
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
            
    return np.reshape(np.array(input_board), (1, 8, 8, 12)).astype(float)

class AtomicSamurai:
    ''' This is the name of the engine which given a position, would only
        use the piece move_to models to decide how it moves 'humanly'. It
        iterates over all models, and depending on the piece, it would pick
        a fixed amount of squares to consider, and find the legal moves that
        correspond to those squares. 
        
        Note that all moves are to be decided from white point of view. If it
        is playing black, the board would need to be mirrored by the board.mirror()
        call first before encoding and passing through the models.
        
        Note this takes into account the number of each piece type also as well
        as how many squares the respective piece can on average reach in a given
        position.
        '''
        
    def __init__(self, log=True, shadow=False, m_piece_models_dic=m_move_to_models, e_piece_models_dic=e_move_to_models, piece_models_dic=move_to_models, playing_side=chess.WHITE, starting_position_fen=chess.STARTING_FEN):
        self.piece_models = piece_models_dic # dictionary of all piece models
        self.e_piece_models = e_piece_models_dic
        self.m_piece_models = m_piece_models_dic
        self.selector = midgame_selector # used for narrowing piece choices when blunder prone
        self.board = chess.Board(starting_position_fen)
        self.phase = phase_of_game(self.board) # phase of game
        self.side = playing_side
        self.stockfish = STOCKFISH # stockfish engine
        self.name = 'AtomicSamurai'
        self.log = ''
        if self.side:
            self.log += 'Playing side: WHITE \n'
        else:
            self.log += 'Playing side: BLACK \n'
        self.blunder_prone = False # when true, the engine is prone to make a human like error
        self.resigned = False # indicates whether engine has resigned
        self.time_scramble_mode = False # when this is on, engine will make moves as fast as possible
        self.resign_threshold = random.randint(1,10) + 30 # number of moves the engine must play before resigning
        self.bullet_threshold = random.randint(1,5) + 10 # threshold before engine goes into bullet mode
        self.premove_mode = False # when engine is in premove mode, a certain percentage of moves it makes are premoves
        self.big_material_take = False # if oppenent suddenly hangs a piece (in time scrambles), don't immediately take back (let's lichess clinet know)
        self.mate_in_one = False
        self.shadow = shadow # alters thinking times to be much more stable
        self.log_true = log # whether or not to output a log file
        self.move_times = [] # store of the last few move times to increase variation in move_times
        self.prev_fen = None
        self.prev_move = None
        self.prev_own_move = None # the move that the engine played last, used for human-like time scrambles
        self.obvious_move = None
        self.own_time = 60
        self.opp_time = 60
        self.long_think = False
        self.quick_move = False
        self.win_percentage = 50
        self.king_dang = 0
        self.fens = [] # for tracking threefold repetition
    
    def update_board(self, board):
        ''' When the engine recieves information about the opponent's move
            it would recieve it via this function in the form of a
            chess.Board() instance. '''
        self.board = board.copy()
    
    def get_board(self):
        ''' Returns it's current board state. '''
        return self.board
    
    def assert_my_turn(self):
        ''' Returns whether it is the engine's turn to move. '''
        return self.board.turn == self.side
    
    def check_repetition(self, potential_board):
        ''' Given a potenital board position, check that it hasn't be repeated 3 times before. '''
        dummy_list = [chess.Board(fen).board_fen() for fen in self.fens]
        
        if len(dummy_list) < 5:
            return False
        if dummy_list.count(potential_board.board_fen()) > 1:
            return True
        else:
            return False
    
    def piece_selector_filter(self, move_dic):
        ''' Uses the piece selector model to predict which pieces to move. Note
            move_dic is a dictionary of value weighted probability and key move_uci
            and that we return a filtered list of 
            ucis. Used only when the engine is blunder prone, and return all moves
            that originate from square with their respective probabilities, and
            hence work out the total probability of each move happening. We adjust
            for number of piece types left of the board.
            '''
        self.log += 'Filtering using selector model... \n'
        # first convert move_dic values to chess.Move objects to find square of origins
        # store in dictionary format: key - uci,; value - from_square (int)
        from_squares = {}
        for move in move_dic.keys():
            move_obj = chess.Move.from_uci(move)
            from_squares[move] = move_obj.from_square
        self.log += 'Recieved move_list and respective from squares: ' + str(from_squares) + '\n'
        # next get prediction from piece selector model
        # remember we must flip the board if we are playing black
        # first check that it is the machine's turn to move
        if not self.assert_my_turn():
            raise Exception("ERROR: Atomic Samurai made to play move when it's not its turn.")
        
        if self.side == chess.BLACK:
            dummy_board = self.board.mirror()
        else:
            dummy_board = self.board.copy()
        
        # parse dummy board for encoding
        one_hot_board = convert_board_one_hot(dummy_board)
        square_predictions = self.selector.predict(one_hot_board)
        
        # count the number of pieces per piece_type:
        pieces_concerned = [piece.piece_type for piece in self.board.piece_map().values() if piece.color == self.side]
        multiplying_factors = {chess.PAWN: pieces_concerned.count(chess.PAWN),
                               chess.KNIGHT: pieces_concerned.count(chess.KNIGHT),
                               chess.BISHOP: pieces_concerned.count(chess.BISHOP),
                               chess.ROOK: pieces_concerned.count(chess.ROOK),
                               chess.QUEEN: pieces_concerned.count(chess.QUEEN),
                               chess.KING: pieces_concerned.count(chess.KING)}
        
        move_prob ={}
        
        for move, from_sq in from_squares.items():
            # need the probability at from square
            if self.side == chess.WHITE:
                from_sq_prob = square_predictions[0][chess.square_mirror(from_sq)]
            else:
                from_sq_prob = square_predictions[0][from_sq]
            
            # account for the fact there may me more of one piece than another
            from_sq_prob = from_sq_prob*multiplying_factors[self.board.piece_type_at(from_sq)]
            to_square_prob = move_dic[move]
            # if current piece is being attacked, give it extra weight relative to the
            # attacked piece's value
            
            # now filter for probability weights
            from_sq_prob, to_square_prob = self.probability_weight(from_sq, chess.Move.from_uci(move).to_square, from_sq_prob, to_square_prob)
            
            total_prob = from_sq_prob * to_square_prob
            move_prob[move] = [total_prob, from_sq_prob, to_square_prob]
        
        # calculate eff mob to decide how many moves to search
        self.log += 'Calculating complexity of the position... \n'
        time_s = time.time()
        complexity, eff_mob = calculate_complexity(self.board) # calculates the complexity and eff_mob of the position
        time_f = time.time()
        self.log += 'Complexity calculated: ' + str(complexity) + '\n'
        self.log += 'Efficient mobility calculated: ' + str(eff_mob) + '\n'
        self.log += 'Time taken to calculate complexity and eff mob: ' + str(time_f-time_s) + '\n'
        
        # eff mob decides whether or not to blunder, complexity decides how much time
        # to spend on the move
        # when eff_mob is between 8 and 25 percent is when we are blunder prone
        
        
        move_prob = {k: v for k, v in sorted(move_prob.items(), key=lambda item: item[1][0], reverse=True)}
        # take first 4 moves as the root moves
        prob_ = {self.board.san(chess.Move.from_uci(key)) : prob for key, prob in move_prob.items()}
        self.log += 'Move Probabilities that the engine sees: \n'
        for key, value in prob_.items():
            self.log += str(key) + ': ' + str(value) + '\n'
        if eff_mob < 10:
            # either the best move is obvious (e.g. a takeback, mate in one) or
            # there is a tactic involved. Decrease search width to mimic human
            # behaviour in tactics under pressure
            # if self.mate_in_one == False:
            if eff_mob > 5 and self.own_time > self.opp_time and self.phase == 'midgame' and self.own_time > 15:
                self.long_think = True
                self.log += 'Long think provoked! \n'
            else:
                self.long_think = False
            no_moves = SEARCH_WIDTH
        else:
            if self.phase != 'endgame' and self.king_dang < 500:
                no_moves = 6
            else:
                no_moves = SEARCH_WIDTH
            self.long_think = False
        
        if self.shadow:
            no_moves = no_moves + 4 # consider more moves when in advisor mode
        else:
            no_moves = no_moves
        
        self.log += 'Number of moves considered from difficulty levels: ' + str(no_moves) + '\n'
        
        move_list = list(move_prob.keys())[:no_moves]
        return move_list
    
    def search_human_moves(self, starting_time):
        ''' Function which returns list of human moves in uci (not necessarily legal)
            along with their probabilities using models by updating self.board. '''
        human_ucis = {}
        
        # first check that it is the machine's turn to move
        if not self.assert_my_turn():
            print(self.log)
            raise Exception("ERROR: Atomic Samurai made to play move when it's not its turn.")
        
        # if engine playing from black side, then we need to flip the board
        if self.side == chess.BLACK:
            dummy_board = self.board.mirror()
        else:
            dummy_board = self.board.copy()
        
        # parse dummy board for encoding
        one_hot_board = convert_board_one_hot(dummy_board)
        
        # now we iterate through all models
        piece_caps = self.calculate_caps(starting_time)
        
        if self.phase == 'midgame':
            # use a different set of move to models
            models = self.m_piece_models
            self.log += 'Used midgame move_to models! \n'
        elif self.phase == 'endgame':
            # use a different set of move to models
            models = self.e_piece_models
            self.log += 'Used endgame move_to models! \n'
        else:
            models = self.piece_models
        
        for piece_type, model in models.items():
            # first find square int positions of all of the certain piece
            # type on the board
            from_squares = []
            for i in range(64):                
                if dummy_board.piece_type_at(i) == piece_type and dummy_board.color_at(i) == chess.WHITE:
                    from_squares.append(i)
            
            piece_predictions = model.predict(one_hot_board)
            sorted_pred = sorted(piece_predictions[0])                
            for i in range(piece_caps[piece_type]):
                # note here that a1 = 0, h8 = 63, so need to do some conversion
                probability = sorted_pred[-i-1]
                index = list(piece_predictions[0]).index(probability)
                square_int = chess.square_mirror(index) # this square int is relative to dummy board
                
                # now construct ucis
                
                for square in from_squares:
                    mirror_needed = self.side == chess.BLACK
                    # we need to mirror back the moves
                    uci = convert_square_to_uci(square, square_int, mirror=mirror_needed)
                    
                    # if it is a pawn move to the back rank, we need to add an extra 'q' at the end
                    if piece_type == chess.PAWN and chess.square_rank(square_int) == 7:
                        uci += 'q'
                    human_ucis[uci] = probability
        return human_ucis
    
    def probability_weight(self, square_from, square_to, sq_fr_prob, sq_to_prob):
        ''' Takes probabilities given by models and slightly alters them to favour
            more the human characteristics of playing. '''
        # if the to_square is in fact a capture of the opposition piece,
        # we give it a bonus proability as captures are more appealing
        # to humans
        enpris_fr = is_en_pris(self.board, square_from)
        
        if self.board.color_at(square_to) == (not self.side):
            
            enpris_to = is_en_pris(self.board, square_to)
            # also if the piece is enpris
            if enpris_to[0]:
                # pawns are more valuable in the endgame
                if self.board.piece_type_at(square_to) == chess.PAWN and self.phase == 'endgame':
                    factor = 10
                else:
                    factor = points_dic[self.board.piece_type_at(square_to)]
                sq_to_prob = sq_to_prob * factor * 2.5
            # punish moves which capture non-enpris pieces specifically with a quite negative score (exchanges allowed)
            elif enpris_to[0] == False and enpris_to[1] < -0.5:
                sq_to_prob = sq_to_prob / abs(enpris_to[1] - 1)
            # punish moves that exchange pieces when we're losing, unless it's the obvious move
            elif enpris_to[0] == False:
                if self.win_percentage < -95: # we are losing
                    sq_to_prob = sq_to_prob / 15
        elif self.board.piece_type_at(square_from) == chess.PAWN:
            # Pawn moves tend to advance the game state, so as to prevent seemingly
            # unnecessary manoeuvring around, we promote these moves
            sq_fr_prob = sq_fr_prob * 2
            
            # If we are promoting, give extra consideration
            if self.side == chess.WHITE:
                if chess.square_rank(square_to) == 7:
                    sq_to_prob = sq_to_prob * 20
            else:
                if chess.square_rank(square_to) == 0:
                    sq_to_prob = sq_to_prob * 20
            
        # If the move from piece is en pris, also consider it more
        if enpris_fr[0]:
            sq_fr_prob = sq_fr_prob * points_dic[self.board.piece_type_at(square_from)]
            
        # If the move attacks something with higher value, increase its tendency
        value_fr = p_dic[self.board.piece_type_at(square_from)]
        dummy_board = self.board.copy()
        dummy_board.push(chess.Move(square_from, square_to))
        if is_en_pris(dummy_board, square_to)[0] == False:
            for square in dummy_board.attacks(square_to):
                if dummy_board.color_at(square) == (not self.side): # opposition
                    if is_en_pris(dummy_board, square)[0] :
                        # pawns more valuable in the endgame
                        if dummy_board.piece_type_at(square) == chess.PAWN and self.phase == 'endgame':
                            factor = 5
                        else:
                            factor = p_dic[dummy_board.piece_type_at(square)]
                        sq_to_prob = sq_to_prob * factor
        
        # If move protects a piece which became en pris by opponent's previous move
        # Add bonus
        considered_move = chess.Move(square_from, square_to)
        dummy_board = self.board.copy()
        dummy_board.push(considered_move)
        attacked = new_attacked(self.prev_fen, self.board.fen(), self.side)
        if attacked[0] == True:
            square = attacked[1]                    
            if is_en_pris(dummy_board, square)[0] == False:
                # then the move successfully protects the en pris piece
                sq_to_prob = sq_to_prob * 5
        elif self.board.piece_type_at(square_to) != (not self.side) and self.phase != 'endgame' and self.prev_own_move is not None:
            # We punish 'awkward shuffling around moves' sometimes happens with rooks on the back rank
            # Refer to the previous move played
            pre_move_obj = chess.Move.from_uci(self.prev_own_move)
            if pre_move_obj.to_square == square_from:
                # we're moving the same piece again
                # check that the to square isn't a square we could have moved to last time
                dummy_board = self.board.copy()
                dummy_board.remove_piece_at(square_from)
                dummy_board.set_piece_at(pre_move_obj.from_square, chess.Piece(self.board.piece_type_at(square_from), self.side))
                if chess.Move(pre_move_obj.from_square, square_to) in dummy_board.legal_moves or pre_move_obj.from_square == square_to:
                    # punish the move if it's not an obvious move
                    if considered_move.uci() != self.obvious_move:
                        sq_to_prob = sq_to_prob / 15
        
        # We punish moves which makes new pieces become en-pris
        # e.g. move a piece that is pinned or move the piece to an attacked square
        pinned_atk = new_attacked(self.board.fen(), dummy_board.fen(), self.side)
        if pinned_atk[0] == True:
            sq_fr_prob = sq_fr_prob / points_dic[self.board.piece_type_at(pinned_atk[1])]
        
        # if the move is a 'weird' computer type move, decrease its probability
        if is_weird_move(self.board, self.phase, considered_move, self.obvious_move, self.king_dang) == True:
            # print('weird move: ', self.board.san(considered_move))
            sq_to_prob = sq_to_prob / 20
        return sq_fr_prob, sq_to_prob
        
    
    def filter_legal_moves(self, moves_dic):
        ''' Takes in a list of possible ucis, and returns a list of those which
            are actually legal in the given position. '''
        all_legal_moves = [move.uci() for move in self.board.legal_moves]
        legal_moves = [move for move in moves_dic.keys() if move in all_legal_moves]
        # if engine is blunder prone, we must add a further filtration process
        if self.blunder_prone:
            legal_dic = {key: value for key, value in moves_dic.items() if key in legal_moves}
            legal_moves = self.piece_selector_filter(legal_dic)
        
        return legal_moves

    def evaluate_moves(self, difficulty, standard_dev, moves_list=[], time_limit=1):
        ''' The main function for dealing with stockfish assistance. given
            an input list of moves in uci format, and difficulty, function
            outputs a move in uci format as the chosen move. difficulty is 
            a continuous variable from 0-10. If moves_list is not set, then the 
            moves considered are all legal moves (simply asking engine to make
            move with no restrictions). '''
        
        moves_dic = self.get_engine_lines(root_moves=moves_list, depth=10)
        
        ''' Now we use the most important part of any engine. We must somehow
            incorporate difficulty variable into filtering out and selecting a 
            move given their evaluations. 
            
            For this we use an normal distribution
            model based on centipawn loss. We take the best move to have 0
            centipawn loss, and depending on the difficulty, we set the mean
            of the distribution accordingly: greater the difficulty, the closer
            to zero the mean is. Later when we implement time restrictions, this
            would contribute to variance.
            
            After generating this centipawn loss, we simply choose the move which
            has evaluation which best matches the decribed loss. '''
        self.log += 'Moves evaluations: ' + str(moves_dic) + '\n'    
        
        mean = -5 * (10 - difficulty)
        # standard_dev = 8 # fixed for now, will adjust when time restrictions in place
        centipawn_loss = np.random.normal(mean, standard_dev, 1)[0]
        self.log += 'Calculation time allowed: ' + str(time_limit) + '\n'
        self.log += 'Decided centipawn loss from mean {} and stdev {}: '.format(mean, standard_dev) + str(centipawn_loss) + '\n'
        
        evaluations = sorted(moves_dic)
        # now find eval closest to centipawn_loss
        target_eval = evaluations[-1] + centipawn_loss
        self.log += 'Target_evaluation: {}'.format(target_eval) + '\n'
        closest = min(evaluations, key=lambda x: abs(target_eval-x))
        chosen_move = moves_dic[closest]
        return chosen_move

    def get_engine_lines(self, time_limit=1, depth=None, root_moves=[], multipv=3, board=None):
        ''' Communicator with the engine which given restrictions, returns
            a dictionary with moves in uci form and their respective evals. 
            root_moves must be a list of uci formated moves. '''
        # if no board is specified, we assume it is self.board
        if board is None:
            board = self.board
        
        # if depth is specified, ignore time restriction
        if depth is not None:
            restriction = chess.engine.Limit(depth=depth)
        else:
            restriction = chess.engine.Limit(time=time_limit)
        if len(root_moves) == 0:
            # returns top 3 moves in any given position
            analysis = self.stockfish.analyse(board, restriction, multipv=multipv)
        else:
            # returns top 3> moves in the subset of moves list
            chess_moves = [chess.Move.from_uci(move) for move in root_moves]
            analysis = self.stockfish.analyse(board, restriction, root_moves=chess_moves, multipv=min(len(root_moves), multipv))
        
        # Note the analysis object gives RELATIVE evaluation, i.e. sign dependent
        # on whose move it is. A positive evaluation score means the position
        # favours the side who has the move.
        
        # self.log += 'Analysis Object recieved:  ' + str(analysis) + '\n'  
        
        moves_dic = {} # stores key: evaluation, value is the move in uci form
        for info in analysis:
            # extracting information from analysis info returned by stockfish
            move_uci = str(info['pv'][0])
            evaluation_str = str(info['score'])
            self.log += 'Evaluation str: ' + evaluation_str + '\n'
            
            # see if the evaluation is some sort of mating eval for example #-2
            # would mean would receive mate from opposition in 2 plies
            try:
                eval_score = int(evaluation_str)
            except ValueError:
                # mating sequence
                # Note a eval string of #-0 means the engine has not calculated enough for the line
                # to have a eval score
                mate_in = int(str(info['score'])[2:])
                if str(info['score'])[1] == '-':
                    # we are recieving mate in the variation
                    # give a very negative evaluation, with more negative the more
                    # immediate the mate
                    eval_score = (mate_in-100)*100
                    
                elif str(info['score'])[1] == '+':
                    # we are giving mate in this variation
                    eval_score = (100-mate_in)*100
                    
                else:
                    raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
            moves_dic[eval_score] = move_uci
        
        return moves_dic

    def calculate_win_percentage(self):
        ''' Given a position, calculates the win percentage of the better side,
            inspired by formula from lucaschess:
                
                win_percentage = abs( 100 * tanh(eval_ /(2 * mat)) )
                
            where eval_ is the evaluation, mat is the remaining material. '''
        self.log += 'Calculating winning percentage... \n'
        time_start = time.time()
        mat = 0
        for square, piece in self.board.piece_map().items():
            if piece.piece_type == chess.PAWN:
                mat += 1
            elif piece.piece_type == chess.KNIGHT:
                mat += 3.1
            elif piece.piece_type == chess.BISHOP:
                mat += 3.5
            elif piece.piece_type == chess.ROOK:
                mat += 5.5
            elif piece.piece_type == chess.QUEEN:
                mat += 9.9
            elif piece.piece_type == chess.KING:
                mat += 3
        
        info = self.stockfish.analyse(self.board, chess.engine.Limit(depth=8))
        evaluation_str = str(info["score"])
        # see if the evaluation is some sort of mating eval for example #-2
        # would mean would receive mate from opposition in 2 plies
        try:
            eval_ = int(evaluation_str)
        except ValueError:
            # mating sequence received
            mate_in = int(str(info['score'])[2:])
            if str(info['score'])[1] == '-':
                # we are recieving mate in the variation
                # give a very negative evaluation, with more negative the more
                # immediate the mate
                eval_ = (mate_in-100)*100
                
            elif str(info['score'])[1] == '+':
                # we are giving mate in this variation
                eval_ = (100-mate_in)*100
                
            else:
                raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
        
        win_percentage = 100 * np.tanh(eval_ / (2 * mat))
        self.log += 'Win percentage: ' + str(round(win_percentage)) + '\n'
        
        time_finish = time.time()
        
        self.log += 'Time taken to calculate win_percentage: ' + str(time_finish - time_start) + '\n'
        return win_percentage

    def decide_resign(self, own_time, opp_time, starting_time):
        ''' The decision making function which decides whether to resign. '''
        # does not resign in the first 20 moves
        return False

    def check_obvious(self, own_time, starting_time, prev_move, prev_fen):
        ''' The first filtering process of deciding what move to make. Will get
            engine to search for minimal depth and see if there is a standout
            move. If there is, AtomicSamurai will play it regardless. 
            
            An obvious move is one which has by far the best evaluation from
            minimal depth search, and also the piece is either en pris or is
            a take-back during an exchange. '''
        if starting_time < 61:
            depth = 4
            if own_time < self.bullet_threshold:
                depth = random.randint(2, 5)
                lines = 5
            else:
                lines = 4
        else:
            depth = 6
            lines = 4
        moves_dic = self.get_engine_lines(depth=depth, multipv=lines)
        # if top obvious move is more than 200 centipawns better than second move
        
        # for some reason the analysis object doesn't always return desired
        # number of lines, in which case we just pass
        if len(moves_dic) < 2:
            return None
        
        sorted_evals = sorted(moves_dic)
    
        self.log += 'Obvious Moves check: ' + str(moves_dic) + '\n'
        
        # Managing flagging
        if own_time < self.bullet_threshold or self.opp_time < 10:
            # if we are down serious time, play randomised moves to avoid flagging
            self.log += 'In flagging mode... \n'
            self.move_times.append(0.01)
            if len(self.move_times) > 5:
                del self.move_times[0]
            
            # work out non-blunder moves
            non_blunder = [eval_ for eval_ in sorted_evals if eval_ > sorted_evals[-1] - 200]
            
            # to mimic human mouse tendencies in time scrambles, if one of the
            # candidate moves involves moving the piece the engine moved last
            # play it
            self.log += 'Last own move played was ' + str(self.prev_own_move) + '\n'
            
            self.log += 'Moves considering: ' + str(moves_dic) + '\n'
            self.log += 'Non blunder evals are ' + str(non_blunder) + '\n'
            
            if self.prev_own_move is None:
                last_move_to_sq = 0
            else:
                last_move_to_sq = chess.Move.from_uci(self.prev_own_move).to_square
            move_distances = {chess.square_distance(last_move_to_sq, chess.Move.from_uci(moves_dic[eval_]).from_square)*3 + chess.square_distance(chess.Move.from_uci(moves_dic[eval_]).to_square, chess.Move.from_uci(moves_dic[eval_]).from_square): eval_ for eval_ in non_blunder}
            self.log += 'Move distances dictionary: ' + str(move_distances) + '\n'
            
            if self.win_percentage > -100 or self.own_time - self.opp_time > 5:
                selected = None
                for distance in sorted(move_distances):
                    dummy_board = self.board.copy()
                    considering_move = chess.Move.from_uci(moves_dic[move_distances[distance]])
                    dummy_board.push(considering_move)
                    self.log += 'Checking ' + self.board.san(considering_move) + ' for repetition as we are currently winning/ up on time. \n'
                    check = self.check_repetition(dummy_board)
                    if check == False:
                        self.log += 'No repetition found. \n'
                        selected = move_distances[distance]
                        break
                    else:
                        self.log += 'Repetition found! \n'
                
                if selected is None:               
                    selected = move_distances[sorted(move_distances)[0]]
            else:
                selected = move_distances[sorted(move_distances)[0]]
            
            self.log += 'Selected eval: ' + str(selected) + '\n'
            top_move_obj = chess.Move.from_uci(moves_dic[selected])
            
            # if the opponent has played a move which attacks one of our pieces
            # e.g. a check, with some probability, add a delay if our chosen
            # move evades the attacked
            atk = new_attacked(prev_fen, self.board.fen(), self.side)
            if atk[0] == True:
                square = atk[1]
                dummy_board = self.board.copy()
                dummy_board.push(top_move_obj)
                if is_en_pris(dummy_board, square)[0] == False:
                    # our move evades the attack
                    if random.random() < 0.3:
                        time.sleep((random.random()+1)/8)
                        self.log += 'Our move evades opposition attack! Pause slightly. \n'            
                    else:
                        self.log += 'Our move evades opposition attack! No pause. \n'            
        else:            
            self.log += 'Not in flagging mode. \n'
            # work out non-blunder moves
            non_blunder = [eval_ for eval_ in sorted_evals if eval_ > sorted_evals[-1] - 80]
            self.log += 'Moves considering: ' + str(moves_dic) + '\n'
            self.log += 'Non blunder evals are ' + str(non_blunder) + '\n'
            selected = random.choice(non_blunder)
            top_move_obj = chess.Move.from_uci(moves_dic[selected])
        
        
        if selected > 9800:
            self.log += 'Mate in one found! \n'
            self.mate_in_one = True
        else:
            self.mate_in_one = False
        
        move_from_sq = top_move_obj.from_square
        move_to_sq = top_move_obj.to_square
        
        if prev_move != False and prev_fen != False:
            opp_prev_move = chess.Move.from_uci(prev_move)
            # check if top move is a take_back
            temp_board = chess.Board(prev_fen)
            if self.board.piece_at(move_to_sq) is not None and opp_prev_move.to_square == move_to_sq and temp_board.piece_at(move_to_sq) is not None:
                point_diff = points_dic[temp_board.piece_type_at(move_to_sq)] - points_dic[self.board.piece_type_at(move_to_sq)]
                if abs(point_diff) < 1.6:
                    take_back = True
                    self.big_material_take = False
                    self.log += 'Top move is a take-back. \n'
                elif self.prev_own_move is not None:
                    if chess.Move.from_uci(self.prev_own_move).to_square == move_to_sq and random.random() < 0.8:
                        take_back = True
                        self.big_material_take = True
                        self.log += 'Top move is a take-back, based on previous move. \n'                        
                    else:
                        take_back = False
                        self.big_material_take = True
                        self.log += 'Top move is not a take-back, as it involves taking big material. \n'
                else:   
                    self.big_material_take = True
                    take_back = False
                    self.log += 'Top move is not a take-back, as it involves taking big material. \n'
            elif self.board.piece_at(move_to_sq) is not None and opp_prev_move.to_square == move_to_sq:
                take_back = False
                self.log += 'Top move is not a take-back as the opponent didnt take anything. Possible hung piece \n'
                if is_en_pris(self.board, move_to_sq) and points_dic[self.board.piece_type_at(move_to_sq)] > 2.9:
                    self.big_material_take = True
                else:
                    self.big_material_take = False
            else:
                self.big_material_take = False
                take_back = False
                self.log += 'Top move is not a take-back. Nothing interesting here. \n'
        else:
            self.log += 'Top move is not a take-back. No previous data provided. \n'
            take_back = False
            self.big_material_take = False
        
        self.log += 'big_material_take: ' + str(self.big_material_take) + '\n'
        
        # if our move takes an enpris piece that only became enpris from last opponent move
        # and it is not a take back
        # pause, cannot take immediately
        atk = new_attacked(prev_fen, self.board.fen(), not self.side)
        if atk[0] == True:
            square = atk[1]
            if top_move_obj.to_square == square and take_back == False and self.big_material_take == False:
                time.sleep((random.random()+1)/6)
                self.log += 'Opposition just hung material! Pause slightly \n' 
        
        if own_time < self.bullet_threshold or self.opp_time < 7 + random.randint(1,5):
            # return move early
            return top_move_obj.uci()
        
        # if currently in a time scramble, and take back is true, then we automatically take it back
        if self.time_scramble_mode == True and take_back == True:
            self.log += 'Obvious move found as currently in time scramble! \n'
            self.move_times.append(0.01)
            if len(self.move_times) > 5:
                del self.move_times[0]
            return top_move_obj.uci()
        elif self.premove_mode == True:
            self.log += 'Obvious move found as currently in premove_mode! \n'
            return top_move_obj.uci()
        
        # check if move from piece is under attack
        # if self.side == chess.WHITE:
        #     opp_side = chess.BLACK
        # elif self.side == chess.BLACK:
        #     opp_side = chess.WHITE
        
        # if len(self.board.attackers(opp_side, move_from_sq)) > 0:
        #     # square is being attacked
        #     if len(self.board.attackers(self.side, move_from_sq)):
        #         # square not protected
        #         attacked = True
        #         self.log += 'Top move piece is under attack. \n'
        #     else:
        #         attacked = False
        #         self.log += 'Top move piece is not under attack. \n'
        # else:
        #     attacked = False
        #     self.log += 'Top move piece is not under attack. \n'
        
        # attacked_and_take = attacked and take_back
        
        # if the move is really an obvious move, store it, otherwise set obvious move as none
        if sorted_evals[-1] > sorted_evals[-2] + 200:
            self.log += 'Top move from obvious move check is by far the best move, storing for later reference. \n'
            self.obvious_move = moves_dic[sorted_evals[-1]]
        else:
            self.obvious_move = None
        
        
        if sorted_evals[-1] > sorted_evals[-2] + 200 and take_back:
            self.log += 'Obvious move found! \n'
            self.move_times.append(0.01)
            if len(self.move_times) > 5:
                del self.move_times[0]
            return top_move_obj.uci()
        elif starting_time < 61 and random.random() < 0.4 and self.big_material_take == False:
            # to increase move time variation during bullet games
            # play some quick moves
            # Only do this if certain conditions are satisfied
            if new_attacked(prev_fen, self.board.fen(), self.side)[0] == False:
                self.log += 'The opposition has not attacked one of our pieces with their last move. \n'
                if is_quiet_move(self.board, top_move_obj) and is_weird_move(self.board, self.phase, top_move_obj, self.obvious_move, self.king_dang) == False:
                    self.log += 'Stockfish move is a quiet, human-like retaliation move. \n'
                    self.log += 'No obvious move, but to increase move time variation we play it \n'
                    self.move_times.append(0.01)
                    if len(self.move_times) > 5:
                        del self.move_times[0]
                    return top_move_obj.uci()
                else:
                    self.log += 'Stockfish move was not a quiet/human like move: ' + top_move_obj.uci() + '\n'
                    return None
            else:
                self.log += 'Opponent attacked one of our pieces, no obvious move. \n'
                return None
        else:
            self.log += 'No obvious move found. \n'
            return None
    
    def get_premove(self, fen):
        ''' Given a fen where it is the engine's turn to move, check for premoves. 
            Returns a move in uci format if the engine finds one, else returns
            None. takeback parameter can be specified to be false if we are in
            the situation where engine is super low on time (e.g. last 10 seconds). '''
        
        # first get all captures of the position that the opponent can do involving
        # similar material
        temp_board = chess.Board(fen)
        # first assert it's actually the opponents move
        if temp_board.turn == self.side:
            return None
        
        # PREMOVES FOR TAKEBAKES ONLY
        if self.premove_mode == False:
            candidate_opp_moves = []
            
            for square, piece in temp_board.piece_map().items():
                if piece.color == self.side:
                    opp_attackers = temp_board.attackers(not self.side, square)
                    if len(opp_attackers) > 0 and len(temp_board.attackers(self.side, square)) > 0:
                        opp_attackers = [[points_dic[temp_board.piece_type_at(sq)], sq] for sq in opp_attackers if temp_board.piece_type_at(sq) != 6]
                        opp_attackers.sort()
                        if len(opp_attackers) > 0:
                            if abs(opp_attackers[0][0] - points_dic[piece.piece_type]) < 0.7:
                                move = chess.Move(opp_attackers[0][1], square)
                                if move in temp_board.legal_moves:
                                    candidate_opp_moves.append(move)
            
            if len(candidate_opp_moves) == 0:
                return None
            else:
                # out of all the candidate opp moves, we consider the one which
                # involves the piece of least value
                opp_move = candidate_opp_moves[0]
                temp_board.push(opp_move)
                moves_dic = self.get_engine_lines(depth=3, multipv=1, board=temp_board)
                if len(moves_dic) == 0:
                    return None
                move = chess.Move.from_uci(list(moves_dic.values())[0])
                if move.to_square == opp_move.to_square:
                    self.log += 'Found premove! In response to ' + opp_move.uci() + ', ' + temp_board.san(move) + '\n'
                    return move.uci()
                else:
                    return None
        else:
            # threshold at 30% are premoves
            if random.random() < 0.66:                
                # we play a premove
                # we assume opponent is going to play best move
                result = self.stockfish.play(temp_board, chess.engine.Limit(depth=5))
                if result.ponder is None:
                    return None
                my_move = result.ponder.uci()
                self.log += 'Found premove in premove mode! ' + my_move + '\n'
                return my_move # note my_move could also be None
            else:
                return None
    
    def decide_parameters(self, own_time, opp_time, starting_time):
        ''' Given a position, we must evaluate how 'quiet' it is and furthermore
            given a time constraint, how likely we are to make a mistake. In quiet
            positions we want to promote high accurate play to avoid computer-like
            moves. We must further decide how much the computer is going to spend
            on this move. Function returns [difficulty, stdev and time_limit]. '''
        
        # if in time scramble mode, position is always blunder prone and response is quick
        if self.time_scramble_mode:
            self.blunder_prone= True
            self.log += 'AtomicSamurai is in time-scramble mode. \n'
            # spend on average the amount of time as if there was 15 more moves to play
            if own_time < 25:
                return [7,20,0.1]
            else:
                if self.board.fullmove_number <10:
                    avg = own_time/260
                elif self.board.fullmove_number <20:
                    avg = own_time/220
                elif self.board.fullmove_number <30:
                    avg = own_time/180
                else:
                    avg = own_time/180
                self.log += 'Average time allowed: ' + str(avg) + '\n'
                self.log += 'Own time remaining: ' + str(own_time) +'\n'
                if starting_time < 61:
                    if own_time > 40:
                        stdev = own_time/50
                    else:
                        stdev = own_time/40
                else:
                    stdev = own_time/50
                self.log += 'Standard devation on time allowed: '+ str(stdev) + '\n'
                time_spend = max(0.1, np.random.normal(avg, stdev))
                return [9,20,time_spend]
        
        # self.phase = phase_of_game(self.board)
        if self.phase == 'opening':
            if starting_time < 61:
                avg_time = 0.1
            else:
                avg_time = 0.4
            time_spend = max(0.2, np.random.normal(avg_time, 0.3))
            return [10,4,time_spend] # quick accurate moves
        
        self.blunder_prone = True
        
        # now we decide the mean time spend for the normal distributions
        # this would be based mainly on own time, which is handled by the 
        # self.time_scramble attribute, but also the opp_time, if they are in
        # time trouble
        if opp_time/starting_time < 1/6:
            # add a random probability factor to increase randomness and minimise
            # detection of pattern
            if random.random() < 0.8:
                mean_time = 1.5
            else:
                mean_time = starting_time/100
                
        ''' For normal play, (i.e. not time scrambling or opening), we base the
            model on move duration on a chi-squared distribution with r=7 degrees
            of freedom. This is based on the study https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2965049/
            and it intuitively correct. The x-axis is the fullmove_number. '''
        move_number = self.board.fullmove_number
        easy_factor = 0.5
        hard_factor = 0.8
        time_spend = chi2.pdf(move_number/4, 7)
        # to make sure it doesn't blitz out endgame moves too quickly
        if move_number > 40:
            time_spend = time_spend * 2
        self.log += 'Mean time from chisquare: ' + str(time_spend) + '\n'
        self.log += 'Easy and hard factors: ' + str(easy_factor) + '; ' + str(hard_factor) + '\n'
        stdev = starting_time/90
        
        # the greater the complexity, the more time spent on move
        # for lower compelxities, spend little time
        # otherwise, randomise time spend by normal distribution
        # if complexity < 25:
        #     time_limit = max(np.random.normal(easy_factor * time_spend, stdev), 0.1)
        # else: # will change these values for deployment
        time_limit = max(np.random.normal(hard_factor * time_spend, stdev), 0.1)         
        
        if self.shadow == True:
            time_limit = 1
        return 10, 4, time_limit
    
    def decide_time_scramble(self, own_time, starting_time):
        ''' Given the amount of time left, decied whether or not to be in time
            scramble mode. '''
        own_time_frac = own_time/starting_time
        # if own_time is below a certain threshold, then automatically
        # enter time_scramble mode
        if own_time < 25:
            return True
        elif starting_time < 61:
            return True          
        elif own_time_frac < 1/6:
            return True
        else:
            return False

    def calculate_caps(self, starting_time):
        ''' Function which given a chess.Board() input returns a dictionary with
            the number of cap moves per piece used to consider human moves. This
            depends on how quiet/closed the position is. '''
        
        # go through all legal moves, and take a percentage per piece
        pawn_moves = 0
        knight_moves = 0
        bishop_moves = 0
        rook_moves = 0
        queen_moves = 0
        king_moves = 0
        for move in self.board.legal_moves:
            if self.board.piece_type_at(move.from_square) == chess.PAWN:
                pawn_moves += 1
            elif self.board.piece_type_at(move.from_square) == chess.KNIGHT:
                knight_moves += 1
            elif self.board.piece_type_at(move.from_square) == chess.BISHOP:
                bishop_moves += 1
            elif self.board.piece_type_at(move.from_square) == chess.ROOK:
                rook_moves += 1
            elif self.board.piece_type_at(move.from_square) == chess.QUEEN:
                queen_moves += 1
            elif self.board.piece_type_at(move.from_square) == chess.KING:
                king_moves += 1
        
        opening_weights = [int(pawn_moves * 0.5 + 3),
                            int(knight_moves * 0.6 + 3),
                            int(bishop_moves * 0.6 + 3),
                            int(rook_moves * 0.2 + 1),
                            int(queen_moves * 0.4 + 3),
                            int(king_moves * 1 + 6)]
        
        midgame_weights = [int(pawn_moves * 0.5 + 3),
                            int(knight_moves * 0.5 + 3),
                            int(bishop_moves * 0.5 + 3),
                            int(rook_moves * 0.5 + 3),
                            int(queen_moves * 0.5 + 4),
                            int(king_moves * 1 + 6)]
        
        endgame_weights = [int(pawn_moves * 0.7 + 3),
                            int(knight_moves * 0.7 + 3),
                            int(bishop_moves * 0.7 + 3),
                            int(rook_moves * 1 + 3),
                            int(queen_moves * 1 + 3),
                            int(king_moves * 1 + 6)]
        
        
        self.log += 'Phase of game recognised: ' + self.phase + '\n'
        if self.phase == 'opening':
            weights = opening_weights
        elif self.phase == 'midgame':
            weights = midgame_weights
        elif self.phase == 'endgame':
            weights = endgame_weights
        
        # if number of pieces if VERY few, we consider an absurd amount of squares
        # to help the engine along
        no_pieces = len(self.board.piece_map())
        if no_pieces < 8:
            self.log += 'PLAY TILL END TRIGGERED, number of pieces left: ' + str(no_pieces) + '\n'
            weights = [64,24,24,24,36,20]
        
        # if engine is currently blunder prone, we must significantly decrease
        # the number of caps to make the move as uncalculated and 'human' as possible
        if self.blunder_prone:
            self.log += 'Currently this position is blunder prone. \n'
            # for i in range(len(weights)):
            #     if weights[i] == 1:
            #         # leave it alone
            #         pass
            #     else:
            #         # give a more restricted set of weights
            #         if starting_time < 61:
            #             weights = [3,2,2,3,7,2]
            #         elif starting_time < 181:
            #             #weights = [10,10,10,10,10,10]
            #             weights = [3,3,3,3,7,6]
            #         elif starting_time < 301:
            #             weights = [4,3,3,4,7,6]
            #         else:
            #             weights = [4,4,4,4,7,6]
            weights = [10,10,15,20,15,10]
        else:
            self.log += 'This position has been decided not to be blunder prone. \n'
        
        self.log += 'Weights Chosen:' + str(weights) + '\n'
        
        pieces = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]
                           
        piece_caps = dict(zip(pieces, weights))
        return piece_caps
    
    def write_log(self):
        ''' Writes down thinking into a log file for debugging. '''
        with open(LOG_FILE,'a') as log:
            log.write(self.log)
            log.close()

    def make_move(self, time_dic, prev_fen=None, prev_move=None):
        ''' Function which decides what move to make under a certain time_limit. '''
        self.log += 'Move number: ' + str(self.board.fullmove_number) + '\n'
        self.prev_fen = prev_fen
        self.prev_move = prev_move
        self.log += 'Current fen: ' + self.board.fen() + '\n'
        self.log += 'Previous fen: ' + str(self.prev_fen) + '\n'
        self.log += 'Previous opponent move: ' + str(self.prev_move) + '\n'
        self.log += 'Previous own move: ' + str(self.prev_own_move) + '\n'
        self.log += str(self.board) + '\n'
        
        self.phase = phase_of_game(self.board)
        self.log += 'Current phase: ' + self.phase + '\n'
        self.win_percentage = self.calculate_win_percentage()
        self.king_dang = king_danger(self.board, self.side, self.phase)
        self.log += 'Current King Danger: ' + str(self.king_dang) + '\n'
        # extracting information about times to hep with decision making
        starting_time = time_dic['starting_time']
        if self.side == chess.WHITE:
            own_time = time_dic['white_time']
            opp_time = time_dic['black_time']
        else:
            own_time = time_dic['black_time']
            opp_time = time_dic['white_time']
        self.own_time = own_time
        self.opp_time = opp_time
        self.log += 'Own time left: ' + str(own_time) + '\n'
        # first check if position is hopeless, in which case resign
        if self.decide_resign(own_time, opp_time, starting_time):
            self.resigned = True
            return None
        else:
            # see if we should be in premove_mode:
            if own_time < 11 or starting_time < 16:
                self.premove_mode = True
            else:
                self.premove_mode = False
            # if there's an obvious move, play it:
            move = self.check_obvious(own_time, starting_time, prev_move, prev_fen)
            if move is not None:
                chosen_move = move
                self.quick_move = True
            else:
                self.quick_move = False
                # check to see if we are in time_scramble mode
                if self.decide_time_scramble(own_time, starting_time) == True:
                    self.time_scramble_mode = True
                else:
                    self.time_scramble_mode = False
                difficulty, standard_dev, time_limit = self.decide_parameters(own_time, opp_time, starting_time)
                # store the time_limit in move_times
                self.move_times.append(time_limit)
                if len(self.move_times) > 5:
                    del self.move_times[0]
                legal_moves = self.filter_legal_moves(self.search_human_moves(starting_time))
                self.log += 'Legal moves found from human search: ' + str(legal_moves) + '\n'
                
                chosen_move = self.evaluate_moves(difficulty, standard_dev, moves_list=legal_moves, time_limit=time_limit)
            
            self.log += 'Last 5 move times: ' + str(self.move_times) + '\n'
            self.log += 'Chosen move: ' + chosen_move + ', '+ self.board.san(chess.Move.from_uci(chosen_move))  + '\n'
            self.board.push_uci(chosen_move)
        if self.log_true:
            # we write to log
            self.write_log()
        self.log = ''
        self.prev_own_move = chosen_move
        return chosen_move
    
    def reset(self):
        ''' Resets the board and clears the move_stack for a new game. '''
        self.board.clear()
        self.board.reset_board()
        self.board.set_castling_fen('KQkq')
        self.board.turn = chess.WHITE
        self.phase = 'opening'
        self.log = ''
        if self.side:
            self.log += 'Playing side: WHITE \n'
        else:
            self.log += 'Playing side: BLACK \n'
        self.blunder_prone = False # when true, the engine is prone to make a human like error
        self.resigned = False
        self.time_scramble_mode = False
        self.resign_threshold = random.randint(1,10) + 30 # number of moves the engine must play before resigning
        
        # if using too much memory, refresh
        
        if psutil.virtual_memory().percent > 90:
            print('Memory Usage Percentage: ', psutil.virtual_memory().percent)
            # refresh memory
            # clearing memory
            try:
                from IPython import get_ipython
                get_ipython().magic('clear')
                get_ipython().magic('reset -f')
            except:
                pass
            print('Memory after: ', psutil.virtual_memory().percent)

def test():
    ''' Test function used for various testing. '''
    # engine = AtomicSamurai(playing_side= chess.WHITE, starting_position_fen='2k1r2r/pppq1pp1/6b1/3P4/N2p2P1/1B1P1P1p/PP3R1P/R3Q1K1 w - - 1 21')
    # engine.blunder_prone = True
    # engine.prev_own_move = 'c4d5'
    # engine.make_move({'white_time': 33.7, 'black_time':25.11, 'starting_time': 60}, prev_fen='2kr3r/pppq1pp1/6b1/3P4/N2p2P1/1B1P1P1p/PP3R1P/R3Q1K1 b - - 0 20', prev_move='d8e8')
    # print(engine.log)
    time_s = time.time()
    print(king_danger(chess.Board('1rb2rk1/p3ppbp/2pp1np1/q7/2P1P3/2N1B3/PPQ1BPPP/R4RK1 w - - 4 12'), chess.WHITE, 'midgame'))
    time_f = time.time()
    print(time_f - time_s)
    #print(complexity(chess.Board('r4rk1/Bq1nbpp1/3p1nbp/RN1Pp3/1QN1P3/1B3P2/2P3PP/5RK1 b - - 0 26')))
    # time_s = time.time()
    # print(is_en_pris(chess.Board('1k2r3/8/3n4/8/4P3/3K4/Q7/8 w - - 0 1'), 28))
    # time_f = time.time()
    # print(time_f - time_s)

if __name__ == '__main__':
    test()