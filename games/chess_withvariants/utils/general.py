URL_STOCKFISH = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar"
import os
#Useful for downloading resources
#E.G the chess engine
# TOBETESTED
def get_path_file():
    cur_path = os.path.split(os.path.realpath(__file__))[0]
    project_path = os.path.split(cur_path)[0]
    return project_path

#We will load the binary here
def get_path_stockfish_bin():
    return os.path.join(get_path_file(), "resources","stockfish-ubuntu-x86-64-avx2" )


def download_stockfish():
    pass
