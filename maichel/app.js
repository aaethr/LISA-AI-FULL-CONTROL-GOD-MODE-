// API paths - using relative paths to ensure it works on any IP/localhost
const API_BASE = '/api/v1';

// Global elements
let terminalLog, statusBadge, commandInput, micBtn, lisaFrame, speechBubble;
let systemHistoryLoaded = false;
let modelSetupNoticeShown = false;
let conversationHistory = [];

function addLog(msg, type = 'info') {
    if (!terminalLog)             console.log(`[${type}] ${msg}`);
            return;
    }
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
    terminalLog.appendChild(entry);
    terminalLog.scrollTop = terminalLog.scrollHeight;
}

// --- Activation Logic ---
function startLisaSystem() {
    const overlay = document.getElementById('start-overlay');
    if (overlay) overlay.classList.add('hidden');

    // Keep microphone access opt-in; text chat remains available by default.
    if (!recognition) setupSpeech();
    speak("ลิซ่าพร้อมแล้วค่ะ");
}

// --- Initialize Components ---
function init() {
    terminalLog = document.getElementById('terminal-log');
    statusBadge = document.getElementById('backend-status');
    commandInput = document.getElementById('command-input');
    micBtn = document.getElementById('mic-btn');
    lisaFrame = document.querySelector('.lisa-avatar-frame');
    speechBubble = document.getElementById('speech-bubble');

    addLog('Lisa UI Initializing...', 'info');

    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = updateThaiVoiceStatus;
        updateThaiVoiceStatus();
    } else {
        addLog('This browser does not support speech playback.', 'error');
    }

    // Start status heartbeats
    setInterval(checkStatus, 3000);
    checkStatus();

    // Setup speech
    setupSpeech();
}

window.addEventListener('load', init); // Use load to ensure all assets are ready

// --- Status & Connectivity ---
let backendOnline = false;
async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (response.ok) {
            const data = await response.json();
            if (!backendOnline) {
                addLog('Backend connected. LISA is ready.', 'success');
                backendOnline = true;
            }
            statusBadge.innerText = data.local_model_configured
                ? 'ONLINE - READY'
                : 'ONLINE - SET UP LOCAL AI';
            statusBadge.classList.add('online');
            if (!data.local_model_configured && !modelSetupNoticeShown) {
                addLog(
                    'ตั้งค่า LISA_OLLAMA_BASE_URL และ LISA_AI_MODEL พร้อมเปิด Ollama ในเครื่องก่อนใช้แชตค่ะ',
                    'warning'
                );
                modelSetupNoticeShown = true;
            }
            if (!systemHistoryLoaded) {
                systemHistoryLoaded = true;
                loadSystemHistory().catch(error => {
                    systemHistoryLoaded = false;
                    addLog(`โหลดประวัติสุขภาพไม่สำเร็จ: ${error.message}`, 'error');
                });
            }
        } else {
            throw new Error(`Status ${response.status}`);
        }
    } catch (err) {
        if (backendOnline) {
            addLog(`Backend Disconnected: ${err.message}`, 'error');
            backendOnline = false;
        }
        statusBadge.innerText = 'OFFLINE';
        statusBadge.classList.remove('online');
    }
}

// --- Speech & AI Voice ---
let recognition;
let micActive = false;
let thaiVoiceStatus = '';

function getThaiVoice() {
    const voices = window.speechSynthesis.getVoices();
    const thaiVoices = voices.filter(voice => {
        const locale = (voice.lang || '').replace(/_/g, '-').toLowerCase();
        return locale.startsWith('th');
    });
    return thaiVoices.find(voice =>
        (voice.lang || '').replace(/_/g, '-').toLowerCase() === 'th-th'
    ) || thaiVoices[0] || null;
}

function updateThaiVoiceStatus() {
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return;

    const voice = getThaiVoice();
    const message = voice
        ? `พร้อมใช้เสียงภาษาไทย: ${voice.name}`
        : 'ไม่พบเสียงพูดภาษาไทย โปรดติดตั้งหรือเปิดใช้เสียงไทยในการตั้งค่าเบราว์เซอร์หรือ Windows';
    const type = voice ? 'success' : 'error';
    if (message !== thaiVoiceStatus) {
        addLog(message, type);
        thaiVoiceStatus = message;
    }
}

function setupSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        addLog('CRITICAL: Speech Recognition not supported.', 'error');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'th-TH';

    recognition.onstart = () => {
        addLog('Microphone is now LIVE.', 'success');
        micActive = true;
        micBtn.classList.add('active');
    };

    recognition.onerror = (event) => {
        addLog(`Mic Error: ${event.error}`, 'error');
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            addLog('กรุณาอนุญาตการใช้ไมโครโฟนในเบราว์เซอร์', 'error');
        } else if (event.error === 'network') {
            addLog('บริการรู้จำเสียงเชื่อมต่อไม่ได้ ลองตรวจเครือข่ายหรือพิมพ์ข้อความแทนค่ะ', 'error');
        }
        if (['not-allowed', 'service-not-allowed', 'audio-capture', 'network'].includes(event.error)) {
            micActive = false;
            micBtn.classList.remove('active');
        }
    };

    recognition.onend = () => {
        if (!micActive) {
            addLog('Microphone stopped.', 'info');
            return;
        }

        addLog('Mic stopped. Restarting...', 'info');
        try {
            recognition.start();
        } catch (error) {
            micActive = false;
            micBtn.classList.remove('active');
            addLog(`Could not restart microphone: ${error.message}`, 'error');
        }
    };

    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.trim();
        addLog(`HEARD: "${transcript}"`, 'success');

        const text = transcript.toLowerCase();
        if (text.includes('lisa') || text.includes('leesa') ||
            text.includes('ลิซ่า') || text.includes('ลีซ่า') ||
            text.includes('ลิซา') || text.includes('ลีซา') ||
            text.includes('लिसा') || text.includes('लीसा')) {
            const cmd = text.replace(/lisa|leesa|ลิซ่า|ลีซ่า|ลิซา|ลีซา|लिसा|लीसा/gi, '').trim();
            if (cmd) {
                processCommand(cmd);
            } else {
                speak("ฟังอยู่ค่ะ");
            }
        }
    };

    addLog('Speech system ready. Click Mic to start.', 'info');
}

function speak(msg) {
    if (!msg) return;
    if (!window.speechSynthesis) {
        addLog(`LISA: "${msg}"`, 'info');
        addLog('This browser does not support speech playback.', 'error');
        return;
    }
    window.speechSynthesis.cancel();
    addLog(`LISA: "${msg}"`, 'info');
    const utterance = new SpeechSynthesisUtterance(msg);
    utterance.volume = 1;
    utterance.pitch = 1.0;
    utterance.rate = 1.0;
    utterance.lang = 'th-TH';

    const voice = getThaiVoice();
    if (!voice) {
        updateThaiVoiceStatus();
        if (!window.speechSynthesis.getVoices().length) {
            addLog('กำลังโหลดรายการเสียงภาษาไทย ลองพูดอีกครั้งในอีกสักครู่ค่ะ', 'info');
        }
        return;
    }
    utterance.voice = voice;

    utterance.onstart = () => {
        if (lisaFrame) lisaFrame.classList.add('talking');
        if (speechBubble) {
            speechBubble.textContent = msg;
            speechBubble.classList.add('show');
        }
    };

    utterance.onend = () => {
        if (lisaFrame) lisaFrame.classList.remove('talking');
        if (speechBubble) setTimeout(() => speechBubble.classList.remove('show'), 2000);
    };

    window.speechSynthesis.speak(utterance);
}

// --- Command Processing ---
async function processCommand(text) {
    const command = text.trim();
    const lowered = command.toLocaleLowerCase();
    if (lowered === '/skills' || lowered === 'ทักษะ' || lowered === 'ดูทักษะ') {
        await loadSkills();
        return;
    }

    const rememberPrefix = ['/remember ', 'จำไว้ ', 'จดจำ '].find(prefix =>
        lowered.startsWith(prefix.toLocaleLowerCase())
    );
    if (rememberPrefix) {
        const note = command.slice(rememberPrefix.length).trim();
        if (!note) {
            addLog('ระบุข้อความหลังคำสั่งจำไว้ก่อนค่ะ', 'warning');
            return;
        }
        await previewMutation('memory_create', { text: note });
        return;
    }

    const recallPrefix = ['/recall ', 'ค้นความจำ '].find(prefix =>
        lowered.startsWith(prefix.toLocaleLowerCase())
    );
    if (recallPrefix) {
        await searchMemory(command.slice(recallPrefix.length).trim());
        return;
    }

    addLog(`Parsing command: "${text}"`, 'info');

    try {
        const parseResp = await fetch(`${API_BASE}/parse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (!parseResp.ok) throw new Error(`Parse failed: ${parseResp.status}`);

        const result = await parseResp.json();
        addLog(`Intent: ${result.intent} (Conf: ${result.confidence.toFixed(2)})`, 'info');

        if (result.intent === 'system_check') {
            await loadSystemReport(true, result.response);
            return;
        }

        if (result.intent === 'chat') {
            const assistantResp = await fetch(`${API_BASE}/assistant`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    history: conversationHistory.slice(-10)
                })
            });
            const assistantResult = await assistantResp.json();
            if (!assistantResp.ok) {
                throw new Error(assistantResult.detail || `Assistant request failed: ${assistantResp.status}`);
            }
            speak(assistantResult.response);
            conversationHistory.push(
                { role: 'user', content: text },
                { role: 'assistant', content: assistantResult.response }
            );
            conversationHistory = conversationHistory.slice(-10);
            return;
        }

        // Speak the response from AI
        speak(result.response);

        // Execute if it's a control intent
        const controls = ['system_lock', 'app_open', 'app_close', 'volume', 'brightness', 'settings'];
        if (controls.includes(result.intent)) {
            let action = result.intent;
            if (action === 'system_lock') action = 'lock';
            if (action === 'app_open') action = 'launch_app';

            executeControl(action, result.entities);
        }
    } catch (err) {
        addLog(`Request failed: ${err.message}`, 'error');
    }
}

async function loadSystemReport(announce = false, responseMessage = '') {
    const scanButton = document.getElementById('scan-system-btn');
    if (scanButton) scanButton.disabled = true;

    try {
        addLog('กำลังอ่านข้อมูลฮาร์ดแวร์และประเมินสุขภาพเครื่อง...', 'info');
        const response = await fetch(`${API_BASE}/system/report`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || `System report failed: ${response.status}`);
        }

        renderSystemReport(data.report);
        addLog('ตรวจเครื่องเสร็จแล้ว: บันทึกข้อมูลไว้ในเครื่องนี้', 'success');
        for (const finding of data.report.findings || []) {
            addLog(`${finding.message} — ${finding.recommendation}`, finding.severity === 'critical' ? 'error' : 'warning');
        }
        for (const warning of data.report.collection_warnings || []) {
            addLog(warning, 'warning');
        }
        try {
            await loadSystemHistory();
        } catch (error) {
            addLog(`โหลดประวัติสุขภาพไม่สำเร็จ: ${error.message}`, 'error');
        }
        if (announce) speak(responseMessage || 'ตรวจสุขภาพเครื่องเรียบร้อยแล้วค่ะ');
        return true;
    } catch (error) {
        addLog(`ตรวจเครื่องไม่สำเร็จ: ${error.message}`, 'error');
        const healthStatus = document.getElementById('health-status');
        if (healthStatus) healthStatus.textContent = 'ตรวจไม่สำเร็จ';
        return false;
    } finally {
        if (scanButton) scanButton.disabled = false;
    }
}

function renderSystemReport(report) {
    const score = document.getElementById('health-score');
    const ring = document.getElementById('health-ring');
    const status = document.getElementById('health-status');
    const checked = document.getElementById('last-checked');
    if (score) score.textContent = report.health_score;
    if (ring) ring.style.setProperty('--score-level', `${report.health_score}%`);
    if (status) {
        status.textContent = {
            healthy: 'สถานะปกติ',
            warning: 'ควรตรวจสอบ',
            attention: 'ต้องดูแล'
        }[report.status] || 'ประเมินแล้ว';
    }
    if (checked) {
        const measuredAt = new Date(report.measured_at);
        checked.textContent = `ตรวจล่าสุด ${measuredAt.toLocaleString('th-TH')}`;
    }

    document.getElementById('cpu-name').textContent = report.cpu.name;
    document.getElementById('cpu-value').textContent = `${report.cpu.usage_percent}%`;
    document.getElementById('ram-detail').textContent = `${report.ram.used_gb} / ${report.ram.total_gb} GB`;
    document.getElementById('ram-value').textContent = `${report.ram.usage_percent}%`;
    document.getElementById('disk-detail').textContent = `${report.system_drive.free_gb} GB ว่าง`;
    document.getElementById('disk-value').textContent = `${report.system_drive.free_percent}%`;
    document.getElementById('gpu-name').textContent = report.gpu.name;
}

async function loadSystemHistory() {
    const response = await fetch(`${API_BASE}/system/history?days=30`);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || `System history failed: ${response.status}`);
    }

    const chart = document.getElementById('health-history');
    if (!chart) return;
    chart.replaceChildren();
    const reports = (data.reports || []).slice(-14);
    if (!reports.length) {
        await loadSystemReport();
        return;
    }

    renderSystemReport(reports[reports.length - 1]);
    for (const report of reports) {
        const bar = document.createElement('span');
        bar.className = 'trend-bar';
        bar.style.setProperty('--bar-height', `${Math.max(8, report.health_score)}%`);
        bar.title = `${report.measured_at.slice(0, 10)}: ${report.health_score}/100`;
        chart.appendChild(bar);
    }
}

async function executeControl(action, params = {}) {
    return previewMutation(action, params);
}

let pendingPreviewId = null;
async function previewMutation(action, params = {}) {
    addLog(`Preparing action preview: ${action}`, 'info');
    try {
        const response = await fetch(`${API_BASE}/actions/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, params })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Preview failed: ${response.status}`);
        pendingPreviewId = data.preview_id;
        const dialog = document.getElementById('action-confirm');
        document.getElementById('action-description').textContent = data.description;
        document.getElementById('action-description').dataset.action = action;
        dialog.showModal();
    } catch (err) {
        addLog(`Action blocked: ${err.message}`, 'error');
    }
}

async function approvePendingAction() {
    if (!pendingPreviewId) return;
    let refreshMemory = false;
    try {
        const approve = await fetch(`${API_BASE}/actions/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preview_id: pendingPreviewId })
        });
        const approval = await approve.json();
        if (!approve.ok) throw new Error(approval.detail || 'Approval failed');
        const execute = await fetch(`${API_BASE}/actions/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preview_id: pendingPreviewId })
        });
        const result = await execute.json();
        if (!execute.ok) throw new Error(result.detail || 'Execution failed');
        addLog(
            `Approved result: ${result.message}`,
            result.status === 'success' ? 'success' : 'warning'
        );
        const action = document.getElementById('action-description').dataset.action;
        refreshMemory = ['memory_create', 'memory_edit', 'memory_delete'].includes(action);
    } catch (error) {
        addLog(`Approved action failed: ${error.message}`, 'error');
    } finally {
        pendingPreviewId = null;
        document.getElementById('action-confirm').close();
    }
    if (refreshMemory) await loadMemory(true);
}

function cancelPendingAction() {
    pendingPreviewId = null;
    addLog('Action cancelled. Nothing changed.', 'info');
    document.getElementById('action-confirm').close();
}

async function loadSkills() {
    try {
        const response = await fetch(`${API_BASE}/skills`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not load skills');
        addLog(data.skills.map(skill =>
            `${skill.name}: ${skill.permissions.join(', ')}${skill.mutates ? ' (approval required)' : ''}`
        ).join(' | '), 'info');
    } catch (error) {
        addLog(`โหลด Skills ไม่สำเร็จ: ${error.message}`, 'error');
    }
}

async function loadMemory(openDialog = true) {
    try {
        const response = await fetch(`${API_BASE}/memory`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not load memories');
        const list = document.getElementById('memory-list');
        list.replaceChildren();
        if (!data.memories.length) {
            const empty = document.createElement('p');
            empty.className = 'memory-empty';
            empty.textContent = 'ยังไม่มีความจำที่บันทึกไว้';
            list.appendChild(empty);
        }
        for (const memory of data.memories) {
            const item = document.createElement('article');
            item.className = 'memory-item';
            const content = document.createElement('p');
            content.textContent = memory.text;
            const actions = document.createElement('div');
            actions.className = 'memory-actions';
            const edit = document.createElement('button');
            edit.type = 'button';
            edit.textContent = 'แก้ไข';
            edit.addEventListener('click', () => editMemory(memory));
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.textContent = 'ลบ';
            remove.addEventListener('click', () => deleteMemory(memory));
            actions.append(edit, remove);
            item.append(content, actions);
            list.appendChild(item);
        }
        if (openDialog) document.getElementById('memory-manager').showModal();
    } catch (error) {
        addLog(`โหลดความจำไม่สำเร็จ: ${error.message}`, 'error');
    }
}

async function searchMemory(query) {
    if (!query) {
        addLog('ระบุคำค้นความจำก่อนค่ะ', 'warning');
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/memory/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not search memories');
        const matches = data.matches || [];
        if (!matches.length) {
            speak('ไม่พบความจำที่ตรงกับคำค้นค่ะ');
            return;
        }
        speak(`พบความจำ ${matches.length} รายการค่ะ`);
        for (const match of matches) addLog(`Memory: ${match}`, 'info');
    } catch (error) {
        addLog(`ค้นความจำไม่สำเร็จ: ${error.message}`, 'error');
    }
}

async function saveMemoryFromPrompt() {
    const text = window.prompt('ข้อความที่ต้องการบันทึกเป็นความจำ (ต้องได้รับอนุมัติก่อน)');
    if (text && text.trim()) {
        document.getElementById('memory-manager').close();
        await previewMutation('memory_create', { text: text.trim() });
    }
}

async function editMemory(memory) {
    const text = window.prompt('แก้ไขข้อความความจำ', memory.text);
    if (text && text.trim()) {
        document.getElementById('memory-manager').close();
        await previewMutation('memory_edit', { id: memory.id, text: text.trim() });
    }
}

async function deleteMemory(memory) {
    document.getElementById('memory-manager').close();
    await previewMutation('memory_delete', { id: memory.id });
}

function handleInput() {
    const input = document.getElementById('command-input');
    const text = input.value.trim();
    if (!text) return;
    addLog(`Input: ${text}`, 'user');
    processCommand(text);
    input.value = '';
}

function toggleVoice() {
    if (!recognition) {
        setupSpeech();
        if (!recognition) return;
    }

    if (micActive) {
        micActive = false;
        recognition.stop();
        micBtn.classList.remove('active');
        addLog('Mic Turned OFF.', 'info');
    } else {
        try {
            recognition.start();
            speak("เปิดระบบเสียงแล้วค่ะ");
        } catch (e) {
            addLog(`Could not start mic: ${e.message}`, 'error');
        }
    }
}

function stopLisa() {
    window.speechSynthesis.cancel();
    addLog('EMERGENCY STOP CALLED', 'error');
}

// Key listeners
document.addEventListener('keydown', (e) => {
    if (e.key === 'F9') stopLisa();
    if (e.key === 'Enter' && document.activeElement.id === 'command-input') handleInput();
});
