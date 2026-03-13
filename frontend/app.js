/**
 * Iris — Frontend App (app.js)
 * WebSocket client, camera feed, mic recording, GPS capture, TTS playback.
 */

// ── Configuration ─────────────────────────────────────────────────────────────
const BACKEND_HOST = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `ws://${window.location.hostname}:8000`
  : `wss://${window.location.hostname}`;

const WS_URL = `${BACKEND_HOST}/ws`;

// User ID — in a real app this would come from Firebase Auth
const USER_ID = localStorage.getItem('iris_user_id') || _generateUserId();
localStorage.setItem('iris_user_id', USER_ID);

// Frame sampling
const FRAME_INTERVAL_IDLE   = 3000;   // ms between frames when idle
const FRAME_INTERVAL_ACTIVE = 800;    // ms between frames when recording

// ── State ─────────────────────────────────────────────────────────────────────
let ws = null;
let mediaStream = null;
let mediaRecorder = null;
let audioCtx = null;
let isRecording = false;
let isSpeaking = false;
let frameInterval = null;
let lastFrameData = null;
let currentGPS = { lat: null, lng: null };
let gpsWatchId = null;
let currentFacingMode = 'environment';  // 'environment' = rear, 'user' = front

// TTS state
let currentUtterance = null;
let ttsAutoHideTimer = null;

// ── DOM references ────────────────────────────────────────────────────────────
const cameraFeed     = document.getElementById('camera-feed');
const arCanvas       = document.getElementById('ar-canvas');
const textOverlay    = document.getElementById('text-overlay');
const overlaySummary = document.getElementById('overlay-summary');
const overlayDetail  = document.getElementById('overlay-detail');
const navOverlay     = document.getElementById('nav-overlay');
const navStep        = document.getElementById('nav-step');
const statusDot      = document.getElementById('status-dot');
const statusText     = document.getElementById('status-text');
const micBtn         = document.getElementById('mic-btn');
const micLabel       = document.getElementById('mic-label');
const interruptBtn   = document.getElementById('interrupt-btn');
const detailBtn      = document.getElementById('detail-btn');
const cameraFlipBtn  = document.getElementById('camera-flip-btn');
const gpsLabel       = document.getElementById('gps-label');
const textInput      = document.getElementById('text-input');
const sendBtn        = document.getElementById('send-btn');
const errorModal     = document.getElementById('error-modal');
const errorMessage   = document.getElementById('error-message');
const errorRetryBtn  = document.getElementById('error-retry-btn');

// Teleprompter DOM (injected dynamically)
let teleprompterEl = null;
let teleprompterInner = null;

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  AROverlay.init(arCanvas);
  await _startCamera();
  _startGPS();
  _connectWebSocket();
  _bindControls();
}

// ── Camera Setup ──────────────────────────────────────────────────────────────
async function _startCamera(facingMode = currentFacingMode) {
  try {
    // Stop any existing stream tracks first
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }

    const constraints = {
      video: {
        facingMode: { ideal: facingMode },
        width:  { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    };
    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    cameraFeed.srcObject = mediaStream;
    currentFacingMode = facingMode;

    // Start frame capture loop
    _startFrameCapture(FRAME_INTERVAL_IDLE);
  } catch (err) {
    console.error('Camera error:', err);
    _showError(
      'Camera Access Required',
      `Iris needs your camera to identify what you're looking at.\n\nError: ${err.message}`
    );
  }
}

// ── Camera Flip ───────────────────────────────────────────────────────────────
async function _flipCamera() {
  const nextMode = currentFacingMode === 'environment' ? 'user' : 'environment';

  // Animate button
  cameraFlipBtn.classList.add('flipping');
  cameraFlipBtn.disabled = true;

  await _startCamera(nextMode);

  // Reset animation after transition completes
  setTimeout(() => {
    cameraFlipBtn.classList.remove('flipping');
    cameraFlipBtn.disabled = false;
  }, 500);
}

// ── Frame Capture ─────────────────────────────────────────────────────────────
function _startFrameCapture(interval) {
  if (frameInterval) clearInterval(frameInterval);
  // Capture frames locally so we have a fresh one ready when user sends a query
  frameInterval = setInterval(_captureFrame, interval);
}

function _captureFrame() {
  if (!mediaStream) return;
  // We only STORE the frame locally — it gets attached when user speaks/types
  const offscreen = document.createElement('canvas');
  offscreen.width  = 640;
  offscreen.height = 360;
  const octx = offscreen.getContext('2d');
  octx.drawImage(cameraFeed, 0, 0, offscreen.width, offscreen.height);

  offscreen.toBlob(blob => {
    if (!blob) return;
    const reader = new FileReader();
    reader.onload = () => {
      lastFrameData = reader.result.split(',')[1];
    };
    reader.readAsDataURL(blob);
  }, 'image/jpeg', 0.6);
}

// ── GPS ───────────────────────────────────────────────────────────────────────
function _startGPS() {
  if (!navigator.geolocation) {
    gpsLabel.textContent = '📍 GPS: Not supported';
    return;
  }
  gpsWatchId = navigator.geolocation.watchPosition(
    pos => {
      currentGPS.lat = pos.coords.latitude;
      currentGPS.lng = pos.coords.longitude;
      gpsLabel.textContent = `📍 ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
      _wsSend({ type: 'gps', lat: currentGPS.lat, lng: currentGPS.lng });
    },
    err => {
      console.warn('GPS error:', err);
      gpsLabel.textContent = '📍 GPS: Unavailable';
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
  );
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function _connectWebSocket() {
  const url = `${WS_URL}?user_id=${encodeURIComponent(USER_ID)}`;
  _setStatus('connecting', 'Connecting…');

  try {
    ws = new WebSocket(url);
  } catch (e) {
    _setStatus('error', 'Connection failed');
    _showError('Connection Failed', `Could not connect to Iris backend at ${WS_URL}.\n\nMake sure the backend is running:\n  cd backend\n  uvicorn main:app --reload`);
    return;
  }

  ws.onopen = () => {
    _setStatus('ready', 'Ready');
    console.log('[Iris] WebSocket connected');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      _handleServerMessage(msg);
    } catch (e) {
      console.error('[Iris] Bad message from server:', e);
    }
  };

  ws.onerror = (err) => {
    console.error('[Iris] WebSocket error:', err);
    _setStatus('error', 'Error');
  };

  ws.onclose = (ev) => {
    _setStatus('error', 'Disconnected');
    console.warn('[Iris] WebSocket closed. Reconnecting in 3s…', ev.code);
    setTimeout(_connectWebSocket, 3000);
  };
}

function _wsSend(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

// ── Server Message Handler ────────────────────────────────────────────────────
function _handleServerMessage(msg) {
  switch (msg.type) {
    case 'status':
      _handleStatus(msg);
      break;
    case 'text':
      _handleText(msg);
      break;
    case 'audio':
      _handleAudio(msg);
      break;
    case 'navigation':
      _handleNavigation(msg);
      break;
    default:
      console.log('[Iris] Unknown message type:', msg.type);
  }
}

function _handleStatus(msg) {
  const state = msg.state || 'ready';
  const labels = {
    thinking: 'Thinking…',
    speaking: 'Speaking',
    ready:    'Ready',
    error:    msg.message || 'Error',
  };
  _setStatus(state, labels[state] || state);

  isSpeaking = (state === 'speaking');
  interruptBtn.classList.toggle('hidden', !isSpeaking);
}

function _handleText(msg) {
  if (!msg.detail && !msg.summary) return;

  // The full text to read out and display
  const fullText = msg.detail || msg.summary || '';

  // Stop any previous TTS + clear overlay
  _stopSpeaking();

  // Show the teleprompter with the full response
  _showTeleprompter(fullText);

  // Speak it aloud with word-by-word highlighting
  _speakWithHighlight(fullText);
}

// ── Teleprompter ──────────────────────────────────────────────────────────────

function _buildTeleprompter() {
  if (teleprompterEl) return;
  teleprompterEl = document.createElement('div');
  teleprompterEl.id = 'iris-teleprompter';

  // Fade gradient at top
  const fadeTop = document.createElement('div');
  fadeTop.className = 'tp-fade tp-fade-top';

  // Scrolling inner container
  teleprompterInner = document.createElement('div');
  teleprompterInner.id = 'iris-tp-inner';

  // Fade gradient at bottom
  const fadeBot = document.createElement('div');
  fadeBot.className = 'tp-fade tp-fade-bot';

  teleprompterEl.appendChild(fadeTop);
  teleprompterEl.appendChild(teleprompterInner);
  teleprompterEl.appendChild(fadeBot);

  document.getElementById('camera-container').appendChild(teleprompterEl);
}

function _showTeleprompter(text) {
  _buildTeleprompter();

  // Split into word spans
  const words = text.split(/\s+/).filter(Boolean);
  teleprompterInner.innerHTML = words
    .map((w, i) => `<span class="tp-word" data-idx="${i}">${w}</span>`)
    .join(' ');

  // Reset scroll
  teleprompterInner.scrollTop = 0;

  // Show
  teleprompterEl.classList.remove('tp-hidden');
  teleprompterEl.classList.add('tp-visible');
}

function _hideTeleprompter() {
  if (!teleprompterEl) return;
  teleprompterEl.classList.remove('tp-visible');
  teleprompterEl.classList.add('tp-hidden');
}

function _highlightWord(index) {
  if (!teleprompterInner) return;
  // Remove previous highlight
  const prev = teleprompterInner.querySelector('.tp-word.active');
  if (prev) prev.classList.remove('active');

  // Also mark all prior words as spoken
  const words = teleprompterInner.querySelectorAll('.tp-word');
  words.forEach((w, i) => {
    if (i < index)  w.classList.add('spoken');
    if (i === index) w.classList.add('active');
    if (i > index)  w.classList.remove('spoken', 'active');
  });

  // Scroll active word into view smoothly
  const activeWord = teleprompterInner.querySelector('.tp-word.active');
  if (activeWord) {
    activeWord.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// ── TTS with word-by-word highlight ──────────────────────────────────────────

function _speakWithHighlight(text) {
  if (!('speechSynthesis' in window)) {
    console.warn('[Iris] speechSynthesis not supported');
    // Still show the text, just no audio
    if (ttsAutoHideTimer) clearTimeout(ttsAutoHideTimer);
    ttsAutoHideTimer = setTimeout(_hideTeleprompter, 12000);
    return;
  }

  // Cancel any in-flight speech
  window.speechSynthesis.cancel();

  // Chrome loads voices async — get them reliably
  _getVoices().then(voices => {
    const utterance = new SpeechSynthesisUtterance(text);
    currentUtterance = utterance;

    utterance.rate   = 0.92;
    utterance.pitch  = 1.05;
    utterance.volume = 1.0;

    const preferred = voices.find(v =>
      v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Neural') || v.name.includes('Samantha') || v.name.includes('Karen'))
    ) || voices.find(v => v.lang.startsWith('en'));
    if (preferred) utterance.voice = preferred;

    _setStatus('speaking', 'Speaking…');
    interruptBtn.classList.remove('hidden');

    utterance.onboundary = (e) => {
      if (e.name !== 'word') return;
      const spokenSoFar = text.slice(0, e.charIndex);
      const wordIdx = spokenSoFar.split(/\s+/).filter(Boolean).length;
      _highlightWord(wordIdx);
    };

    utterance.onend = () => {
      _setStatus('ready', 'Ready');
      interruptBtn.classList.add('hidden');
      currentUtterance = null;
      if (teleprompterInner) {
        teleprompterInner.querySelectorAll('.tp-word').forEach(w => {
          w.classList.add('spoken');
          w.classList.remove('active');
        });
      }
      if (ttsAutoHideTimer) clearTimeout(ttsAutoHideTimer);
      ttsAutoHideTimer = setTimeout(_hideTeleprompter, 2500);
    };

    utterance.onerror = (e) => {
      console.warn('[Iris TTS] error:', e.error);
      _setStatus('ready', 'Ready');
      interruptBtn.classList.add('hidden');
      currentUtterance = null;
      if (ttsAutoHideTimer) clearTimeout(ttsAutoHideTimer);
      ttsAutoHideTimer = setTimeout(_hideTeleprompter, 4000);
    };

    window.speechSynthesis.speak(utterance);
  });
}

function _stopSpeaking() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  currentUtterance = null;
  if (ttsAutoHideTimer) clearTimeout(ttsAutoHideTimer);
  _hideTeleprompter();
  _setStatus('ready', 'Ready');
  interruptBtn.classList.add('hidden');
}

function _handleAudio(msg) {
  // Play base64 audio from backend (if TTS is implemented)
  if (!msg.data) return;
  try {
    const binary = atob(msg.data);
    const bytes  = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'audio/mpeg' });
    const url  = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(e => console.warn('Audio play failed:', e));
    audio.onended = () => URL.revokeObjectURL(url);
  } catch (e) {
    console.error('Audio decode error:', e);
  }
}

function _handleNavigation(msg) {
  const steps = msg.steps || [];
  if (steps.length > 0) {
    // Show first step in nav overlay
    navStep.textContent = `${_directionEmoji(steps[0].direction)} ${steps[0].instruction} — ${steps[0].distance}`;
    navOverlay.classList.remove('hidden');

    // Draw AR arrows
    AROverlay.setNavigation(steps);

    // Auto-advance step every 15 seconds
    setTimeout(() => _advanceNavStep(steps, 1), 15000);
  }
}

function _advanceNavStep(steps, index) {
  if (index >= steps.length) {
    navOverlay.classList.add('hidden');
    AROverlay.clearNavigation();
    return;
  }
  navStep.textContent = `${_directionEmoji(steps[index].direction)} ${steps[index].instruction} — ${steps[index].distance}`;
  AROverlay.advanceStep();
  setTimeout(() => _advanceNavStep(steps, index + 1), 15000);
}

function _directionEmoji(direction) {
  const map = {
    'straight': '⬆️', 'left': '⬅️', 'right': '➡️',
    'sharp-left': '↖️', 'sharp-right': '↗️',
    'slight-left': '↖️', 'slight-right': '↗️',
    'u-turn': '↩️', 'roundabout': '🔄',
  };
  return map[direction] || '⬆️';
}

// ── Mic Recording ─────────────────────────────────────────────────────────────
async function _startRecording() {
  if (isRecording) return;
  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm;codecs=opus' });
    const chunks = [];

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const reader = new FileReader();
      reader.onload = () => {
        const b64 = reader.result.split(',')[1];
        // Send audio + current frame together as multimodal
        _wsSend({
          type:  'multimodal',
          audio: b64,
          frame: lastFrameData,
        });
      };
      reader.readAsDataURL(blob);
      // Stop audio tracks
      audioStream.getTracks().forEach(t => t.stop());
    };

    mediaRecorder.start();
    isRecording = true;
    micBtn.classList.add('recording');
    micLabel.textContent = 'Recording…';
    _startFrameCapture(FRAME_INTERVAL_ACTIVE);
  } catch (err) {
    console.error('Mic error:', err);
    _showError('Microphone Required', `Iris needs your microphone to hear you.\n\nError: ${err.message}`);
  }
}

function _stopRecording() {
  if (!isRecording || !mediaRecorder) return;
  mediaRecorder.stop();
  isRecording = false;
  micBtn.classList.remove('recording');
  micLabel.textContent = 'Hold to speak';
  _startFrameCapture(FRAME_INTERVAL_IDLE);
}

// ── UI Controls ───────────────────────────────────────────────────────────────
function _bindControls() {
  // ── Mic: hold to record ──────────────────────────────────
  micBtn.addEventListener('mousedown', _startRecording);
  micBtn.addEventListener('mouseup',   _stopRecording);
  micBtn.addEventListener('touchstart', e => { e.preventDefault(); _startRecording(); });
  micBtn.addEventListener('touchend',   e => { e.preventDefault(); _stopRecording(); });

  // ── Interrupt ────────────────────────────────────────────
  interruptBtn.addEventListener('click', () => {
    _wsSend({ type: 'interrupt' });
    _stopSpeaking();  // also kill TTS + teleprompter
  });

  // ── Toggle detail ────────────────────────────────────────
  detailBtn.addEventListener('click', () => {
    overlayDetail.classList.toggle('hidden');
  });

  // ── Camera flip ──────────────────────────────────────────
  cameraFlipBtn.addEventListener('click', _flipCamera);

  // ── Text input (desktop) ─────────────────────────────────
  sendBtn.addEventListener('click', _sendTextMessage);
  textInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') _sendTextMessage();
  });

  // ── Error retry ──────────────────────────────────────────
  errorRetryBtn.addEventListener('click', () => {
    errorModal.classList.add('hidden');
    init();
  });
}

function _sendTextMessage() {
  const text = textInput.value.trim();
  if (!text) return;

  // Stop any current response before starting new query
  _stopSpeaking();

  _wsSend({ type: 'multimodal', text, frame: lastFrameData });
  textInput.value = '';

  // Show user's message in the teleprompter briefly
  _buildTeleprompter();
  teleprompterInner.innerHTML = `<span class="tp-word active">"${text}"</span>`;
  teleprompterEl.classList.remove('tp-hidden');
  teleprompterEl.classList.add('tp-visible');
}

// ── Status utility ────────────────────────────────────────────────────────────
function _setStatus(state, label) {
  document.body.className = state;
  statusText.textContent  = label;
}

// ── Error modal ───────────────────────────────────────────────────────────────
function _showError(title, message) {
  document.getElementById('error-title').textContent   = title;
  errorMessage.textContent = message;
  errorModal.classList.remove('hidden');
}

// ── Utility ───────────────────────────────────────────────────────────────────
function _generateUserId() {
  return 'user_' + Math.random().toString(36).slice(2, 11);
}

// ── Voice loader (handles Chrome async voices) ────────────────────────────────
function _getVoices() {
  return new Promise(resolve => {
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      resolve(voices);
    } else {
      window.speechSynthesis.addEventListener('voiceschanged', () => {
        resolve(window.speechSynthesis.getVoices());
      }, { once: true });
    }
  });
}

// ── Boot ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', init);
