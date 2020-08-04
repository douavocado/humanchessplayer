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
from scipy.stats import chi2

import chess
import chess.engine

import numpy as np
from tensorflow.keras.models import load_model

import random
import math

# load all models

# loading piece_selector model
# opening_selector = load_model('piece_selector_models/piece_selector_opening.h5')
midgame_selector = load_model('piece_selector_models/piece_selector_midgame.h5')
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

move_to_models = {chess.PAWN: pawn_model,
                  chess.KNIGHT: knight_model,
                  chess.BISHOP: bishop_model,
                  chess.ROOK: rook_model,
                  chess.QUEEN: queen_model,
                  chess.KING: king_model}

STOCKFISH = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
LOG_FILE = 'Engine_Logs/log_' + str(datetime.datetime.now()) + '.txt'

# value of each piece, used in engine.check_obvious for takebacks
points_dic = {chess.PAWN: 1,
              chess.KNIGHT: 3,
              chess.BISHOP: 3.5,
              chess.ROOK: 4.5,
              chess.QUEEN: 6,
              chess.KING: 0}

def phase_of_game(board):
    ''' Takes in a chess.Board() instance and returns opening, midgame, endgame
        depending on what phase of the game the board position is. '''
    # count minor and major pieces on the board
    min_maj_pieces = 0
    for square in chess.SQUARES:
        if board.piece_type_at(square) is not None: # square is occupied
            if board.piece_type_at(square) != chess.PAWN and board.piece_type_at(square) != chess.KING:
                min_maj_pieces += 1
    if min_maj_pieces < 7:
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
        
    def __init__(self, log=True, shadow=True, piece_models_dic=move_to_models, playing_side=chess.WHITE, starting_position_fen=chess.STARTING_FEN):
        self.piece_models = piece_models_dic # dictionary of all piece models
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
        self.bullet_threshold = random.randint(1,5) + 9 # threshold before engine goes into bullet mode
        self.premove_mode = False # when engine is in premove mode, a certain percentage of moves it makes are premoves
        self.big_material_take = False # if oppenent suddenly hangs a piece (in time scrambles), don't immediately take back (let's lichess clinet know)
        self.mate_in_one = False
        self.shadow = shadow# alters thinking times to be much more stable
        self.log_true = log # whether or not to output a log file
    
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
        
        move_prob ={}
        
        for move, from_sq in from_squares.items():
            # need the probability at from square
            if self.side == chess.WHITE:
                from_sq_prob = square_predictions[0][chess.square_mirror(from_sq)]
            else:
                from_sq_prob = square_predictions[0][from_sq]
            to_square_prob = move_dic[move]
            # if current piece is being attacked, give it extra weight relative to the
            # attacked piece's value
            
            total_prob = from_sq_prob * to_square_prob
            move_prob[move] = total_prob
        
        
        move_prob = {k: v for k, v in sorted(move_prob.items(), key=lambda item: item[1], reverse=True)}
        # take first 4 moves as the root moves
        prob_ = {self.board.san(chess.Move.from_uci(key)) : prob for key, prob in move_prob.items()}
        self.log += 'Move Probabilities that the engine sees: \n'
        for key, value in prob_.items():
            self.log += str(key) + ': ' + str(value) + '\n'
        move_list = list(move_prob.keys())[:7]
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
        
        # count the number of pieces per piece_type:
        pieces_concerned = [piece.piece_type for piece in self.board.piece_map().values() if piece.color == self.side]
        multiplying_factors = {chess.PAWN: pieces_concerned.count(chess.PAWN),
                               chess.KNIGHT: pieces_concerned.count(chess.KNIGHT),
                               chess.BISHOP: pieces_concerned.count(chess.BISHOP),
                               chess.ROOK: pieces_concerned.count(chess.ROOK),
                               chess.QUEEN: pieces_concerned.count(chess.QUEEN),
                               chess.KING: pieces_concerned.count(chess.KING)}
        
        # now we iterate through all models
        piece_caps = self.calculate_caps(starting_time)
        
        for piece_type, model in self.piece_models.items():
            possible_uci_moves = []
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
                # if the to_square is in fact a capture of the opposition piece,
                # we give it a bonus proability as captures are more appealing
                # to humans
                if dummy_board.color_at(square_int) == chess.BLACK:
                    probability = probability*2
                
                for square in from_squares:
                    mirror_needed = self.side == chess.BLACK
                    # we need to mirror back the moves
                    uci = convert_square_to_uci(square, square_int, mirror=mirror_needed)
                    human_ucis[uci] = probability*multiplying_factors[piece_type]
        return human_ucis
    
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
        
        moves_dic = self.get_engine_lines(root_moves=moves_list, time_limit=time_limit)
        
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
        
        info = self.stockfish.analyse(self.board, chess.engine.Limit(depth=10))
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
                eval_ = (mate_in-50)*100
                
            elif str(info['score'])[1] == '+':
                # we are giving mate in this variation
                eval_ = (50-mate_in)*100
                
            else:
                raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
        
        if eval_ < 0:
            # then we are at a disadvantage
            msg = 'losing'
        else:
            msg = 'winning'
        
        win_percentage = abs( 100 * np.tanh(eval_ / (2 * mat)) )
        self.log += 'Win percentage: ' + str(round(win_percentage)) + ' ' + msg + '\n'
        
        time_finish = time.time()
        
        self.log += 'Time taken to calculate win_percentage: ' + str(time_finish - time_start) + '\n'
        return win_percentage, msg
        

    def complexity(self):
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
        self.log += 'Calculating complexity of the position... \n'
        time_start = time.time()
        
        mov = self.board.legal_moves.count()
        
        pie = len(self.board.piece_map())
        
        mat = 0
        own_mat = 0
        for square, piece in self.board.piece_map().items():
            if piece.piece_type == chess.PAWN:
                mat += 1
                if piece.color == self.board.turn:
                    own_mat += 1
            elif piece.piece_type == chess.KNIGHT:
                mat += 3.1
                if piece.color == self.board.turn:
                    own_mat += 3.1
            elif piece.piece_type == chess.BISHOP:
                mat += 3.5
                if piece.color == self.board.turn:
                    own_mat += 3.5
            elif piece.piece_type == chess.ROOK:
                mat += 5.5
                if piece.color == self.board.turn:
                    own_mat += 5.5
            elif piece.piece_type == chess.QUEEN:
                mat += 9.9
                if piece.color == self.board.turn:
                    own_mat += 9.9
            elif piece.piece_type == chess.KING:
                mat += 3
                if piece.color == self.board.turn:
                    own_mat += 3
        
        # now need to work out the number of good moves, at most 100 centipawns
        # worst than best move
        analysis = self.stockfish.analyse(self.board, chess.engine.Limit(depth=8), multipv=18)
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
                    eval_score = (mate_in-50)*50
                    
                elif str(info['score'])[1] == '+':
                    # we are giving mate in this variation
                    eval_score = (50-mate_in)*50
                    
                else:
                    raise Exception('ERROR, do not understand the evaluation score:', str(info['score']))
            evals.append(eval_score)
        evals.sort()
        best_eval = evals[-1]
        good_evals = [x for x in evals if x +100 > best_eval]
        
        gmo = len(good_evals)
        
        self.log += 'gmo, mov, pie, mat, own_mat, best_eval: ' + str(gmo) + ';'+ str(mov) + ';' + str(pie) + ';' + str(mat) + ';' + str(own_mat) + ';' + str(best_eval) + '\n'
        complexity = gmo * mov * pie * mat / (400 * own_mat ) 
        self.log += 'Complexity calculated: ' + str(complexity) + '\n'
        
        # added metric form lucas chess: Efficient mobility
        eff_mob = (gmo-1)*100/mov
        self.log += 'Efficient mobility calculated: ' + str(eff_mob) + '\n'
    
        time_finish = time.time()
        
        self.log += 'Time taken to calculate complexity and eff_mob: ' + str(time_finish - time_start) + '\n'
        
        return complexity, eff_mob

    def decide_resign(self, own_time, opp_time, starting_time):
        ''' The decision making function which decides whether to resign. '''
        # does not resign in the first 20 moves
        return False
        if self.board.fullmove_number < self.resign_threshold:
            return False
        else:
            # check the win percentage
            percentage, msg = self.calculate_win_percentage()
            if msg == 'winning':
                return False
            else:
                # If we are playing with time constraints, must take that into consideration
                if starting_time is not None:
                    # If opponent has less than 30 seconds left, never resign
                    if opp_time < 30:
                        return False
                    # If we are losing badly, and opponent has quite alot of time
                    # we resign
                    opp_time_frac = opp_time/starting_time
                    if opp_time_frac > 1/6 and percentage > 99:
                        self.log += 'POSITION IS HOPLESS AND OPPONENT HAS ENOUGH TIME, ATOMIC SAMURAI RESIGNS \n'
                        return True
                else:
                    if percentage > 97:
                        self.log += 'POSITION IS HOPLESS, ATOMIC SAMURAI RESIGNS \n'
                        return True
                    else:
                        return False

    def check_obvious(self, own_time, starting_time, prev_move, prev_fen):
        ''' The first filtering process of deciding what move to make. Will get
            engine to search for minimal depth and see if there is a standout
            move. If there is, AtomicSamurrai will play it regardless. 
            
            An obvious move is one which has by far the best evaluation from
            minimal depth search, and also the piece is either en pris or is
            a take-back during an exchange. '''
        if starting_time < 61:
            depth = 5
        else:
            depth = 6
        moves_dic = self.get_engine_lines(depth=depth, multipv=2)
        # if top obvious move is more than 200 centipawns better than second move
        
        # for some reason the analysis object doesn't always return desired
        # number of lines, in which case we just pass
        if len(moves_dic) < 2:
            return None
    
        self.log += 'Obvious Moves check: ' + str(moves_dic) + '\n'
        sorted_evals = sorted(moves_dic)
        top_move_obj = chess.Move.from_uci(moves_dic[sorted_evals[-1]])
        if sorted_evals[-1] > 4800: # then the move is a mate in one
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
                if abs(point_diff) < 1.7:
                    take_back = True
                    self.big_material_take = False
                    self.log += 'Top move is a take-back. \n'
                elif point_diff < -2.5:   
                    self.big_material_take = True
                    take_back = False
                    self.log += 'Top move is not a take-back. \n'
                else:
                    take_back = False
                    self.big_material_take = False
                    self.log += 'Top move is not a take-back. \n'
            elif self.board.piece_at(move_to_sq) is not None and opp_prev_move.to_square == move_to_sq:
                take_back = False
                self.log += 'Top move is not a take-back. \n'
                if points_dic[self.board.piece_type_at(move_to_sq)] > 2.9:
                    self.big_material_take = True
                elif points_dic[self.board.piece_type_at(move_to_sq)] - points_dic[self.board.piece_type_at(move_from_sq)] > 1:
                    self.big_material_take = True
                else:
                    self.big_material_take = False
            else:
                self.big_material_take = False
                take_back = False
                self.log += 'Top move is not a take-back. \n'
        else:
            self.log += 'Top move is not a take-back. \n'
            take_back = False
            self.big_material_take = False
        
        self.log += 'big_material_take: ' + str(self.big_material_take) + '\n'
        
        # if currently in a time scramble, and take back is true, then we automatically take it back
        if self.time_scramble_mode == True and take_back == True:
            self.log += 'Obvious move found as currently in time scramble! \n'
            return moves_dic[sorted_evals[-1]]
        elif self.premove_mode == True:
            self.log += 'Obvious move found as currently in premove_mode! \n'
            return moves_dic[sorted_evals[-1]]
        
        # check if move from piece is under attack
        if self.side == chess.WHITE:
            opp_side = chess.BLACK
        elif self.side == chess.BLACK:
            opp_side = chess.WHITE
        
        if len(self.board.attackers(opp_side, move_from_sq)) > 0:
            # square is being attacked
            if len(self.board.attackers(self.side, move_from_sq)):
                # square not protected
                attacked = True
                self.log += 'Top move piece is under attack. \n'
            else:
                attacked = False
                self.log += 'Top move piece is not under attack. \n'
        else:
            attacked = False
            self.log += 'Top move piece is not under attack. \n'
        
        attacked_and_take = attacked and take_back
        
        if sorted_evals[-1] > sorted_evals[-2] + 200 and attacked_and_take:
            self.log += 'Obvious move found! \n'
            return moves_dic[sorted_evals[-1]]
        elif own_time < self.bullet_threshold:
            # if we are down serious time, play the obvious move
            self.log += 'No obvious move, but time low so we play it \n'
            return moves_dic[sorted_evals[-1]]
        elif starting_time < 61 and random.random() < 0.1 and self.big_material_take == False:
            # to increase move time variation during bullet games
            # play some quick moves
            self.log += 'No obvious move, but to increase move time variation we play it \n'
            return moves_dic[sorted_evals[-1]]
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
            if random.random() < 0.35:
                self.blunder_prone= True
            else:
                self.blunder_prone = False
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
                return [7,20,time_spend]
        
        self.phase = phase_of_game(self.board)
        if self.phase == 'opening':
            if starting_time < 61:
                avg_time = 0.1
            else:
                avg_time = 0.4
            time_spend = max(0.2, np.random.normal(avg_time, 0.3))
            return [10,4,time_spend] # quick accurate moves
        
        
        complexity, eff_mob = self.complexity() # calculates the complexity and eff_mob of the position
        
        # eff mob decides whether or not to blunder, complexity decides how much time
        # to spend on the move
        # when eff_mob is between 8 and 25 percent is when we are blunder prone
        
        
        if  8 < eff_mob < 20: # low complexity, play high accurate moves
            self.blunder_prone = True
            difficulty = random.random() * 3 + 7
            standard_dev = complexity**0.65
        elif eff_mob < 8:
            # there's still a chance that it would miss a tactic etc
            if random.random() < 0.3:
                self.log += 'eff_mob low, but decided to blunder anyway trying to miss a tactic. \n'
                self.blunder_prone = True
            else:
                self.blunder_prone = False
            
            difficulty = 10
            standard_dev = 4
        else:
            difficulty = 10
            standard_dev = 4
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
        easy_factor = starting_time/10 * (complexity/55)**1.8
        hard_factor = starting_time/7* (complexity/55)**1.8
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
        if complexity < 25:
            time_limit = max(np.random.normal(easy_factor * time_spend, stdev), 0.1)
        else: # will change these values for deployment
            time_limit = max(np.random.normal(hard_factor * time_spend, stdev), 0.1)         
        
        if self.shadow == True:
            time_limit = 1
        return difficulty, standard_dev, time_limit
    
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
            weights = [10,10,10,10,10,10]
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
        self.log += self.board.fen() + '\n'
        self.log += str(self.board) + '\n'
        # extracting information about times to hep with decision making
        starting_time = time_dic['starting_time']
        if self.side == chess.WHITE:
            own_time = time_dic['white_time']
            opp_time = time_dic['black_time']
        else:
            own_time = time_dic['black_time']
            opp_time = time_dic['white_time']
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
            else:
                # check to see if we are in time_scramble mode
                if self.decide_time_scramble(own_time, starting_time) == True:
                    self.time_scramble_mode = True
                else:
                    self.time_scramble_mode = False
                difficulty, standard_dev, time_limit = self.decide_parameters(own_time, opp_time, starting_time)
                legal_moves = self.filter_legal_moves(self.search_human_moves(starting_time))
                self.log += 'Legal_moves found from human search: ' + str(legal_moves) + '\n'
                
                chosen_move = self.evaluate_moves(difficulty, standard_dev, moves_list=legal_moves, time_limit=time_limit)
            self.log += 'Chosen move: ' + chosen_move + ', '+ self.board.san(chess.Move.from_uci(chosen_move))  + '\n'
            self.board.push_uci(chosen_move)
        if self.log_true:
            # we write to log
            self.write_log()
        self.log = ''
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

def test():
    ''' Test function used for various testing. '''
    engine = AtomicSamurai(playing_side= chess.WHITE, starting_position_fen='5rk1/ppp4p/3p3b/3Pnp2/QPPN1p1q/4rP1N/P5PP/1R3RK1 w - - 5 21')
    engine.blunder_prone = True
    engine.filter_legal_moves(engine.search_human_moves(180))
    # print(engine.log)
    #print(complexity(chess.Board('r4rk1/Bq1nbpp1/3p1nbp/RN1Pp3/1QN1P3/1B3P2/2P3PP/5RK1 b - - 0 26')))

if __name__ == '__main__':
    test()