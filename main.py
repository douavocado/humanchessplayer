#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  3 17:27:17 2020

@author: jx283
"""
from lichess_premove_continuous_client import GameFinder
import argparse

# clearing memory
try:
    from IPython import get_ipython
    get_ipython().magic('clear')
    get_ipython().magic('reset -f')
except:
    pass

parser = argparse.ArgumentParser(description='Establish connection to lichess.org account.')
parser.add_argument('username', metavar='USERNAME', type=str, nargs=1, help='lichess username to connect to')
parser.add_argument("-s", "--shadow", help="Run in shadow mode, where the mouse hovers over it's recommended move approximately 1 second after position found.",
                        action="store_true")
args = parser.parse_args()
if len(args.username) > 1:
    raise Exception('Number of username inputs detected', len(args.username), ". Please enter only one username. ")
finder = GameFinder(args.username[0], shadow_mode=args.shadow)
finder.run()
# finder = GameFinder('Moment_of_Inertia')
# finder.run()