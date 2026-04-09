class SnakeGame {
    constructor() {
        // Game configuration
        this.gridSize = 20; // number of cells
        this.cellSize = 20; // pixels per cell
        this.speed = 150; // milliseconds per frame
        this.canvasSize = this.gridSize * this.cellSize;

        // Game state
        this.snake = [];
        this.food = {};
        this.direction = 'right';
        this.nextDirection = 'right';
        this.score = 0;
        this.gameLoop = null;
        this.isPlaying = false;

        // Get DOM elements
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.scoreElement = document.getElementById('score');
        this.overlay = document.getElementById('gameOverlay');
        this.overlayTitle = document.getElementById('overlayTitle');
        this.overlayMessage = document.getElementById('overlayMessage');
        this.startBtn = document.getElementById('startBtn');

        this.init();
    }

    init() {
        // Set canvas size
        this.canvas.width = this.canvasSize;
        this.canvas.height = this.canvasSize;

        // Bind events
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.startBtn.addEventListener('click', () => this.startGame());

        // Draw initial state
        this.drawGrid();
    }

    startGame() {
        // Reset game state
        this.resetGame();

        // Hide overlay
        this.overlay.classList.add('hidden');
        this.isPlaying = true;

        // Start game loop
        this.gameLoop = setInterval(() => this.update(), this.speed);
    }

    resetGame() {
        // Initialize snake in the middle with 3 segments
        this.snake = [
            { x: 10, y: 10 },
            { x: 9, y: 10 },
            { x: 8, y: 10 }
        ];
        this.direction = 'right';
        this.nextDirection = 'right';
        this.score = 0;
        this.updateScore();

        // Generate first food
        this.generateFood();
    }

    handleKeydown(event) {
        if (!this.isPlaying) return;

        const key = event.key;

        // Prevent reverse direction
        if (key === 'ArrowUp' && this.direction !== 'down') {
            this.nextDirection = 'up';
        } else if (key === 'ArrowDown' && this.direction !== 'up') {
            this.nextDirection = 'down';
        } else if (key === 'ArrowLeft' && this.direction !== 'right') {
            this.nextDirection = 'left';
        } else if (key === 'ArrowRight' && this.direction !== 'left') {
            this.nextDirection = 'right';
        }
    }

    update() {
        // Update direction
        this.direction = this.nextDirection;

        // Get new head position
        const head = this.snake[0];
        let newHead = { x: head.x, y: head.y };

        switch (this.direction) {
            case 'up':
                newHead.y--;
                break;
            case 'down':
                newHead.y++;
                break;
            case 'left':
                newHead.x--;
                break;
            case 'right':
                newHead.x++;
                break;
        }

        // Check collision with wall
        if (this.checkWallCollision(newHead)) {
            this.gameOver();
            return;
        }

        // Check collision with self
        if (this.checkSelfCollision(newHead)) {
            this.gameOver();
            return;
        }

        // Add new head
        this.snake.unshift(newHead);

        // Check if ate food
        if (newHead.x === this.food.x && newHead.y === this.food.y) {
            this.score++;
            this.updateScore();
            this.generateFood();
        } else {
            // Remove tail if didn't eat
            this.snake.pop();
        }

        // Redraw
        this.draw();
    }

    checkWallCollision(head) {
        return head.x < 0 || head.x >= this.gridSize ||
               head.y < 0 || head.y >= this.gridSize;
    }

    checkSelfCollision(head) {
        return this.snake.some(segment => segment.x === head.x && segment.y === head.y);
    }

    generateFood() {
        let newFood;
        // Keep generating until we get a position that's not on the snake
        do {
            newFood = {
                x: Math.floor(Math.random() * this.gridSize),
                y: Math.floor(Math.random() * this.gridSize)
            };
        } while (this.snake.some(segment => segment.x === newFood.x && segment.y === newFood.y));

        this.food = newFood;
    }

    gameOver() {
        this.isPlaying = false;
        clearInterval(this.gameLoop);

        // Show overlay with game over
        this.overlayTitle.textContent = '游戏结束';
        this.overlayMessage.textContent = `最终得分: ${this.score}`;
        this.overlay.classList.remove('hidden');
        this.startBtn.textContent = '再来一局';
    }

    updateScore() {
        this.scoreElement.textContent = this.score;
    }

    draw() {
        // Clear canvas
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
        this.ctx.fillRect(0, 0, this.canvasSize, this.canvasSize);

        this.drawGrid();
        this.drawFood();
        this.drawSnake();
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.05)';
        this.ctx.lineWidth = 1;

        for (let i = 0; i <= this.gridSize; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(i * this.cellSize, 0);
            this.ctx.lineTo(i * this.cellSize, this.canvasSize);
            this.ctx.stroke();

            this.ctx.beginPath();
            this.ctx.moveTo(0, i * this.cellSize);
            this.ctx.lineTo(this.canvasSize, i * this.cellSize);
            this.ctx.stroke();
        }
    }

    drawSnake() {
        this.snake.forEach((segment, index) => {
            if (index === 0) {
                // Head - darker color
                this.ctx.fillStyle = '#2f855a';
            } else {
                // Body - lighter color
                this.ctx.fillStyle = '#48bb78';
            }

            this.roundedRect(
                segment.x * this.cellSize + 1,
                segment.y * this.cellSize + 1,
                this.cellSize - 2,
                this.cellSize - 2,
                3
            );
            this.ctx.fill();
        });
    }

    drawFood() {
        this.ctx.fillStyle = '#f56565';
        const x = this.food.x * this.cellSize;
        const y = this.food.y * this.cellSize;
        const radius = this.cellSize / 2 - 2;

        this.ctx.beginPath();
        this.ctx.arc(
            x + this.cellSize / 2,
            y + this.cellSize / 2,
            radius,
            0,
            Math.PI * 2
        );
        this.ctx.fill();
    }

    // Helper for rounded rectangles
    roundedRect(x, y, width, height, radius) {
        this.ctx.beginPath();
        this.ctx.moveTo(x + radius, y);
        this.ctx.arcTo(x + width, y, x + width, y + height, radius);
        this.ctx.arcTo(x + width, y + height, x, y + height, radius);
        this.ctx.arcTo(x, y + height, x, y, radius);
        this.ctx.arcTo(x, y, x + width, y, radius);
        this.ctx.closePath();
    }
}

// Initialize game when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.game = new SnakeGame();
});
