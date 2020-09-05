#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 16:11:53 2020

@author: jx283
"""
import time
import chess

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


time_s = time.time()
print(is_locked_file(chess.Board('2q2k2/4ppbp/2pp2p1/4n3/p3P3/P3BP1P/1P2Q1P1/1R4K1 w - - 0 24'),4))
time_f = time.time()