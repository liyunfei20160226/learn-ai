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

            if (!data.task_id) {
                throw new Error(data.error || '启动任务失败');
            }

            currentTaskId = data.task_id;

            // Update URL hash for refresh recovery
            window.location.hash = `#task=${currentTaskId}`;

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
        // Remember current log count to avoid repeating logs when reconnecting
        let lastIndex = logContainer.children.length;
        let retryCount = 0;
        const maxRetries = 30; // 最多重试 30 次

        eventSource.onmessage = function(event) {
            const data = event.data;
            // Reset retry count on successful message
            retryCount = 0;
            if (data.startsWith('[DONE]')) {
                // Connection done
                eventSource.close();
                checkStatus(taskId);
                return;
            }
            // Only add new logs that haven't been displayed yet
            if (lastIndex > 0) {
                // Skip the first N lines that are already displayed
                lastIndex--;
            } else {
                addLogLine(data);
            }
        };

        eventSource.onerror = function(error) {
            eventSource.close();
            // Check if task is still running, if yes, auto-reconnect
            fetch(`/api/status/${taskId}`).then(response => response.json()).then(data => {
                const isStillRunning = data.status === 'running';
                if (isStillRunning && retryCount < maxRetries) {
                    retryCount++;
                    addLogLine(`⚠️ 连接中断，正在重连 (${retryCount}/${maxRetries})...`);
                    setTimeout(() => {
                        connectSSE(taskId);
                    }, 1000);
                } else {
                    addLogLine('⚠️ 连接中断，停止重连');
                    startBtn.disabled = false;
                    stopTimer();
                }
            }).catch(() => {
                addLogLine('⚠️ 连接中断，无法检查任务状态，停止重连');
                startBtn.disabled = false;
                stopTimer();
            });
        };
    }

    // Check final status and show download links
    async function checkStatus(taskId) {
        try {
            const response = await fetch(`/api/status/${taskId}`);
            const data = await response.json();

            startBtn.disabled = false;
            stopTimer();

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
            startBtn.disabled = false;
            stopTimer();
        }
    }

    // Check URL for existing task (for page refresh recovery)
    function checkUrlForExistingTask() {
        const hash = window.location.hash;
        const match = hash.match(/^#task=([a-f0-9]{8})$/);
        if (match) {
            const taskId = match[1];
            // If we already have this task connected, do nothing
            if (currentTaskId === taskId && eventSource) {
                return;
            }
            currentTaskId = taskId;
            // Clear previous logs
            clearLogs();
            startBtn.disabled = true;
            startTimer();
            // Check task status and connect
            connectSSE(taskId);
        }
    }

    // When hash changes
    window.addEventListener('hashchange', () => {
        checkUrlForExistingTask();
    });

    // On page load, check for existing task
    checkUrlForExistingTask();
});
