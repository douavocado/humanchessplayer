#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 13:47:58 2020

@author: jx283
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, MaxPool2D, Flatten, Dropout
from sklearn.preprocessing import MinMaxScaler

from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import EarlyStopping

SAVE_FILE = 'piece_selector/training_data_midgame_fics.h5'

training_file_train_df = pd.read_hdf(SAVE_FILE, key='train')
X = training_file_train_df.values
training_file_test_df = pd.read_hdf(SAVE_FILE, key='test')
y = training_file_test_df.values[:len(X)]

Xtrain, Xtest, ytrain, ytest = train_test_split(X, y, test_size=0.2)

# RESHAPING
Xtrain= Xtrain.reshape(len(Xtrain), 8, 8, 12)
Xtest = Xtest.reshape(len(Xtest), 8, 8, 12)

# scaler = MinMaxScaler()
# Xtrain = scaler.fit_transform(Xtrain)
# Xtest = scaler.transform(Xtest)

model = Sequential()

## FIRST SET OF LAYERS

# CONVOLUTIONAL LAYER
model.add(Conv2D(filters=64, kernel_size=(2,2),input_shape=(8, 8, 12), activation='relu',))
# POOLING LAYER
# model.add(MaxPool2D(pool_size=(2, 2)))

## SECOND SET OF LAYERS

# CONVOLUTIONAL LAYER
model.add(Conv2D(filters=64, kernel_size=(2,2),input_shape=(8, 8, 12), activation='relu',))
# POOLING LAYER
# model.add(MaxPool2D(pool_size=(2, 2)))

# FLATTEN IMAGES FROM 8,8 by 12 to 768 BEFORE FINAL LAYER
model.add(Flatten())

# 256 NEURONS IN DENSE HIDDEN LAYER (YOU CAN CHANGE THIS NUMBER OF NEURONS)
model.add(Dense(1024, activation='relu'))
# model.add(Dense(512, activation='relu'))
# model.add(Dense(256, activation='relu'))
# model.add(Dense(128, activation='relu'))

# LAST LAYER IS THE CLASSIFIER, THUS 64 POSSIBLE CLASSES
model.add(Dense(64, activation='softmax'))


model.compile(loss='categorical_crossentropy',
              optimizer='adam',
              metrics=['accuracy'])

early_stop = EarlyStopping(monitor='val_loss',patience=0)

model.fit(Xtrain,ytrain,epochs=1000,validation_data=(Xtest,ytest),callbacks=[early_stop], batch_size=128)

losses = pd.DataFrame(model.history.history)
losses[['accuracy','val_accuracy']].plot()
plt.show()

model.save('piece_selector_models/piece_selector_midgame_fics.h5')