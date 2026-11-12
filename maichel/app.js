// API paths - using relative paths to ensure it works on any IP/localhost
const API_BASE = '/api/v1';

// Global elements
let terminalLog, statusBadge, commandInput, micBtn, lisaFrame, speechBubble;

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

    // Initialize speech system with a real gesture
    if (!recognition) setupSpeech();
    speak("Lisa AI Activated. System God Mode online.");

    // Attempt to start mic
    if (recognition) {
        try { recognition.start(); } catch (e) { console.error(e); }
    }
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
                addLog('Backend Connected! God Mode Active.', 'success');
                backendOnline = true;
            }
            statusBadge.innerText = 'ONLINE - GOD MODE';
            statusBadge.classList.add('online');
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

function setupSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        addLog('CRITICAL: Speech Recognition not supported.', 'error');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'hi-IN';

    recognition.onstart = () => {
        addLog('Microphone is now LIVE.', 'success');
        micActive = true;
        micBtn.classList.add('active');
    };

    recognition.onerror = (event) => {
        addLog(`Mic Error: ${event.error}`, 'error');
        if (event.error === 'not-allowed') {
            addLog('Please CLICK the page and allow Mic access.', 'error');
            micActive = false;
            micBtn.classList.remove('active');
        }
    };

    recognition.onend = () => {
        addLog('Mic stopped. Restarting...', 'info');
        if (micActive) {
            try { recognition.start(); } catch (e) { }
        }
    };

    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.trim();
        addLog(`HEARD: "${transcript}"`, 'success');

        const text = transcript.toLowerCase();
        if (text.includes('lisa') || text.includes('leesa') || text.includes('लिसा') || text.includes('लीसा')) {
            const cmd = text.replace(/lisa|leesa|लिसा|लीसा/gi, '').trim();
            if (cmd) {
                processCommand(cmd);
            } else {
                speak("Ji Admin, main sun rahi hoon.");
            }
        }
    };

    addLog('Speech system ready. Click Mic to start.', 'info');
}

function speak(msg) {
    if (!msg) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(msg);
    utterance.volume = 1;
    utterance.pitch = 1.3;
    utterance.rate = 1.0;
    utterance.lang = 'hi-IN';

    // Get female/hindi voice
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.lang.includes('hi')) || voices.find(v => v.name.includes('Female'));
    if (voice) utterance.voice = voice;

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
    addLog(`LISA: "${msg}"`, 'info');
}

// --- Command Processing ---
async function processCommand(text) {
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

        // Speak the response from AI
        speak(result.response);

        // Execute if it's a control intent
        const controls = ['system_lock', 'app_open', 'app_close', 'volume', 'brightness', 'settings', 'terminal_command'];
        if (controls.includes(result.intent)) {
            let action = result.intent;
            if (action === 'system_lock') action = 'lock';
            if (action === 'app_open') action = 'launch_app';
            if (action === 'terminal_command') action = 'terminal';

            executeControl(action, result.entities);
        }
    } catch (err) {
        addLog(`CRITICAL: ${err.message}`, 'error');
        // Manual fallbacks
        if (text.includes('lock')) executeControl('lock');
    }
}

async function executeControl(action, params = {}) {
    addLog(`Executing Action: ${action}`, 'info');
    try {
        const response = await fetch(`${API_BASE}/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, params })
        });

        if (!response.ok) throw new Error(`Control failed: ${response.status}`);

        const data = await response.json();
        addLog(`Result: ${data.message || 'Success'}`, 'success');
    } catch (err) {
        addLog(`Execution Error: ${err.message}`, 'error');
    }
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
    }

    if (micActive) {
        micActive = false;
        recognition.stop();
        micBtn.classList.remove('active');
        addLog('Mic Turned OFF.', 'info');
    } else {
        try {
            recognition.start();
            speak("Voice system activated.");
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
