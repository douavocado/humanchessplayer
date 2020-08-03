# ATOMIC SAMURAI

Atomic Samurai is the name given to the chess engine which 'imitates' human moves. It uses machine learning to recognize given any chess position, it deduces the rough probabilities that a human plays a certain move. Only top set of moves are considered (usually between 5-10), and eventually fed to [stockfish](https://stockfishchess.org/) engine to evaluate and play the move with the desired average centipawn loss.

The move selection models were based on [this](https://towardsdatascience.com/predicting-professional-players-chess-moves-with-deep-learning-9de6e305109e) and [this](https://pdfs.semanticscholar.org/28a9/fff7208256de548c273e96487d750137c31d.pdf). There is a piece selector model, which predicts the most likely squares the human player would move from. Combined with the piece-to models, which predicts the likely squares for given pieces and their types in a position, we have a basis for producing an overall probability of a whole move. Weights were adjusted slightly to account for other factors (moves which take pieces are more attractive etc.).

Models were trained from high level grandmaster games (2500+ elo) and downloaded from [fics](https://www.ficsgames.org/) using training data creating scripts *train_data_creator.py* (for piece_selector) and *training_data_creator_pieces.py* (for piece move_to models). The model is trained at *train_move_from_model.py*.

## Requirements

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the necessary requirements.

```bash
pip3 install -r requirements.txt
```

## Usage

Navigate to the downloaded folder in command line (using **cd**) and run:

```python3
python3 main.py [USERNAME] [-s]
```

Where *USERNAME* is your lichess username, and the optional argument *-s* puts the engine in 'shadow mode', where the mouse only hovers over moves instead of executing them.
