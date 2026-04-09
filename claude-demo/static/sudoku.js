class SudokuGame {
    constructor() {
        this.board = [];
        this.original = [];
        this.selectedCell = null;
        this.difficulty = {
            easy: 40,
            medium: 50,
            hard: 60
        };
        this.currentDifficulty = 'easy';

        this.init();
    }

    init() {
        this.bindEvents();
        this.newGame();
    }

    bindEvents() {
        document.getElementById('newGameBtn').addEventListener('click', () => this.newGame());
        document.getElementById('checkBtn').addEventListener('click', () => this.checkSolution());
        document.getElementById('hintBtn').addEventListener('click', () => this.giveHint());
        document.getElementById('modalOk').addEventListener('click', () => this.hideModal());

        document.querySelectorAll('.diff-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelector('.diff-btn.active').classList.remove('active');
                e.target.classList.add('active');
                this.currentDifficulty = e.target.dataset.diff;
                this.newGame();
            });
        });

        document.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    newGame() {
        // Generate a solved Sudoku
        this.generateFullSudoku();
        // Remove cells based on difficulty
        this.createPuzzle();
        // Copy to original to track which are pre-filled
        this.original = this.board.map(row => [...row]);
        // Render
        this.render();
    }

    generateFullSudoku() {
        // Create empty 9x9 board
        this.board = Array(9).fill().map(() => Array(9).fill(0));
        // Solve it using backtracking
        this.solve(this.board);
        // Shuffle to get different solutions
        this.shuffleBoard();
    }

    shuffleBoard() {
        // Shuffle numbers (1-9) to get different boards
        const nums = [1,2,3,4,5,6,7,8,9];
        const shuffled = [...nums].sort(() => Math.random() - 0.5);
        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                if (this.board[i][j] !== 0) {
                    this.board[i][j] = shuffled[this.board[i][j] - 1];
                }
            }
        }
    }

    solve(board) {
        const empty = this.findEmpty(board);
        if (!empty) return true; // solved

        const [row, col] = empty;
        // Try numbers 1-9 in random order
        const nums = [1,2,3,4,5,6,7,8,9].sort(() => Math.random() - 0.5);

        for (let num of nums) {
            if (this.isValid(board, row, col, num)) {
                board[row][col] = num;
                if (this.solve(board)) return true;
                board[row][col] = 0; // backtrack
            }
        }
        return false;
    }

    findEmpty(board) {
        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                if (board[i][j] === 0) return [i, j];
            }
        }
        return null;
    }

    isValid(board, row, col, num) {
        // Check row
        for (let i = 0; i < 9; i++) {
            if (board[row][i] === num && i !== col) return false;
        }

        // Check column
        for (let i = 0; i < 9; i++) {
            if (board[i][col] === num && i !== row) return false;
        }

        // Check 3x3 box
        const boxRow = Math.floor(row / 3) * 3;
        const boxCol = Math.floor(col / 3) * 3;

        for (let i = boxRow; i < boxRow + 3; i++) {
            for (let j = boxCol; j < boxCol + 3; j++) {
                if (board[i][j] === num && (i !== row || j !== col)) return false;
            }
        }

        return true;
    }

    createPuzzle() {
        const cellsToRemove = this.difficulty[this.currentDifficulty];
        let removed = 0;

        while (removed < cellsToRemove) {
            const row = Math.floor(Math.random() * 9);
            const col = Math.floor(Math.random() * 9);

            if (this.board[row][col] !== 0) {
                this.board[row][col] = 0;
                removed++;
            }
        }
    }

    render() {
        const boardElement = document.getElementById('sudokuBoard');
        boardElement.innerHTML = '';

        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = i;
                cell.dataset.col = j;

                if (this.original[i][j] !== 0) {
                    cell.textContent = this.original[i][j];
                    cell.classList.add('fixed');
                } else if (this.board[i][j] !== 0) {
                    cell.textContent = this.board[i][j];
                    cell.classList.add('user-filled');
                    // Check if this cell has error
                    if (!this.isValidCell(i, j)) {
                        cell.classList.add('error');
                    }
                }

                cell.addEventListener('click', () => this.selectCell(i, j));
                boardElement.appendChild(cell);
            }
        }

        if (this.selectedCell) {
            this.highlightRelated();
        }
    }

    selectCell(row, col) {
        // Unselect previous
        if (this.selectedCell) {
            const prev = this.getCellElement(this.selectedCell.row, this.selectedCell.col);
            prev.classList.remove('selected');
        }

        // Can't select fixed cells
        if (this.original[row][col] !== 0) {
            this.selectedCell = null;
            return;
        }

        this.selectedCell = { row, col };
        const cell = this.getCellElement(row, col);
        cell.classList.add('selected');
        this.highlightRelated();
    }

    highlightRelated() {
        if (!this.selectedCell) return;
        const { row, col } = this.selectedCell;
        const val = this.board[row][col];

        document.querySelectorAll('.cell').forEach(cell => {
            cell.classList.remove('highlighted');
            cell.classList.remove('selected');
        });

        // Highlight same row, column, box, and same value
        document.querySelectorAll('.cell').forEach(cell => {
            const r = parseInt(cell.dataset.row);
            const c = parseInt(cell.dataset.col);

            if (r === row || c === col) {
                cell.classList.add('highlighted');
            }

            if (Math.floor(r/3) === Math.floor(row/3) && Math.floor(c/3) === Math.floor(col/3)) {
                cell.classList.add('highlighted');
            }

            if (val !== 0 && this.board[r][c] === val) {
                cell.classList.add('highlighted');
            }
        });

        this.getCellElement(row, col).classList.add('selected');
    }

    getCellElement(row, col) {
        return document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
    }

    handleKeydown(e) {
        if (!this.selectedCell) return;

        const { row, col } = this.selectedCell;

        if (e.key >= '1' && e.key <= '9') {
            const num = parseInt(e.key);
            this.board[row][col] = num;
            this.render();
            this.checkComplete();
        } else if (e.key === 'Delete' || e.key === 'Backspace') {
            this.board[row][col] = 0;
            this.render();
        }
    }

    isValidCell(row, col) {
        if (this.board[row][col] === 0) return true;
        return this.isValid(this.board, row, col, this.board[row][col]);
    }

    checkSolution() {
        let hasErrors = false;

        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                if (this.original[i][j] === 0 && this.board[i][j] !== 0) {
                    const cell = this.getCellElement(i, j);
                    if (!this.isValidCell(i, j)) {
                        cell.classList.add('error');
                        hasErrors = true;
                    } else {
                        cell.classList.remove('error');
                    }
                }
            }
        }

        if (!hasErrors && this.isComplete()) {
            this.showModal('恭喜你 🎉', '数独解答正确！');
        } else if (hasErrors) {
            this.showModal('有错误哦 ⚠️', '红色格子有冲突，请检查后修改');
        } else {
            this.showModal('继续努力 💪', '目前没有错误，继续加油！');
        }
    }

    isComplete() {
        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                if (this.board[i][j] === 0) return false;
            }
        }
        return true;
    }

    checkComplete() {
        if (this.isComplete()) {
            // Check if all correct
            let allCorrect = true;
            for (let i = 0; i < 9; i++) {
                for (let j = 0; j < 9; j++) {
                    if (this.original[i][j] === 0 && !this.isValidCell(i, j)) {
                        allCorrect = false;
                        break;
                    }
                }
                if (!allCorrect) break;
            }

            if (allCorrect) {
                setTimeout(() => {
                    this.showModal('恭喜你 🎉', '数独完成！');
                }, 300);
            }
        }
    }

    giveHint() {
        if (!this.selectedCell) {
            // Find first empty cell
            for (let i = 0; i < 9; i++) {
                for (let j = 0; j < 9; j++) {
                    if (this.board[i][j] === 0) {
                        this.selectedCell = { row: i, col: j };
                        break;
                    }
                }
                if (this.selectedCell) break;
            }
        }

        if (!this.selectedCell) return;

        // We need to find the solution to get the correct value
        const solution = this.board.map(row => [...row]);
        this.solve(solution);
        const { row, col } = this.selectedCell;
        this.board[row][col] = solution[row][col];
        this.render();
        this.checkComplete();
    }

    isComplete() {
        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                if (this.board[i][j] === 0) return false;
            }
        }
        return true;
    }

    showModal(title, message) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalMessage').textContent = message;
        document.getElementById('messageModal').classList.remove('hidden');
    }

    hideModal() {
        document.getElementById('messageModal').classList.add('hidden');
    }
}

// Initialize game when DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    window.game = new SudokuGame();
});
