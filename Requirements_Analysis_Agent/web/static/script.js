document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('generator-form');
    const startBtn = document.getElementById('start-btn');
    const logContainer = document.getElementById('log-container');
    const resultSection = document.getElementById('result-section');
    const resultFiles = document.getElementById('result-files');
    const elapsedTimeEl = document.getElementById('elapsed-time');
    const elapsedValueEl = document.getElementById('elapsed-value');

    let currentTaskId = null;
    let eventSource = null;
    let timerInterval = null;
    let startTime = null;

    // Add log line
    function addLogLine(message) {
        const line = document.createElement('div');
        line.className = 'log-line';

        if (message.includes('✅') || message.includes('完成')) {
            line.classList.add('log-success');
        } else if (message.includes('❌') || message.includes('错误')) {
            line.classList.add('log-error');
        } else if (message.includes('⚠️') || message.includes('警告')) {
            line.classList.add('log-warning');
        } else {
            line.classList.add('log-info');
        }

        line.textContent = message;
        logContainer.appendChild(line);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Clear logs
    function clearLogs() {
        logContainer.innerHTML = '';
        resultSection.style.display = 'none';
        resultFiles.innerHTML = '';
    }

    // Format elapsed time as MM:SS
    function formatElapsed(ms) {
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    // Start elapsed timer
    function startTimer() {
        startTime = Date.now();
        elapsedTimeEl.style.display = 'inline';
        timerInterval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            elapsedValueEl.textContent = formatElapsed(elapsed);
        }, 1000);
    }

    // Stop elapsed timer
    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    // Start task
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Clear previous
        clearLogs();
        stopTimer();
        startBtn.disabled = true;
        startTimer();

        // Get form data
        const formData = new FormData(form);

        try {
            // Start task
            const response = await fetch('/api/start', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            currentTaskId = data.task_id;

            // Connect SSE for logs
            connectSSE(currentTaskId);

        } catch (error) {
            addLogLine('❌ 启动任务失败: ' + error.message);
            startBtn.disabled = false;
            stopTimer();
        }
    });

    // Connect SSE
    function connectSSE(taskId) {
        eventSource = new EventSource(`/api/events/${taskId}`);

        eventSource.onmessage = function(event) {
            const data = event.data;
            if (data.startsWith('[DONE]')) {
                // Connection done
                eventSource.close();
                startBtn.disabled = false;
                stopTimer();
                checkStatus(taskId);
                return;
            }
            addLogLine(data);
        };

        eventSource.onerror = function(error) {
            addLogLine('⚠️ 连接中断');
            eventSource.close();
            startBtn.disabled = false;
            stopTimer();
        };
    }

    // Check final status and show download links
    async function checkStatus(taskId) {
        try {
            const response = await fetch(`/api/status/${taskId}`);
            const data = await response.json();

            if (data.output_files && data.output_files.length > 0) {
                resultSection.style.display = 'block';
                resultFiles.innerHTML = '';

                data.output_files.forEach(filename => {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'result-file';
                    fileDiv.innerHTML = `
                        <span class="result-file-name">${filename}</span>
                        <a href="/api/download/${taskId}/${filename}" class="download-btn" download>下载</a>
                    `;
                    resultFiles.appendChild(fileDiv);
                });
            }
        } catch (error) {
            console.error('Failed to get status:', error);
        }
    }
});
