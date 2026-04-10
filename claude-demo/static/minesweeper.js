class MinesweeperGame {
    constructor() {
        // Difficulty configuration
        this.difficulties = {
            easy: { rows: 9, cols: 9, mines: 10 },
            medium: { rows: 16, cols: 16, mines: 40 },
            hard: { rows: 16, cols: 30, mines: 99 }
        };

        this.currentDifficulty = 'easy';
        this.board = [];
        this.minesLeft = 0;
        this.timer = 0;
        this.timerInterval = null;
        this.gameStarted = false;
        this.gameOver = false;
        this.gameWon = false;

        this.bindEvents();
        this.initGame();
    }

    bindEvents() {
        // Difficulty buttons
        document.querySelectorAll('.diff-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelector('.diff-btn.active').classList.remove('active');
                e.target.classList.add('active');
                this.currentDifficulty = e.target.dataset.diff;
                this.initGame();
            });
        });

        // Reset button
        document.getElementById('resetBtn').addEventListener('click', () => {
            this.initGame();
        });

        // Modal ok
        document.getElementById('modalOk').addEventListener('click', () => {
            this.hideModal();
        });
    }

    initGame() {
        // Stop existing timer
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }

        const config = this.difficulties[this.currentDifficulty];
        this.minesLeft = config.mines;
        this.timer = 0;
        this.gameStarted = false;
        this.gameOver = false;
        this.gameWon = false;

        // Initialize empty board
        this.board = [];
        for (let i = 0; i < config.rows; i++) {
            this.board[i] = [];
            for (let j = 0; j < config.cols; j++) {
                this.board[i][j] = {
                    isMine: false,
                    revealed: false,
                    flagged: false,
                    adjacentMines: 0
                };
            }
        }

        this.updateMinesLeft();
        this.updateTimer();
        this.updateFace();
        this.render();
    }

    placeMines(firstRow, firstCol) {
        const config = this.difficulties[this.currentDifficulty];
        let minesPlaced = 0;

        while (minesPlaced < config.mines) {
            const r = Math.floor(Math.random() * config.rows);
            const c = Math.floor(Math.random() * config.cols);

            // Don't place mine on first click, don't duplicate
            if (!this.board[r][c].isMine && !(r === firstRow && c === firstCol)) {
                this.board[r][c].isMine = true;
                minesPlaced++;
            }
        }

        // Calculate adjacent mines
        this.calculateAdjacentMines();
    }

    calculateAdjacentMines() {
        const config = this.difficulties[this.currentDifficulty];

        for (let i = 0; i < config.rows; i++) {
            for (let j = 0; j < config.cols; j++) {
                if (!this.board[i][j].isMine) {
                    let count = 0;
                    this.forEachNeighbor(i, j, (ni, nj) => {
                        if (this.board[ni][nj].isMine) {
                            count++;
                        }
                    });
                    this.board[i][j].adjacentMines = count;
                }
            }
        }
    }

    forEachNeighbor(row, col, callback) {
        for (let di = -1; di <= 1; di++) {
            for (let dj = -1; dj <= 1; dj++) {
                if (di === 0 && dj === 0) continue;
                const ni = row + di;
                const nj = col + dj;
                if (this.isValidCell(ni, nj)) {
                    callback(ni, nj);
                }
            }
        }
    }

    isValidCell(row, col) {
        const config = this.difficulties[this.currentDifficulty];
        return row >= 0 && row < config.rows && col >= 0 && col < config.cols;
    }

    render() {
        const config = this.difficulties[this.currentDifficulty];
        const boardElement = document.getElementById('gameBoard');

        // Set grid template
        boardElement.style.gridTemplateColumns = `repeat(${config.cols}, 1fr)`;
        boardElement.innerHTML = '';

        for (let i = 0; i < config.rows; i++) {
            for (let j = 0; j < config.cols; j++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = i;
                cell.dataset.col = j;

                if (this.board[i][j].revealed) {
                    cell.classList.add('revealed');
                    if (this.board[i][j].isMine) {
                        cell.textContent = '💣';
                        if (this.gameOver && this.board[i][j].isMine && this.isExplosion) {
                            cell.classList.add('mine-exploded');
                        }
                    } else if (this.board[i][j].adjacentMines > 0) {
                        cell.textContent = this.board[i][j].adjacentMines;
                        cell.dataset.count = this.board[i][j].adjacentMines;
                    }
                } else if (this.board[i][j].flagged) {
                    cell.textContent = '🚩';
                    cell.classList.add('flagged');
                }

                cell.addEventListener('click', () => this.handleLeftClick(i, j));
                cell.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    this.handleRightClick(i, j);
                });

                boardElement.appendChild(cell);
            }
        }
    }

    handleLeftClick(row, col) {
        if (this.gameOver || this.gameWon) return;
        if (this.board[row][col].revealed) return;
        if (this.board[row][col].flagged) return;

        // First click - start game and place mines
        if (!this.gameStarted) {
            this.gameStarted = true;
            this.placeMines(row, col);
            this.startTimer();
        }

        // If it's a mine - game over
        if (this.board[row][col].isMine) {
            this.gameOver = true;
            this.board[row][col].revealed = true;
            this.revealAllMines(row, col);
            this.endGame(false);
            this.render();
            return;
        }

        // Reveal this cell
        this.revealCell(row, col);

        // Check win
        this.checkWin();
        this.render();
    }

    handleRightClick(row, col) {
        if (this.gameOver || this.gameWon) return;
        if (this.board[row][col].revealed) return;

        // Toggle flag
        this.board[row][col].flagged = !this.board[row][col].flagged;
        this.minesLeft += this.board[row][col].flagged ? -1 : 1;
        this.updateMinesLeft();
        this.render();

        // Check win after flagging
        this.checkWin();
    }

    revealCell(row, col) {
        if (!this.isValidCell(row, col)) return;
        if (this.board[row][col].revealed || this.board[row][col].flagged) return;

        this.board[row][col].revealed = true;

        // If adjacentMines is 0 - reveal neighbors recursively
        if (this.board[row][col].adjacentMines === 0) {
            this.forEachNeighbor(row, col, (ni, nj) => {
                this.revealCell(ni, nj);
            });
        }
    }

    revealAllMines(explodedRow, explodedCol) {
        const config = this.difficulties[this.currentDifficulty];
        for (let i = 0; i < config.rows; i++) {
            for (let j = 0; j < config.cols; j++) {
                if (this.board[i][j].isMine) {
                    this.board[i][j].revealed = true;
                }
            }
        }
        // Mark the exploded mine
        this.explosionRow = explodedRow;
        this.explosionCol = explodedCol;
    }

    checkWin() {
        const config = this.difficulties[this.currentDifficulty];
        let unrevealed = 0;

        for (let i = 0; i < config.rows; i++) {
            for (let j = 0; j < config.cols; j++) {
                if (!this.board[i][j].revealed && !this.board[i][j].isMine) {
                    unrevealed++;
                }
            }
        }

        if (unrevealed === 0) {
            this.gameWon = true;
            this.endGame(true);
        }
    }

    endGame(won) {
        this.gameOver = true;
        this.stopTimer();

        if (won) {
            this.showModal('🎉 恭喜胜利', '你成功扫出了所有地雷！');
        } else {
            this.showModal('💥 游戏结束', '你踩中了地雷，再来一局吧！');
        }
    }

    startTimer() {
        this.timer = 0;
        this.updateTimer();
        this.timerInterval = setInterval(() => {
            this.timer++;
            this.updateTimer();
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateMinesLeft() {
        document.getElementById('minesLeft').textContent = this.minesLeft;
    }

    updateTimer() {
        document.getElementById('timer').textContent = this.timer;
    }

    updateFace() {
        let face = '😐';
        if (this.gameOver) face = '😵';
        if (this.gameWon) face = '😎';
        document.getElementById('face').textContent = face;
    }

    showModal(title, message) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalMessage').textContent = message;
        document.getElementById('messageModal').classList.remove('hidden');
        this.updateFace();
    }

    hideModal() {
        document.getElementById('messageModal').classList.add('hidden');
    }
}

// Initialize game when DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    window.game = new MinesweeperGame();

    // Prevent context menu on board
    document.getElementById('gameBoard').addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });
});
