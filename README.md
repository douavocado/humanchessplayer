# ATOMIC SAMURAI

Atomic Samurai is the name given to the chess engine which 'imitates' human moves. It uses machine learning to recognize given any chess position, it deduces the rough probabilities that a human plays a certain move. Only top set of moves are considered (usually between 5-10), and eventually fed to [stockfish](https://stockfishchess.org/) engine to evaluate and play the move with the desired average centipawn loss.

The move selection models were based on [this](https://towardsdatascience.com/predicting-professional-players-chess-moves-with-deep-learning-9de6e305109e) and [this](https://pdfs.semanticscholar.org/28a9/fff7208256de548c273e96487d750137c31d.pdf). There is a piece selector model, which predicts the most likely squares the human player would move from. Combined with the piece-to models, which predicts the likely squares for given pieces and their types in a position, we have a basis for producing an overall probability of a whole move. Weights were adjusted slightly to account for other factors (moves which take pieces are more attractive etc.).

Models were trained from high level grandmaster games (2500+ elo) and downloaded from [fics](https://www.ficsgames.org/) as well as the games of high-rated players on [lichess](https://lichess.org/) itself. Using training data creating scripts *train_data_creator.py* (for piece_selector) and *training_data_creator_pieces.py* (for piece move_to models). The model is trained at *train_move_from_model.py*.

## Requirements

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the necessary requirements.

```bash
pip3 install -r requirements.txt
```

Also a requirement is to install stockfish/any other strong existing computer chess engine. Install stockfish either through **pip** or [here](https://stockfishchess.org/).

For optional, but not necessary sound effects (sounded when the program has detected a new game, also when there has been an error in retrieving game data from lichess), you should install [mpg123](https://www.mpg123.de/download.shtml). Note that this is already built-in for most linux, unix systems.

## Configuration

Before usage, you need to configure the your user settings. Either manually edit the *config.ini* file or run *config_client.py*, which has a useful calibration tool for mouse clicks on the computer screen.

Make sure the **full** path to your stockfish binary is given. For windows users, please remember to double backslash file names. For more details of this, see [this](https://stackoverflow.com/questions/26662247/invalid-argument-error-and-python-not-reading-file/34616750).


## Usage

Navigate to the downloaded folder in command line (using **cd**) and run:

```bash
python3 main.py [-s] [-n]
```

Or to see the options:

```bash
python3 main.py -h
```

Once the 'Status connected' message is received, you can logon to lichess and start playing! For non-ultrabullet games, the **first three seconds** of your clock time is left alone. This gives you leeway to play your own openings. After that, the program kicks in.

Note this is still a developing project, so at times the engine will still occasionally make very 'computer-like' moves.
