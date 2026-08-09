document.addEventListener('DOMContentLoaded', () => {
    const taskForm = document.getElementById('task-form');
    const taskInput = document.getElementById('task-input');
    const actionSelect = document.getElementById('action-select');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    const apiUrlInput = document.getElementById('api-url-input');
    const healthStatus = document.getElementById('health-status');

    const executionBadge = document.getElementById('execution-badge');
    const codeOutput = document.getElementById('code-output');
    const reportOutput = document.getElementById('report-output');
    const summaryOutput = document.getElementById('summary-output');

    const stepTask = document.getElementById('step-task');
    const stepDev = document.getElementById('step-dev');
    const stepTest = document.getElementById('step-test');
    const stepManager = document.getElementById('step-manager');
    const stepArchive = document.getElementById('step-archive');

    const steps = [stepTask, stepDev, stepTest, stepManager, stepArchive];

    function setStepState(activeIdx, completedUpToIdx) {
        steps.forEach((step, idx) => {
            step.classList.remove('active', 'completed');
            if (idx <= completedUpToIdx) {
                step.classList.add('completed');
            } else if (idx === activeIdx) {
                step.classList.add('active');
            }
        });
    }

    function getCleanBaseUrl() {
        let cleanBase = apiUrlInput.value.trim().replace(/\/$/, '');
        if (cleanBase.endsWith('/crew/invoke')) {
            cleanBase = cleanBase.replace(/\/crew\/invoke$/, '');
        } else if (cleanBase.endsWith('/crew')) {
            cleanBase = cleanBase.replace(/\/crew$/, '');
        }
        return cleanBase;
    }

    async function checkHealth() {
        const baseUrl = getCleanBaseUrl();
        try {
            const res = await fetch(`${baseUrl}/health`);
            if (res.ok) {
                healthStatus.classList.add('online');
                healthStatus.title = "Backend Online";
            } else {
                healthStatus.classList.remove('online');
                healthStatus.title = "Backend Unreachable";
            }
        } catch {
            healthStatus.classList.remove('online');
            healthStatus.title = "Backend Unreachable";
        }
    }

    // Periodically check health
    checkHealth();
    apiUrlInput.addEventListener('change', checkHealth);

    taskForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const task = taskInput.value.trim();
        const action = actionSelect.value;
        const baseUrl = getCleanBaseUrl();
        const invokeUrl = `${baseUrl}/crew/invoke`;

        if (!task) return;

        // UI Reset & Loading State
        submitBtn.disabled = true;
        btnText.textContent = "Crew Running...";
        btnSpinner.classList.remove('hidden');

        executionBadge.className = 'badge running';
        executionBadge.textContent = 'Running Node Workflow';

        codeOutput.textContent = '# Generating Python solution via Developer Node...';
        reportOutput.textContent = '# Generating test cases and running code via Tester Node...';
        summaryOutput.innerHTML = '<p>LangGraph workflow execution in progress...</p>';

        setStepState(1, 0); // Task received, developer node active

        try {
            // Simulate progression visually
            const devTimer = setTimeout(() => setStepState(2, 1), 1200);
            const testTimer = setTimeout(() => setStepState(3, 2), 2400);

            console.log("Backend URL:", baseUrl);
            console.log("Invoke URL:", invokeUrl);
            console.log("Request body:", {
                input: {
                    task: task,
                    action: action
                }
            });

            const response = await fetch(invokeUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    input: {
                        task: task,
                        action: action
                    }
                })
            });

            console.log("Response status:", response.status);
            console.log("Response URL:", response.url);

            clearTimeout(devTimer);
            clearTimeout(testTimer);

            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: 'Unknown Server Error' }));
                throw new Error(errData.detail || `Server error ${response.status}`);
            }

            const rawData = await response.json();
            const data = rawData.output || rawData;

            // Populate Outputs
            codeOutput.textContent = data.generated_code || '# No code generated.';
            reportOutput.textContent = data.test_report || '# No report generated.';

            const isArchived = data.next_step === 'archiver' || data.status === 'completed';
            const actionText = action === 'another' ? 'Route to New Task Input' : 'Store & Finish Task';
            
            summaryOutput.innerHTML = `
                <p><strong>Status:</strong> <span style="color: #10B981;">${data.status}</span></p>
                <p><strong>Manager Decision:</strong> Action = "${action}" (${actionText})</p>
                <p><strong>Next Step:</strong> <code>${data.next_step}</code></p>
            `;

            if (isArchived) {
                setStepState(-1, 4); // All steps completed
            } else {
                setStepState(0, 3); // Routed back to task input
            }

            executionBadge.className = 'badge completed';
            executionBadge.textContent = isArchived ? 'Task Archived' : 'Awaiting Next Task';

        } catch (err) {
            executionBadge.className = 'badge idle';
            executionBadge.textContent = 'Error';
            summaryOutput.innerHTML = `<p style="color: #EF4444;"><strong>Execution Error:</strong> ${err.message}</p>`;
            setStepState(-1, -1);
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = "Execute Dev Crew Workflow";
            btnSpinner.classList.add('hidden');
        }
    });
});
