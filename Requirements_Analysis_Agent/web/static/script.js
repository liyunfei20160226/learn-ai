document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('generator-form');
    const startBtn = document.getElementById('start-btn');
    const logContainer = document.getElementById('log-container');
    const resultSection = document.getElementById('result-section');
    const resultFiles = document.getElementById('result-files');
    const elapsedTimeEl = document.getElementById('elapsed-time');
    const elapsedValueEl = document.getElementById('elapsed-value');
    const questionSection = document.getElementById('question-section');
    const questionsContainer = document.getElementById('questions-container');
    const submitAnswersBtn = document.getElementById('submit-answers-btn');

    let currentTaskId = null;
    let eventSource = null;
    let timerInterval = null;
    let startTime = null;
    let currentQuestions = [];

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
        const maxRetries = 30; // 最多重试 30 次，每次等待 1 秒后重试

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
                // Server sends all lines every connection, so we just drop the ones we already have
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
                } else if (data.status === 'waiting_for_answer' && retryCount < maxRetries) {
                    retryCount++;
                    // Still waiting for answer, reconnect after a short delay
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

            // Check if task is waiting for user answers
            if (data.status === 'waiting_for_answer') {
                // Keep start button disabled until task completes
                startBtn.disabled = true;
                stopTimer();
                loadPendingQuestions(taskId);
                return;
            }

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

    // Load pending questions for interactive mode
    async function loadPendingQuestions(taskId) {
        try {
            const response = await fetch(`/api/questions/${taskId}`);
            const data = await response.json();
            currentQuestions = data.pending_questions || [];

            if (currentQuestions.length > 0) {
                questionSection.style.display = 'block';
                questionsContainer.innerHTML = '';
                // Re-enable submit button for new round of questions
                submitAnswersBtn.disabled = false;

                currentQuestions.forEach((q, index) => {
                    const questionDiv = document.createElement('div');
                    questionDiv.className = 'question-item';
                    questionDiv.innerHTML = `
                        <div class="question-text">${index + 1}. ${q.question}</div>
                        <div class="ai-answer"><strong>AI建议回答:</strong> ${q.ai_answer}</div>
                        <div class="question-choice">
                            <label class="choice-option">
                                <input type="radio" name="choice-${index}" value="ai" checked>
                                使用 AI 建议回答
                            </label>
                            <label class="choice-option">
                                <input type="radio" name="choice-${index}" value="custom">
                                我自己回答
                            </label>
                        </div>
                        <div class="user-answer-container" id="user-answer-container-${index}" style="display: none;">
                            <textarea placeholder="请输入你的回答"></textarea>
                        </div>
                    `;
                    questionsContainer.appendChild(questionDiv);

                    // Toggle user answer textarea visibility based on choice
                    questionDiv.querySelectorAll(`input[name="choice-${index}"]`).forEach(radio => {
                        radio.addEventListener('change', function() {
                            const container = document.getElementById(`user-answer-container-${index}`);
                            container.style.display = this.value === 'custom' ? 'block' : 'none';
                        });
                    });
                });
            }
        } catch (error) {
            console.error('Failed to load questions:', error);
            addLogLine('❌ 加载问题失败: ' + error.message);
        }
    }

    // Submit user answers
    async function submitAnswers() {
        if (!currentTaskId) return;

        const answers = [];
        currentQuestions.forEach((q, index) => {
            const choice = document.querySelector(`input[name="choice-${index}"]:checked`).value;
            const userAnswerEl = document.querySelector(`#user-answer-container-${index} textarea`);
            const userAnswer = userAnswerEl ? userAnswerEl.value.trim() : '';
            answers.push({
                question: q.question,
                choice: choice,
                answer: choice === 'ai' ? q.ai_answer : (userAnswer || q.ai_answer)
            });
        });

        try {
            submitAnswersBtn.disabled = true;
            const response = await fetch(`/api/answer/${currentTaskId}`, {
                method: 'POST',
                body: new URLSearchParams({
                    ...Object.fromEntries(answers.map((a, i) => [`answers[${i}][question]`, a.question])),
                ...Object.fromEntries(answers.map((a, i) => [`answers[${i}][choice]`, a.choice])),
                ...Object.fromEntries(answers.map((a, i) => [`answers[${i}][answer]`, a.answer])),
                }),
            });
            const result = await response.json();

            if (result.success) {
                questionSection.style.display = 'none';
                addLogLine('✅ 回答已提交，继续生成...');
                // Reconnect SSE to continue getting logs
                connectSSE(currentTaskId);
            } else {
                addLogLine('❌ 提交回答失败: ' + (result.error || 'Unknown error'));
                submitAnswersBtn.disabled = false;
            }
        } catch (error) {
            addLogLine('❌ 提交回答失败: ' + error.message);
            submitAnswersBtn.disabled = false;
        }
    }

    // Bind submit button click
    submitAnswersBtn.addEventListener('click', submitAnswers);

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
