#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 14:55:45 2020

@author: jx283
"""
import time
from python_imagesearch.imagesearch import imagesearcharea

time_s = time.time()
pos =imagesearcharea("./python_logo.png", 0, 0, 800, 750)
time_f = time.time()
if pos[0] != -1:
    print("position : ", pos[0], pos[1], "in", time_f-time_s, "seconds")
else:
    print("image not found")