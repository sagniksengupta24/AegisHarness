/**
 * AEGIS VERIFICATION ENGINE — UI RUNTIME
 *
 * This file intentionally owns only the imperative pieces of the experience:
 * WebGL/canvas visuals, scroll telemetry, audio feedback, and the small
 * interactions that are shared by the existing React markup.
 *
 * The runtime is fully mount/unmount safe so React StrictMode does not create
 * duplicate listeners or animation loops during development.
 */

const STATE_META = Object.freeze({
  IDLE: {
    kicker: 'PHASE 00 / STANDBY',
    word: 'READY',
    detail: 'Scroll or run demo to scrub the verification cycle.',
    integrity: '100%',
    badge: 'SYSTEM READY',
    phase: 'STANDBY'
  },
  PLAN: {
    kicker: 'PHASE 01 / SPECIFICATION',
    word: 'PLAN',
    detail: 'Orchestrator FSM plans task contract with Gemini 3.8 Flash.',
    integrity: '100%',
    badge: 'FSM_PLAN',
    phase: 'PHASE 01 / PLAN'
  },
  IMPLEMENT: {
    kicker: 'PHASE 02 / SYNTHESIS',
    word: 'IMPLEMENT',
    detail: 'Tool Bus applies surgical patch via LocalExecutor or Docker.',
    integrity: '98%',
    badge: 'APPLYING_PATCH',
    phase: 'PHASE 02 / BUILD'
  },
  VERIFY: {
    kicker: 'PHASE 03 / MEASUREMENT',
    word: 'VERIFY',
    detail: 'Verification Engine executes pre_flight, lint, and test suite.',
    integrity: '84%',
    badge: 'GATES_ACTIVE',
    phase: 'PHASE 03 / VERIFY'
  },
  FAIL: {
    kicker: 'PHASE 04 / INTERCEPTION',
    word: 'GATE FAIL',
    detail: 'Test runner exits non-zero or GateGuard detects a violation.',
    integrity: '0%',
    badge: 'GATE_FAILED',
    phase: 'PHASE 04 / FAILED'
  },
  DIAGNOSE: {
    kicker: 'PHASE 05 / ISOLATION',
    word: 'DIAGNOSE',
    detail: 'Bounded error diagnosis analyzes captured failure traceback.',
    integrity: '65%',
    badge: 'DIAGNOSING',
    phase: 'PHASE 05 / REPAIR'
  },
  REPAIR: {
    kicker: 'PHASE 06 / SURGICAL FIX',
    word: 'REPAIR',
    detail: 'Gemini synthesizes targeted repair within bounded retry budget.',
    integrity: '92%',
    badge: 'REPAIRING',
    phase: 'PHASE 06 / REPAIR'
  },
  GATEGUARD: {
    kicker: 'SECURITY BARRIER',
    word: 'GATEGUARD',
    detail: 'PathGuard, SecretGuard, and CommandGuard protect the environment.',
    integrity: '100%',
    badge: 'ARMED',
    phase: 'GATEGUARD DEFENSE'
  },
  TRACE: {
    kicker: 'AUDIT LEDGER',
    word: 'TRACE',
    detail: 'Deterministic session telemetry traces every prompt, tool, and gate.',
    integrity: '100%',
    badge: 'TRACE_STREAM',
    phase: 'TIMELINE AUDIT'
  },
  ROLLBACK: {
    kicker: 'SURGICAL RESTORATION',
    word: 'ROLLBACK',
    detail: 'Transactional revert resets touched files while keeping untracked work.',
    integrity: '100%',
    badge: 'SURGICAL_ROLLBACK',
    phase: 'ROLLBACK'
  },
  PASS: {
    kicker: 'PHASE 07 / PROVEN',
    word: 'COMPLETED',
    detail: 'All required gates pass. Task transitions to COMPLETED state.',
    integrity: '100%',
    badge: 'COMPLETED',
    phase: 'COMPLETE'
  }
});

const DEMO_SEQUENCE = ['PLAN', 'IMPLEMENT', 'VERIFY', 'FAIL', 'DIAGNOSE', 'REPAIR', 'VERIFY', 'PASS'];
const VIDEO_CHAPTERS = [
  { start: 0, end: 7, name: 'CH 01: DETERMINISTIC HARNESS', state: 'PLAN', target: 'hero' },
  { start: 7, end: 14, name: 'CH 02: GEMINI SPEC & SYNTHESIS', state: 'IMPLEMENT', target: 'narrative' },
  { start: 14, end: 21, name: 'CH 03: VERIFICATION GATE CHECK', state: 'FAIL', target: 'narrative' },
  { start: 21, end: 28, name: 'CH 04: GATEGUARD DEFENSE', state: 'GATEGUARD', target: 'gateguard' },
  { start: 28, end: 35, name: 'CH 05: SESSION AUDIT TRACE', state: 'TRACE', target: 'trace' },
  { start: 35, end: 42, name: 'CH 06: TRANSACTIONAL ROLLBACK', state: 'ROLLBACK', target: 'rollback' }
];
const VIDEO_DURATION = 42;

export function initAegisEngine() {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return () => {};
  }

  const abortController = new AbortController();
  const { signal } = abortController;
  const cleanups = [];

  const byId = id => document.getElementById(id);
  const on = (target, type, handler, options = {}) => {
    if (!target || typeof target.addEventListener !== 'function') return;
    target.addEventListener(type, handler, { ...options, signal });
  };

  const topbarState = byId('topbarState');
  const topbarMetric = byId('topbarMetric');
  const phaseKicker = byId('phaseKicker');
  const phaseBadge = byId('phaseBadge');
  const phaseWord = byId('phaseWord');
  const phaseDetail = byId('phaseDetail');
  const astRisk = byId('astRiskVal');
  const coverage = byId('coverageVal');
  const assertions = byId('assertionsVal');
  const cardState = byId('cardStateVal');
  const cardIntegrityVal = byId('cardIntegrityVal');
  const engineBadge = byId('engineBadge');
  const cursorRig = byId('cursor3DRig');
  const cursorMode = byId('cursorMode');
  const soundToggle = byId('soundToggle');
  const diagAudioStatus = byId('diagAudioStatus');
  const scrollRailFill = byId('scrollRailFill');
  const scrubButtons = Array.from(document.querySelectorAll('.scrub-btn'));

  let destroyed = false;
  let currentState = 'IDLE';
  let demoTimer = null;
  let audioContext = null;
  let soundEnabled = false;
  let engineRaf = 0;
  let worldRaf = 0;
  let cursorRaf = 0;
  let videoRaf = 0;
  let videoPlaying = false;
  let videoMode = false;
  let videoTime = 0;
  let videoSpeed = 1;
  let lastVideoTick = 0;
  let lastChapter = -1;
  let videoCanvasContext = null;
  let videoCanvas = null;
  let videoCanvasSize = { width: 0, height: 0, dpr: 1 };
  let rollbackResetTimer = null;
  let gateTimer = null;
  let demoResetTimer = null;

  const cleanupTimer = handle => {
    if (handle == null) return;
    clearTimeout(handle);
    clearInterval(handle);
  };

  const safeText = (el, value) => {
    if (el) el.textContent = value;
  };

  const updateStateMetrics = state => {
    const metrics = {
      IDLE: ['0.00%', '100%', '42 PASSED'],
      PLAN: ['0.00%', '100%', '42 PASSED'],
      IMPLEMENT: ['1.85%', '98%', '42 PASSED'],
      VERIFY: ['5.16%', '96%', '46 PASSED'],
      FAIL: ['18.42%', '71%', '47 PASSED'],
      DIAGNOSE: ['7.21%', '78%', '51 PASSED'],
      REPAIR: ['1.03%', '99%', '57 PASSED'],
      GATEGUARD: ['0.00%', '100%', '64 PASSED'],
      TRACE: ['0.00%', '100%', '64 PASSED'],
      ROLLBACK: ['0.00%', '100%', '64 PASSED'],
      PASS: ['0.00%', '100%', '64 PASSED']
    }[state] || ['0.00%', '100%', '42 PASSED'];

    safeText(astRisk, metrics[0]);
    safeText(coverage, metrics[1]);
    safeText(assertions, metrics[2]);

    const astRiskFill = byId('astRiskFill');
    const coverageFill = byId('coverageFill');
    const phaseProgressBar = byId('phaseProgressBar');

    const riskPercents = {
      IDLE: '0%', PLAN: '4%', IMPLEMENT: '18%', VERIFY: '36%',
      FAIL: '94%', DIAGNOSE: '52%', REPAIR: '10%', GATEGUARD: '0%',
      TRACE: '0%', ROLLBACK: '0%', PASS: '0%'
    };
    const coveragePercents = {
      IDLE: '100%', PLAN: '100%', IMPLEMENT: '98%', VERIFY: '96%',
      FAIL: '71%', DIAGNOSE: '78%', REPAIR: '99%', GATEGUARD: '100%',
      TRACE: '100%', ROLLBACK: '100%', PASS: '100%'
    };
    const stageIndexes = {
      IDLE: 0, PLAN: 1, IMPLEMENT: 2, VERIFY: 3,
      FAIL: 4, DIAGNOSE: 5, REPAIR: 6, PASS: 7
    };

    if (astRiskFill) {
      astRiskFill.style.width = riskPercents[state] || '0%';
      astRiskFill.classList.toggle('alert', state === 'FAIL');
    }
    if (coverageFill) {
      coverageFill.style.width = coveragePercents[state] || '100%';
    }
    if (phaseProgressBar && stageIndexes[state] !== undefined) {
      phaseProgressBar.style.width = `${((stageIndexes[state] + 1) / 8) * 100}%`;
    }

    const integrityByState = {
      IDLE: '100%', PLAN: '100%', IMPLEMENT: '98%', VERIFY: '84%', FAIL: '0%',
      DIAGNOSE: '65%', REPAIR: '92%', GATEGUARD: '100%', TRACE: '100%', ROLLBACK: '100%', PASS: '100%'
    };
    safeText(cardIntegrityVal, integrityByState[state] || '100%');
    cardIntegrityVal?.classList.toggle('green', !['FAIL', 'VERIFY'].includes(state));
    cardIntegrityVal?.classList.toggle('text-alert', state === 'FAIL');
  };

  const setState = (requestedState, playAudio = true) => {
    const state = STATE_META[requestedState] ? requestedState : 'IDLE';
    currentState = state;
    const meta = STATE_META[state];

    safeText(topbarState, state);
    safeText(phaseKicker, meta.kicker);
    safeText(phaseBadge, meta.badge);
    safeText(phaseWord, meta.word);
    safeText(phaseDetail, meta.detail);
    safeText(cardState, state);
    safeText(engineBadge, meta.badge);
    updateStateMetrics(state);

    scrubButtons.forEach(button => {
      const active = button.dataset.state === state;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });

    if (cursorRig) {
      cursorRig.classList.toggle('state-fail', state === 'FAIL');
      cursorRig.classList.toggle('state-pass', state === 'PASS');
    }

    if (playAudio && soundEnabled) {
      if (state === 'FAIL') playTone('block');
      else if (state === 'PASS') playTone('pass');
      else playTone('tick');
    }
  };

  const initAudio = () => {
    if (!audioContext) {
      const AudioCtor = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtor) return;
      audioContext = new AudioCtor();
    }
    if (audioContext.state === 'suspended') {
      audioContext.resume().catch(() => {});
    }
  };

  const playTone = type => {
    if (!soundEnabled) return;
    try {
      initAudio();
      if (!audioContext) return;
      const t = audioContext.currentTime;

      const configs = {
        tick: { type: 'sine', start: 800, end: 140, duration: 0.03, gain: 0.035 },
        block: { type: 'triangle', start: 110, end: 45, duration: 0.22, gain: 0.08 },
        sweep: { type: 'sine', start: 220, end: 660, duration: 0.2, gain: 0.03 }
      };

      if (type === 'pass') {
        [523.25, 659.25].forEach((frequency, index) => {
          const offset = index * 0.03;
          const oscillator = audioContext.createOscillator();
          const gain = audioContext.createGain();
          oscillator.type = 'sine';
          oscillator.frequency.setValueAtTime(frequency, t + offset);
          gain.gain.setValueAtTime(0.0001, t + offset);
          gain.gain.exponentialRampToValueAtTime(0.055, t + offset + 0.015);
          gain.gain.exponentialRampToValueAtTime(0.0001, t + offset + 0.35);
          oscillator.connect(gain).connect(audioContext.destination);
          oscillator.start(t + offset);
          oscillator.stop(t + offset + 0.4);
        });
        return;
      }

      const cfg = configs[type] || configs.tick;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = cfg.type;
      oscillator.frequency.setValueAtTime(cfg.start, t);
      oscillator.frequency.exponentialRampToValueAtTime(cfg.end, t + cfg.duration * 0.75);
      gain.gain.setValueAtTime(cfg.gain, t);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + cfg.duration);
      oscillator.connect(gain).connect(audioContext.destination);
      oscillator.start(t);
      oscillator.stop(t + cfg.duration + 0.02);
    } catch {
      // Audio feedback is optional and should never break the page.
    }
  };

  on(soundToggle, 'click', () => {
    soundEnabled = !soundEnabled;
    if (soundEnabled) initAudio();
    soundToggle.classList.toggle('active', soundEnabled);
    soundToggle.setAttribute('aria-pressed', String(soundEnabled));
    safeText(soundToggle.querySelector('.sound-label'), soundEnabled ? 'Audio on' : 'Audio off');
    safeText(diagAudioStatus, soundEnabled ? 'ARMED' : 'MUTED');
    if (soundEnabled) playTone('pass');
  });

  // -----------------------------------------------------------------------
  // Hero WebGL engine
  // -----------------------------------------------------------------------
  const engineCanvas = byId('engineCanvas');
  const gl = engineCanvas?.getContext?.('webgl', { antialias: true, alpha: true, depth: true }) || null;
  let shaderProgram = null;
  let positionBuffer = null;
  let colorBuffer = null;
  let particleNodes = [];
  let pointerX = 0;
  let pointerY = 0;
  let targetRotX = 0;
  let targetRotY = 0;
  let currentRotX = 0;
  let currentRotY = 0;
  let dragging = false;
  let lastPointerX = 0;
  let lastPointerY = 0;
  let fpsFrames = 0;
  let fpsStart = performance.now();
  const vertexPositions = [];
  const vertexColors = [];
  const TAU = Math.PI * 2;

  const mat4Perspective = (fov, aspect, near, far) => {
    const f = 1.0 / Math.tan(fov / 2);
    const nf = 1.0 / (near - far);
    const out = new Float32Array(16);
    out[0] = f / aspect;
    out[5] = f;
    out[10] = (far + near) * nf;
    out[11] = -1.0;
    out[14] = (2.0 * far * near) * nf;
    out[15] = 0.0;
    return out;
  };

  const mat4Multiply = (a, b) => {
    const out = new Float32Array(16);
    for (let i = 0; i < 4; i++) {
      for (let j = 0; j < 4; j++) {
        let sum = 0;
        for (let k = 0; k < 4; k++) {
          sum += a[k * 4 + j] * b[i * 4 + k];
        }
        out[i * 4 + j] = sum;
      }
    }
    return out;
  };

  const mat4RotX = rad => {
    const c = Math.cos(rad), s = Math.sin(rad);
    const out = new Float32Array(16);
    out[0] = 1; out[5] = c; out[6] = s; out[9] = -s; out[10] = c; out[15] = 1;
    return out;
  };

  const mat4RotY = rad => {
    const c = Math.cos(rad), s = Math.sin(rad);
    const out = new Float32Array(16);
    out[0] = c; out[2] = -s; out[5] = 1; out[8] = s; out[10] = c; out[15] = 1;
    return out;
  };

  const mat4RotZ = rad => {
    const c = Math.cos(rad), s = Math.sin(rad);
    const out = new Float32Array(16);
    out[0] = c; out[1] = s; out[4] = -s; out[5] = c; out[10] = 1; out[15] = 1;
    return out;
  };

  const mat4Translate = (x, y, z) => {
    const out = new Float32Array(16);
    out[0] = 1; out[5] = 1; out[10] = 1; out[15] = 1;
    out[12] = x; out[13] = y; out[14] = z;
    return out;
  };

  const addRing = (rx, ry, zPos, tiltX, tiltY, alpha, rgb) => {
    const segments = 84;
    for (let i = 0; i <= segments; i += 1) {
      const theta = (TAU * i) / segments;
      const x = rx * Math.cos(theta);
      const y = ry * Math.sin(theta);
      const cosX = Math.cos(tiltX), sinX = Math.sin(tiltX);
      const y1 = y * cosX - zPos * sinX;
      const z1 = y * sinX + zPos * cosX;
      const cosY = Math.cos(tiltY), sinY = Math.sin(tiltY);
      const x2 = x * cosY + z1 * sinY;
      const z2 = -x * sinY + z1 * cosY;
      vertexPositions.push(x2, y1, z2);
      vertexColors.push(rgb[0], rgb[1], rgb[2], alpha);
    }
  };

  const generateGeometry = (state, timeMs) => {
    vertexPositions.length = 0;
    vertexColors.length = 0;
    const base = state === 'FAIL'
      ? [1.0, 0.31, 0.18]
      : state === 'PASS'
        ? [0.10, 0.65, 0.42]
        : [0.18, 0.18, 0.16];
    const accent = [1.0, 0.31, 0.18];
    const ringCount = state === 'VERIFY' ? 9 : state === 'FAIL' ? 11 : state === 'PASS' ? 7 : 6;

    for (let r = 0; r < ringCount; r += 1) {
      const p = r / Math.max(ringCount - 1, 1);
      const rx = 1 + p * 1.1;
      const ry = rx * (0.7 + 0.18 * Math.sin(r * 1.5 + timeMs * 0.001));
      const z = (p - 0.5) * 0.9;
      const tiltX = r * 0.28 + (state === 'FAIL' ? Math.sin(timeMs * 0.008 + r) * 0.35 : Math.sin(timeMs * 0.001) * 0.1);
      const tiltY = r * 0.35 + timeMs * 0.0004;
      const alpha = state === 'FAIL' ? 0.85 : state === 'PASS' ? 0.75 : (r % 2 === 0 ? 0.75 : 0.5);
      const color = (state === 'IDLE' && r === 2) ? accent : base;
      addRing(rx, ry, z, tiltX, tiltY, alpha, color);
    }

    const core = state === 'FAIL' ? 0.65 : 0.85;
    for (let c = 0; c < 4; c += 1) {
      const tilt = c * (Math.PI / 4) + timeMs * 0.0007;
      const color = state === 'IDLE' ? accent : base;
      addRing(core, core * 0.8, 0, tilt, tilt * 0.8, 0.85, color);
    }

    for (const node of particleNodes) {
      const pulse = 1 + 0.08 * Math.sin(timeMs * node.speed + node.phase);
      const jitter = state === 'FAIL' ? (Math.random() - 0.5) * 0.12 : 0;
      vertexPositions.push((node.x + jitter) * pulse, (node.y + jitter) * pulse, (node.z + jitter) * pulse);
      const pColor = state === 'IDLE' ? (Math.random() > 0.6 ? accent : base) : base;
      vertexColors.push(pColor[0], pColor[1], pColor[2], state === 'PASS' ? 0.75 : 0.6);
    }
  };

  const resizeEngineCanvas = () => {
    if (!engineCanvas || !gl) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = engineCanvas.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width * dpr));
    const height = Math.max(1, Math.floor(rect.height * dpr));
    if (engineCanvas.width !== width || engineCanvas.height !== height) {
      engineCanvas.width = width;
      engineCanvas.height = height;
      gl.viewport(0, 0, width, height);
    }
  };

  const compileShader = (type, source) => {
    const shader = gl.createShader(type);
    if (!shader) throw new Error('Unable to create WebGL shader');
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) || 'Shader compile failed');
    return shader;
  };

  const initWebGL = () => {
    if (!gl || !engineCanvas) return;
    const vs = compileShader(gl.VERTEX_SHADER, `
      attribute vec3 aPosition;
      attribute vec4 aColor;
      uniform mat4 uMatrix;
      uniform float uPointSize;
      varying vec4 vColor;
      void main() {
        gl_Position = uMatrix * vec4(aPosition, 1.0);
        gl_PointSize = uPointSize;
        vColor = aColor;
      }
    `);
    const fs = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float;
      varying vec4 vColor;
      uniform float uIsPoint;
      void main() {
        float alpha = vColor.a;
        if (uIsPoint > 0.5) {
          vec2 coord = gl_PointCoord - vec2(0.5);
          float dist = length(coord);
          alpha *= smoothstep(0.5, 0.08, dist);
        }
        gl_FragColor = vec4(vColor.rgb, alpha);
      }
    `);

    shaderProgram = gl.createProgram();
    if (!shaderProgram) throw new Error('Unable to create WebGL program');
    gl.attachShader(shaderProgram, vs);
    gl.attachShader(shaderProgram, fs);
    gl.linkProgram(shaderProgram);
    if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(shaderProgram) || 'Program link failed');
    positionBuffer = gl.createBuffer();
    colorBuffer = gl.createBuffer();
    particleNodes = Array.from({ length: 240 }, () => {
      const theta = Math.random() * TAU;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 1.2 + Math.random() * 1.35;
      return {
        x: radius * Math.sin(phi) * Math.cos(theta),
        y: radius * Math.cos(phi) * 0.72,
        z: radius * Math.sin(phi) * Math.sin(theta),
        speed: 0.0006 + Math.random() * 0.0014,
        phase: Math.random() * TAU
      };
    });
    gl.deleteShader(vs);
    gl.deleteShader(fs);
  };

  const renderEngine = timeMs => {
    if (destroyed || !gl || !shaderProgram) return;
    resizeEngineCanvas();
    fpsFrames += 1;
    if (timeMs - fpsStart >= 1000) {
      const fps = Math.round((fpsFrames * 1000) / (timeMs - fpsStart));
      safeText(topbarMetric, `${fps} FPS`);
      fpsFrames = 0;
      fpsStart = timeMs;
    }

    currentRotX += (targetRotX - currentRotX) * 0.08;
    currentRotY += (targetRotY - currentRotY) * 0.08;
    const aspect = engineCanvas.height ? engineCanvas.width / engineCanvas.height : 1;
    let matrix = mat4Multiply(mat4Perspective(0.95, aspect, 0.1, 50), mat4Translate(0, 0, -5.8));
    matrix = mat4Multiply(matrix, mat4RotX(currentRotX + 0.18 + Math.sin(timeMs * 0.0004) * 0.05));
    matrix = mat4Multiply(matrix, mat4RotY(currentRotY + timeMs * 0.00025));
    matrix = mat4Multiply(matrix, mat4RotZ(Math.sin(timeMs * 0.0003) * 0.04));

    generateGeometry(currentState, timeMs);
    gl.viewport(0, 0, engineCanvas.width, engineCanvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(shaderProgram);

    const uMatrix = gl.getUniformLocation(shaderProgram, 'uMatrix');
    if (uMatrix) gl.uniformMatrix4fv(uMatrix, false, matrix);
    const uPointSize = gl.getUniformLocation(shaderProgram, 'uPointSize');
    if (uPointSize) gl.uniform1f(uPointSize, Math.max(2, Math.min(6, window.innerWidth / 250)));

    const aPos = gl.getAttribLocation(shaderProgram, 'aPosition');
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertexPositions), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);

    const aColor = gl.getAttribLocation(shaderProgram, 'aColor');
    gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertexColors), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(aColor);
    gl.vertexAttribPointer(aColor, 4, gl.FLOAT, false, 0, 0);

    const totalVertices = Math.floor(vertexPositions.length / 3);
    const ringVertexCount = Math.max(0, totalVertices - particleNodes.length);
    const uIsPoint = gl.getUniformLocation(shaderProgram, 'uIsPoint');
    if (uIsPoint) gl.uniform1f(uIsPoint, 0.0);
    gl.drawArrays(gl.LINE_STRIP, 0, ringVertexCount);

    if (uIsPoint) gl.uniform1f(uIsPoint, 1.0);
    gl.drawArrays(gl.POINTS, ringVertexCount, particleNodes.length);
    engineRaf = window.requestAnimationFrame(renderEngine);
  };

  on(engineCanvas, 'pointerdown', event => {
    dragging = true;
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
    engineCanvas.setPointerCapture?.(event.pointerId);
  });
  on(window, 'pointerup', () => { dragging = false; });
  on(engineCanvas, 'pointermove', event => {
    const rect = engineCanvas.getBoundingClientRect();
    const nx = (event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5;
    const ny = (event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5;
    if (dragging) {
      targetRotY += (event.clientX - lastPointerX) * 0.008;
      targetRotX += (event.clientY - lastPointerY) * 0.008;
      lastPointerX = event.clientX;
      lastPointerY = event.clientY;
    } else {
      targetRotY = nx * 0.6;
      targetRotX = -ny * 0.4;
    }
  }, { passive: true });

  // -----------------------------------------------------------------------
  // Ambient world canvas and pointer rig
  // -----------------------------------------------------------------------
  const worldCanvas = byId('world3dBg');
  const worldCtx = worldCanvas?.getContext?.('2d') || null;
  const trailCanvas = byId('cursorTrailCanvas');
  const trailCtx = trailCanvas?.getContext?.('2d') || null;
  const cursorOrb = byId('cursorOrb');
  const cursorCoords = byId('cursorCoords');
  const worldCubes = Array.from({ length: 34 }, (_, index) => ({
    x: ((index * 137) % 760) - 380,
    y: ((index * 83) % 520) - 260,
    z: 320 + ((index * 191) % 2200),
    size: 14 + (index % 6) * 5,
    rz: (index % 8) * 0.24,
    vrz: 0.0004 + (index % 3) * 0.00015,
    alpha: 0.35 + (index % 5) * 0.06
  }));
  const trailParticles = [];
  let cursorX = window.innerWidth / 2;
  let cursorY = window.innerHeight / 2;
  let smoothCursorX = cursorX;
  let smoothCursorY = cursorY;
  let previousCursorX = cursorX;
  let previousCursorY = cursorY;
  let shockwaveTimer = null;

  const resize2DCanvas = (canvas, ctx) => {
    if (!canvas || !ctx) return null;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.floor(window.innerWidth * dpr));
    const height = Math.max(1, Math.floor(window.innerHeight * dpr));
    canvas.width = width;
    canvas.height = height;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { width: window.innerWidth, height: window.innerHeight };
  };

  let worldSize = resize2DCanvas(worldCanvas, worldCtx) || { width: 1, height: 1 };
  resize2DCanvas(trailCanvas, trailCtx);

  const renderWorld = timeMs => {
    if (destroyed || !worldCtx) return;
    const { width, height } = worldSize;
    worldCtx.clearRect(0, 0, width, height);
    const cx = width / 2;
    const cy = height / 2;
    const fov = 480;
    const camX = (cursorX / Math.max(width, 1) - 0.5) * 90 + Math.sin(timeMs * 0.00042) * 35;
    const camY = (cursorY / Math.max(height, 1) - 0.5) * 60 + Math.cos(timeMs * 0.00035) * 25 + (window.scrollY * 0.14) % 360;

    worldCtx.strokeStyle = currentState === 'FAIL'
      ? 'rgba(255, 79, 47, 0.045)'
      : currentState === 'PASS'
        ? 'rgba(26, 138, 97, 0.045)'
        : 'rgba(26, 26, 24, 0.035)';
    worldCtx.lineWidth = 1;

    const horizonY = cy + 100;
    for (let z = 200; z <= 2400; z += 240) {
      const screenY = cy + (450 - camY * 0.3) * fov / z;
      if (screenY > horizonY && screenY < height) {
        worldCtx.beginPath();
        worldCtx.moveTo(0, screenY);
        worldCtx.lineTo(width, screenY);
        worldCtx.stroke();
      }
    }

    for (let x = -1400; x <= 1400; x += 280) {
      const x1 = cx + (x - camX * 0.4) * fov / 200;
      const y1 = cy + (450 - camY * 0.3) * fov / 200;
      const x2 = cx + (x - camX * 0.4) * fov / 2400;
      const y2 = cy + (450 - camY * 0.3) * fov / 2400;
      worldCtx.beginPath();
      worldCtx.moveTo(x1, y1);
      worldCtx.lineTo(x2, y2);
      worldCtx.stroke();
    }

    worldCubes.forEach(cube => {
      cube.rz += cube.vrz;
      if (cube.z <= 50) return;
      const scale = fov / cube.z;
      const px = cx + (cube.x - camX) * scale;
      const py = cy + (cube.y - camY) * scale;
      const size = cube.size * scale;
      if (px < -100 || px > width + 100 || py < -100 || py > height + 100) return;
      const alpha = Math.max(0.04, Math.min(0.35, (1 - cube.z / 2600) * cube.alpha));
      worldCtx.save();
      worldCtx.translate(px, py);
      worldCtx.rotate(cube.rz);
      worldCtx.strokeStyle = currentState === 'FAIL'
        ? `rgba(255, 79, 47, ${alpha * 1.5})`
        : currentState === 'PASS'
          ? `rgba(26, 138, 97, ${alpha * 1.5})`
          : `rgba(26, 26, 24, ${alpha})`;
      worldCtx.lineWidth = Math.max(0.6, 1.2 * scale);
      worldCtx.strokeRect(-size / 2, -size / 2, size, size);
      if (size > 14) {
        worldCtx.beginPath();
        worldCtx.moveTo(-size / 2, -size / 2);
        worldCtx.lineTo(size / 2, size / 2);
        worldCtx.moveTo(size / 2, -size / 2);
        worldCtx.lineTo(-size / 2, size / 2);
        worldCtx.stroke();
      }
      worldCtx.restore();
    });

    worldRaf = window.requestAnimationFrame(renderWorld);
  };

  const spawnTrail = (x, y, vx, vy, burst = false) => {
    if (!trailCtx) return;
    if (trailParticles.length > 72) trailParticles.splice(0, trailParticles.length - 72);
    const count = burst ? 14 : 1;
    for (let i = 0; i < count; i += 1) {
      const angle = burst ? (TAU * i) / count : Math.atan2(vy, vx) + (Math.random() - 0.5) * 1.2;
      const speed = burst ? 2.5 + Math.random() * 5 : 0.8 + Math.random() * 1.5;
      trailParticles.push({
        x: x + (Math.random() - 0.5) * 4,
        y: y + (Math.random() - 0.5) * 4,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        size: burst ? 2 + Math.random() * 3 : 1.2 + Math.random() * 1.6,
        alpha: 0.9,
        decay: burst ? 0.035 : 0.05
      });
    }
  };

  const renderCursor = () => {
    if (destroyed) return;
    const velocityX = cursorX - previousCursorX;
    const velocityY = cursorY - previousCursorY;
    previousCursorX = cursorX;
    previousCursorY = cursorY;
    smoothCursorX += (cursorX - smoothCursorX) * 0.35;
    smoothCursorY += (cursorY - smoothCursorY) * 0.35;
    if (cursorOrb) {
      cursorOrb.style.left = `${smoothCursorX}px`;
      cursorOrb.style.top = `${smoothCursorY}px`;
    }
    if (cursorRig) {
      const reticle = cursorRig.querySelector('.cursor-3d-reticle');
      if (reticle) {
        reticle.style.transform = `translate3d(${smoothCursorX}px, ${smoothCursorY}px, 0)`;
      }
    }
    safeText(cursorCoords, `X: ${Math.round(smoothCursorX)} Y: ${Math.round(smoothCursorY)}`);
    if (Math.hypot(velocityX, velocityY) > 2.8) spawnTrail(smoothCursorX, smoothCursorY, velocityX, velocityY, false);

    if (trailCtx && trailCanvas) {
      trailCtx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      for (let i = trailParticles.length - 1; i >= 0; i -= 1) {
        const particle = trailParticles[i];
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.alpha -= particle.decay;
        if (particle.alpha <= 0) {
          trailParticles.splice(i, 1);
          continue;
        }
        const rgb = currentState === 'FAIL' ? '255, 79, 47' : currentState === 'PASS' ? '26, 138, 97' : '255, 110, 60';
        trailCtx.beginPath();
        trailCtx.arc(particle.x, particle.y, particle.size, 0, TAU);
        trailCtx.fillStyle = `rgba(${rgb}, ${particle.alpha.toFixed(2)})`;
        trailCtx.shadowColor = `rgba(${rgb}, 0.8)`;
        trailCtx.shadowBlur = 6;
        trailCtx.fill();
      }
    }
    cursorRaf = window.requestAnimationFrame(renderCursor);
  };

  on(window, 'mousemove', event => {
    cursorX = event.clientX;
    cursorY = event.clientY;
  }, { passive: true });
  on(window, 'pointerdown', event => {
    cursorRig?.classList.add('mouse-down');
    cursorRig?.classList.remove('shockwave');
    void cursorRig?.offsetWidth;
    cursorRig?.classList.add('shockwave');
    cleanupTimer(shockwaveTimer);
    shockwaveTimer = window.setTimeout(() => cursorRig?.classList.remove('shockwave'), 550);
    spawnTrail(event.clientX, event.clientY, 0, 0, true);
    if (soundEnabled) playTone('tick');
  }, { passive: true });
  on(window, 'pointerup', () => cursorRig?.classList.remove('mouse-down'));

  // -----------------------------------------------------------------------
  // Scroll narrative and demo controls
  // -----------------------------------------------------------------------
  const updateScrollProgress = () => {
    const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    const progress = maxScroll ? Math.min(1, Math.max(0, window.scrollY / maxScroll)) : 0;
    if (scrollRailFill) scrollRailFill.style.height = `${progress * 100}%`;

    const narrative = byId('narrative');
    const gateguard = byId('gateguard');
    const trace = byId('trace');
    const rollback = byId('rollback');
    const install = byId('install');
    const hero = byId('hero');
    const centerY = window.scrollY + window.innerHeight * 0.48;

    if (install && centerY >= install.offsetTop) setState('PASS', false);
    else if (rollback && centerY >= rollback.offsetTop) setState('ROLLBACK', false);
    else if (trace && centerY >= trace.offsetTop) setState('TRACE', false);
    else if (gateguard && centerY >= gateguard.offsetTop) setState('GATEGUARD', false);
    else if (narrative && centerY >= narrative.offsetTop && centerY <= narrative.offsetTop + narrative.offsetHeight) {
      if (!manualPhaseLock) {
        const local = (centerY - narrative.offsetTop) / Math.max(narrative.offsetHeight, 1);
        const index = Math.min(DEMO_SEQUENCE.length - 1, Math.floor(local * DEMO_SEQUENCE.length));
        setState(DEMO_SEQUENCE[index], false);
      }
    } else if (hero && centerY >= hero.offsetTop) setState('IDLE', false);
  };

  let manualPhaseLock = false;
  let manualPhaseTimer = null;

  on(window, 'scroll', updateScrollProgress, { passive: true });

  scrubButtons.forEach(button => {
    on(button, 'click', () => {
      manualPhaseLock = true;
      cleanupTimer(manualPhaseTimer);
      manualPhaseTimer = window.setTimeout(() => {
        manualPhaseLock = false;
      }, 2800);
      setState(button.dataset.state || 'IDLE', true);
    });
  });

  on(document, 'pointerover', event => {
    const target = event.target?.closest?.('a, button, [role="button"], input, .scrub-btn, .option-wheel, .engine-card, .gateguard-card, .inspector-card, .topo-node, .wheel-step-dot, .primary-btn, .secondary-btn');
    if (cursorRig) {
      cursorRig.classList.toggle('hover-target', Boolean(target));
    }
  });
  on(document, 'pointerout', event => {
    if (!event.relatedTarget || !event.relatedTarget.closest('a, button, [role="button"], input, .scrub-btn, .option-wheel, .engine-card, .gateguard-card, .inspector-card, .topo-node, .wheel-step-dot, .primary-btn, .secondary-btn')) {
      cursorRig?.classList.remove('hover-target');
    }
  });

  const startDemo = byId('startDemoBtn');
  on(startDemo, 'click', () => {
    cleanupTimer(demoTimer);
    let index = 0;
    const label = startDemo.querySelector('span:not(.btn-glow)');
    safeText(label, 'Running cycle...');
    startDemo.setAttribute('aria-busy', 'true');
    setState(DEMO_SEQUENCE[index], true);
    demoTimer = window.setInterval(() => {
      index += 1;
      if (index >= DEMO_SEQUENCE.length) {
        cleanupTimer(demoTimer);
        demoTimer = null;
        startDemo.setAttribute('aria-busy', 'false');
        safeText(label, 'Scrub verification cycle');
        cleanupTimer(demoResetTimer);
        demoResetTimer = window.setTimeout(() => {
          if (!destroyed) setState('IDLE', false);
          demoResetTimer = null;
        }, 900);
        return;
      }
      setState(DEMO_SEQUENCE[index], true);
    }, 650);
  });

  // -----------------------------------------------------------------------
  // GateGuard
  // -----------------------------------------------------------------------
  const evalInput = byId('evalInput');
  const evalBtn = byId('evalBtn');
  const evalOutput = byId('evalOutput');

  const evaluateGateCommand = command => {
    const cmd = String(command || '').trim();
    if (!cmd || !evalOutput) return;
    cleanupTimer(gateTimer);
    const malicious = /sudo|rm\s+-rf|curl.*\|\s*bash|export.*SECRET|chmod\s+777|cat\s+\/etc\/passwd|\.\.\/|eval\(|exec\(/i.test(cmd);
    const latency = (12.4 + Math.random() * 26.2).toFixed(1);
    safeText(evalOutput, '[GATEGUARD] Inspecting payload…');
    if (soundEnabled) playTone('tick');
    gateTimer = window.setTimeout(() => {
      if (malicious) {
        safeText(evalOutput, `[GATEGUARD] Blocked: '${cmd}'. Action: BLOCKED. Risk score: 1.00. Latency: ${latency}μs.`);
        setState('FAIL', false);
        if (soundEnabled) playTone('block');
      } else {
        safeText(evalOutput, `[GATEGUARD] Cleared: '${cmd}'. Action: ALLOWED. Risk score: 0.00. Latency: ${latency}μs.`);
        setState('GATEGUARD', false);
        if (soundEnabled) playTone('pass');
      }
    }, 420);
  };

  on(evalBtn, 'click', () => evaluateGateCommand(evalInput?.value || ''));
  on(evalInput, 'keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      evaluateGateCommand(evalInput.value);
    }
  });

  // -----------------------------------------------------------------------
  // Rollback
  // -----------------------------------------------------------------------
  const rollbackBtn = byId('rollbackBtn');
  on(rollbackBtn, 'click', () => {
    cleanupTimer(rollbackResetTimer);
    setState('ROLLBACK', true);
    const original = rollbackBtn.querySelector('span');
    const originalText = original?.textContent || 'Execute Surgical Rollback';
    safeText(original, 'Rollback complete ✓');
    rollbackBtn.classList.add('success-state');
    rollbackResetTimer = window.setTimeout(() => {
      rollbackBtn.classList.remove('success-state');
      safeText(original, originalText);
    }, 1800);
  });

  // -----------------------------------------------------------------------
  // Video tour (current React modal)
  // -----------------------------------------------------------------------
  const videoModal = byId('videoModal');
  const vmTitle = byId('vmTitle');
  const vmCloseBtn = byId('vmCloseBtn');
  videoCanvas = byId('cinemaCanvas');
  videoCanvasContext = videoCanvas?.getContext?.('2d') || null;
  let videoStars = [];

  const resizeVideoCanvas = () => {
    if (!videoCanvas || !videoCanvasContext) return;
    const rect = videoCanvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    videoCanvasSize = { width: Math.max(1, rect.width), height: Math.max(1, rect.height), dpr };
    videoCanvas.width = Math.floor(videoCanvasSize.width * dpr);
    videoCanvas.height = Math.floor(videoCanvasSize.height * dpr);
    videoCanvasContext.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!videoStars.length) {
      videoStars = Array.from({ length: 110 }, (_, index) => ({
        x: (index * 71) % videoCanvasSize.width,
        y: (index * 127) % videoCanvasSize.height,
        r: 0.6 + (index % 3) * 0.4,
        z: 0.2 + (index % 7) / 10
      }));
    }
  };

  const updateVideoModal = () => {
    if (videoModal) {
      videoModal.classList.toggle('open', videoMode);
      videoModal.setAttribute('aria-hidden', String(!videoMode));
    }
    const chapterIndex = VIDEO_CHAPTERS.findIndex(chapter => videoTime >= chapter.start && videoTime < chapter.end);
    const index = chapterIndex === -1 ? VIDEO_CHAPTERS.length - 1 : chapterIndex;
    const chapter = VIDEO_CHAPTERS[index];
    safeText(vmTitle, chapter ? `${chapter.name} / ${String(Math.floor(videoTime)).padStart(2, '0')}s` : 'AEGIS / CINEMATIC TOUR');
  };

  const renderVideo = now => {
    if (destroyed || !videoMode || !videoCanvasContext) return;
    const ctx = videoCanvasContext;
    const { width, height } = videoCanvasSize;
    ctx.clearRect(0, 0, width, height);

    const gradient = ctx.createRadialGradient(width / 2, height / 2, 20, width / 2, height / 2, Math.max(width, height) * 0.8);
    gradient.addColorStop(0, '#24231f');
    gradient.addColorStop(1, '#0d0d0c');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    const progress = videoTime / VIDEO_DURATION;
    const centerX = width / 2 + Math.sin(now * 0.0007) * 22;
    const centerY = height / 2 + Math.cos(now * 0.0005) * 15;
    const rings = 5;
    for (let i = 0; i < rings; i += 1) {
      const radius = 70 + i * 48 + progress * 60;
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, radius, radius * (0.72 + i * 0.025), now * 0.0004 + i * 0.24, 0, TAU);
      ctx.strokeStyle = i === Math.min(3, Math.floor(progress * rings)) ? 'rgba(255,79,47,0.85)' : 'rgba(244,241,235,0.17)';
      ctx.lineWidth = i === 0 ? 2 : 1;
      ctx.stroke();
    }

    videoStars.forEach(star => {
      const px = (star.x + progress * width * star.z * 0.35) % width;
      ctx.fillStyle = `rgba(244,241,235,${0.15 + star.z * 0.4})`;
      ctx.beginPath();
      ctx.arc(px, star.y, star.r, 0, TAU);
      ctx.fill();
    });

    ctx.font = '11px JetBrains Mono, monospace';
    ctx.fillStyle = 'rgba(244,241,235,0.55)';
    ctx.fillText(`AEGIS / LIVE TOUR / ${String(Math.floor(progress * 100)).padStart(2, '0')}%`, 24, 30);

    if (videoPlaying) {
      const delta = (now - lastVideoTick) / 1000;
      lastVideoTick = now;
      videoTime = Math.min(VIDEO_DURATION, videoTime + delta * videoSpeed);
      const chapterIndex = VIDEO_CHAPTERS.findIndex(chapter => videoTime >= chapter.start && videoTime < chapter.end);
      if (chapterIndex !== lastChapter) {
        lastChapter = chapterIndex;
        const chapter = VIDEO_CHAPTERS[chapterIndex];
        if (chapter) {
          setState(chapter.state, true);
          byId(chapter.target)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
      updateVideoModal();
      if (videoTime >= VIDEO_DURATION) {
        videoTime = VIDEO_DURATION;
        videoPlaying = false;
      }
    }

    videoRaf = window.requestAnimationFrame(renderVideo);
  };

  const launchVideo = () => {
    videoMode = true;
    videoPlaying = true;
    videoTime = 0;
    lastChapter = -1;
    lastVideoTick = performance.now();
    document.body.classList.add('in-video-mode');
    resizeVideoCanvas();
    updateVideoModal();
    cancelAnimationFrame(videoRaf);
    videoRaf = window.requestAnimationFrame(renderVideo);
    playTone('pass');
  };

  const exitVideo = () => {
    videoMode = false;
    videoPlaying = false;
    document.body.classList.remove('in-video-mode');
    if (videoModal) {
      videoModal.classList.remove('open');
      videoModal.setAttribute('aria-hidden', 'true');
    }
    cancelAnimationFrame(videoRaf);
  };

  on(byId('videoTourBtn'), 'click', launchVideo);
  on(vmCloseBtn, 'click', exitVideo);
  on(videoModal, 'click', event => {
    if (event.target === videoModal) exitVideo();
  });

  // -----------------------------------------------------------------------
  // Navigation helpers / cleanup-friendly keyboard support
  // -----------------------------------------------------------------------
  on(window, 'keydown', event => {
    if (event.key === 'Escape' && videoMode) {
      exitVideo();
      return;
    }
    if ((event.key === 'm' || event.key === 'M') && soundToggle) soundToggle.click();
  });

  on(window, 'resize', () => {
    resizeEngineCanvas();
    worldSize = resize2DCanvas(worldCanvas, worldCtx) || worldSize;
    resize2DCanvas(trailCanvas, trailCtx);
    resizeVideoCanvas();
  }, { passive: true });

  try {
    initWebGL();
  } catch (error) {
    console.warn('[Aegis] WebGL engine unavailable; continuing with the rest of the page.', error);
  }

  resizeEngineCanvas();
  setState('IDLE', false);
  updateScrollProgress();
  worldRaf = window.requestAnimationFrame(renderWorld);
  cursorRaf = window.requestAnimationFrame(renderCursor);
  if (gl && shaderProgram) engineRaf = window.requestAnimationFrame(renderEngine);

  cleanups.push(() => {
    destroyed = true;
    abortController.abort();
    cleanupTimer(demoTimer);
    startDemo?.setAttribute('aria-busy', 'false');
    cleanupTimer(gateTimer);
    cleanupTimer(rollbackResetTimer);
    cleanupTimer(demoResetTimer);
    cleanupTimer(shockwaveTimer);
    cancelAnimationFrame(engineRaf);
    cancelAnimationFrame(worldRaf);
    cancelAnimationFrame(cursorRaf);
    cancelAnimationFrame(videoRaf);
    document.body.classList.remove('in-video-mode');
    if (audioContext) audioContext.close?.().catch?.(() => {});
    if (gl) {
      if (positionBuffer) gl.deleteBuffer(positionBuffer);
      if (colorBuffer) gl.deleteBuffer(colorBuffer);
      if (shaderProgram) gl.deleteProgram(shaderProgram);
    }
    trailParticles.length = 0;
  });

  return () => cleanups.forEach(cleanup => cleanup());
}
