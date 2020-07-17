#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  3 12:12:14 2020

@author: jx283

"""

import time
import requests
import re
import chess

last_fen = chess.STARTING_FEN
lookout = 'w'
URL = 'https://lichess.org/tv'

prev_time = time.time()
avgs = []
for i in range(10):
    time_ = time.time()
    avgs.append(time_-prev_time)
    prev_time = time_
    page = requests.get(URL)

    fen_search = re.findall('\"fen\":\"([^,]{10,80})\"', page.text)
    result_search = re.findall('Result', page.text)
    prev_move = re.findall('uci\":\"(.{3,5})\"', page.text)
    if len(result_search) > 0:
        # game has ended
        game_end = True
        successful_request = True
        break
    try:
        white_time = float(re.findall('white\":(\d{1,4}\.\d{1,2})', page.text)[0])
        black_time = float(re.findall('black\":(\d{1,4}\.\d{1,2})', page.text)[0])
        successful_request = True
    except IndexError:
        pass
    
    if len(fen_search) == 0:
        fen = chess.STARTING_FEN
    else:
        fen = fen_search[-1]
    
    if last_fen != fen and fen.split()[-5] == lookout:
        # we have found new updated fen
        pass

print('speed: ', sum(avgs)/len(avgs))