import chess
import chess.svg

from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QApplication, QWidget

board_fen= '''b b r k r n n q
p p p . . p . p
. . . . . . p .
. . . p . . . .
. . . P P . . .
. . . . . . p P
P P P . . . . .
B B R K R N N Q'''

board_fen= board_fen.replace('\n','/').replace(' ','') 
for i in range(8):
    board_fen = board_fen.replace('.' * (8-i) , f'{8-i}')

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setGeometry(100, 100, 1100, 1100)

        self.widgetSvg = QSvgWidget(parent=self)
        self.widgetSvg.setGeometry(10, 10, 800, 800)

        self.chessboard = chess.Board(board_fen)

        self.chessboardSvg = chess.svg.board(self.chessboard).encode("UTF-8")
        self.widgetSvg.load(self.chessboardSvg)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

