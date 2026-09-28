import React, { useEffect, useMemo, useState } from 'react';
import TechText from './components/TechText';
import GhostFibers from './components/GhostFibers';
import WebThreads from './components/WebThreads';
import ClickSpark from './components/ClickSpark';
import FlowingMenu from './components/FlowingMenu';
import MagicRings from './components/MagicRings';
import OptionWheel from './components/OptionWheel';
import { initAegisEngine } from './engine';

const FLOWING_MENU_ITEMS = [
  { link: '#hero', text: 'Overview', image: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600&h=400&fit=crop' },
  { link: '#narrative', text: 'Verification Cycle', image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=600&h=400&fit=crop' },
  { link: '#gateguard', text: 'GateGuard Barriers', image: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=600&h=400&fit=crop' },
  { link: '#trace', text: 'Trace Timeline', image: 'https://images.unsplash.com/photo-1504639725590-34d0984388bd?q=80&w=600&h=400&fit=crop' },
  { link: '#rollback', text: 'Surgical Rollback', image: 'https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=600&h=400&fit=crop' }
];

const MERKLE_LEAF_DATA = [
  {
    step: '01',
    name: 'Session Init',
    action: 'INIT_ORCHESTRATOR_FSM',
    leafHash: '0x3f9e8a1b4c7d2e5f6a8b9c0d1e2f3a4b5c6d7e8f',
    parentHash: '0x12a9c4b78912e604f321d5890c213456789abcde',
    merklePath: 'L1 ➔ FSM_INIT ➔ STATE_IDLE ➔ ROOT',
    nonce: 100234,
    status: 'FSM_INITIALIZED',
    inodes: 112,
    duration: '0.18ms',
    signature: 'sha256:3f9e8a1b4c7d2e5f6a8b9c0d1e2f3a4b5c6d7e8f // ORCHESTRATOR_INIT',
    summary: 'Orchestrator finite state machine initialized. Project context and configuration loaded from .aegis.yaml with zero unverified mutations.',
    tags: ['PYTHON: 3.12+', 'TESTS: 112 PASS', 'GATES: ARMED']
  },
  {
    step: '02',
    name: 'Gemini Dispatch',
    action: 'INVOKE_GEMINI_CLIENT',
    leafHash: '0x7b2a9d4c1e3f5a8b6c0d2e4f1a3b5c7d9e0f2a4b',
    parentHash: '0x3f9e8a1b4c7d2e5f6a8b9c0d1e2f3a4b5c6d7e8f',
    merklePath: 'L2 ➔ GEMINI_CLIENT ➔ GOOGLE_GENAI ➔ ROOT',
    nonce: 100291,
    status: 'DISPATCH_OK',
    inodes: 18,
    duration: '1.24s',
    signature: 'sha256:7b2a9d4c1e3f5a8b6c0d2e4f1a3b5c7d9e0f2a4b // MODEL_DISPATCH',
    summary: 'GeminiModelClient query executed via google-genai SDK. Protected with 6-attempt exponential backoff and 429/503 resilience.',
    tags: ['MODEL: GEMINI-3.8-FLASH', 'RETRY: BACKOFF', 'TAINT: ZERO']
  },
  {
    step: '03',
    name: 'GateGuard Shield',
    action: 'EVAL_PATH_COMMAND_AST',
    leafHash: '0x8f9a2b4c7d1e3f5a6b8c9d0e1f2a3b4c5d6e7f8a',
    parentHash: '0x7b2a9d4c1e3f5a8b6c0d2e4f1a3b5c7d9e0f2a4b',
    merklePath: 'L3 ➔ GATEGUARD ➔ AST_SCANNER ➔ ROOT',
    nonce: 100348,
    status: 'BARRIER_ENFORCED',
    inodes: 64,
    duration: '0.42ms',
    signature: 'sha256:8f9a2b4c7d1e3f5a6b8c9d0e1f2a3b4c5d6e7f8a // GATEGUARD_OK',
    summary: 'PathGuard, SecretGuard, CommandGuard, and ASTRiskScanner evaluated. Zero traversal, no credential leaks, eval/exec blocked.',
    tags: ['PATHGUARD: PASS', 'COMMANDGUARD: PASS', 'AST_SCAN: CLEAN']
  },
  {
    step: '04',
    name: 'Tool Bus Dispatch',
    action: 'EXECUTE_LOCAL_PATCH',
    leafHash: '0x1c4e9f2a7b8d0c3e5a6f1b4d2e8a0c5f7b9d1e3a',
    parentHash: '0x8f9a2b4c7d1e3f5a6b8c9d0e1f2a3b4c5d6e7f8a',
    merklePath: 'L4 ➔ TOOL_BUS ➔ LOCAL_EXECUTOR ➔ ROOT',
    nonce: 100405,
    status: 'PATCH_APPLIED',
    inodes: 88,
    duration: '2.12ms',
    signature: 'sha256:1c4e9f2a7b8d0c3e5a6f1b4d2e8a0c5f7b9d1e3a // TOOL_PATCH',
    summary: 'Tool Bus executes write_patch in isolated workspace snapshot. Inode mutation recorded with pre-flight checkpoint.',
    tags: ['BACKEND: LOCAL_EXECUTOR', 'FILES_TOUCHED: 1', 'CHECKPOINT: SNAP']
  },
  {
    step: '05',
    name: 'Gate Verification',
    action: 'RUN_VERIFICATION_GATES',
    leafHash: '0x5d8c1b3e9a0f2e4d7a6b8c1f3a5e7d9b0c2e4a6f',
    parentHash: '0x1c4e9f2a7b8d0c3e5a6f1b4d2e8a0c5f7b9d1e3a',
    merklePath: 'L5 ➔ GATES ➔ TEST_RUNNER ➔ ROOT',
    nonce: 100462,
    status: 'ALL_GATES_PASSED',
    inodes: 312,
    duration: '840ms',
    signature: 'sha256:5d8c1b3e9a0f2e4d7a6b8c1f3a5e7d9b0c2e4a6f // GATES_VERIFIED',
    summary: 'Pre-flight compilation, ruff linting, and pytest test suite executed. Hard state transition confirmed by exit code 0.',
    tags: ['PRE_FLIGHT: PASS', 'LINT: PASS', 'TEST_CMD: PASS']
  },
  {
    step: '06',
    name: 'Verified Commit',
    action: 'COMMIT_VERIFIED_STATE',
    leafHash: '0x9e0a2f4c6b8d1e3a5f7c9b0d2e4a6f8b1c3d5e7a',
    parentHash: '0x5d8c1b3e9a0f2e4d7a6b8c1f3a5e7d9b0c2e4a6f',
    merklePath: 'L6 ➔ FSM_COMPLETED ➔ SESSION_LEDGER ➔ ROOT',
    nonce: 100519,
    status: 'PROVEN_COMPLETED',
    inodes: 4,
    duration: '0.35ms',
    signature: 'sha256:9e0a2f4c6b8d1e3a5f7c9b0d2e4a6f8b1c3d5e7a // VERIFIED_PROMOTION',
    summary: 'Task state transition to COMPLETED confirmed. Episodic memory lesson logged into .aegis/memory.json with zero human intervention.',
    tags: ['STATE: COMPLETED', 'MEMORY: STORED', 'ROLLBACK: DISARMED']
  }
];

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedTraceState, setSelectedTraceState] = useState(2);
  const [copiedHash, setCopiedHash] = useState(false);
  const [stats, setStats] = useState({ faultRate: '0.0', latency: 0, proofs: 0, ready: false });

  useEffect(() => initAegisEngine(), []);

  useEffect(() => {
    const duration = 1100;
    const start = performance.now();
    let raf = 0;
    const update = (now) => {
      const elapsed = now - start;
      const progress = Math.min(1, elapsed / duration);
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setStats({
        faultRate: (ease * 99.9).toFixed(1),
        latency: Math.round(ease * 14),
        proofs: Math.round(ease * 100),
        ready: progress === 1
      });
      if (progress < 1) {
        raf = requestAnimationFrame(update);
      }
    };
    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, []);

  useEffect(() => {
    document.body.classList.toggle('menu-open', menuOpen);
    return () => document.body.classList.remove('menu-open');
  }, [menuOpen]);

  useEffect(() => {
    const onKeyDown = event => {
      if (event.key === 'Escape' && menuOpen) setMenuOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [menuOpen]);

  const activeLeaf = useMemo(() => {
    return MERKLE_LEAF_DATA[selectedTraceState] ?? MERKLE_LEAF_DATA[0];
  }, [selectedTraceState]);

  const handleCopyProof = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(activeLeaf.signature).then(() => {
        setCopiedHash(true);
        setTimeout(() => setCopiedHash(false), 2200);
      }).catch(() => { });
    }
  };

  return (
    <ClickSpark sparkColor="#ff4f2f" sparkSize={12} sparkRadius={20} sparkCount={10} duration={400}>
      <div className="aegis-app">
        <canvas id="world3dBg" className="world-3d-bg" aria-hidden="true"></canvas>

        <div className="scroll-rail" id="scrollRail" aria-hidden="true">
          <div className="scroll-rail-fill" id="scrollRailFill"></div>
        </div>

        <div className="cursor-orb" id="cursorOrb" aria-hidden="true"></div>

        <div className="cursor-3d-rig" id="cursor3DRig" aria-hidden="true">
          <canvas id="cursorTrailCanvas" className="cursor-trail-canvas"></canvas>
          <div className="cursor-3d-reticle" id="cursor3DReticle">
            <div className="cursor-ring-outer"></div>
            <div className="cursor-ring-inner"></div>
            <div className="cursor-crosshair h"></div>
            <div className="cursor-crosshair v"></div>
            <div className="cursor-core-dot"></div>
            <div className="cursor-pulse-ring"></div>
          </div>
        </div>

        <a className="skip-link" href="#story">Skip to verification cycle</a>

        <header className="topbar">
          <div className="topbar-left">
            <a href="#hero" className="brand" aria-label="Aegis home">
              <span className="brand-mark">A</span>
              <span className="brand-name">AEGIS</span>
            </a>
            <span className="brand-sep">/</span>
            <span className="brand-sub">HARNESS</span>
          </div>

          <div className="topbar-center">
            <div className="status-pill" aria-label="Aegis engine status">
              <span className="live-dot"></span>
              <span className="status-label">ENGINE:</span>
              <span className="status-val" id="topbarState">IDLE</span>
              <span className="status-metric" id="topbarMetric">60 FPS</span>
            </div>
          </div>

          <nav className="topbar-actions" aria-label="Main Navigation">
            <a className="nav-link" href="#narrative">Cycle</a>
            <a className="nav-link" href="#gateguard">GateGuard</a>
            <a className="nav-link" href="#trace">Trace</a>
            <a className="nav-link" href="#rollback">Rollback</a>

            <button className="cinema-pill-btn" id="videoTourBtn" type="button" title="Launch Cinematic 3D Video Tour">
              <span className="pulse-play">▶</span>
              <span>Video Tour</span>
            </button>

            <button className="sound-toggle-btn" id="soundToggle" type="button" aria-pressed="false" title="Toggle audio feedback">
              <span className="sound-bars" aria-hidden="true">
                <i></i><i></i><i></i><i></i>
              </span>
              <span className="sound-label">Audio off</span>
            </button>

            <a className="primary-btn compact" href="#install">
              <span>Get Aegis</span>
              <span className="btn-arrow" aria-hidden="true">↓</span>
            </a>

            <button
              className={`hamburger-toggle-btn${menuOpen ? ' is-open' : ''}`}
              onClick={() => setMenuOpen(open => !open)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              aria-controls="aegis-navigation-drawer"
              type="button"
            >
              <span></span>
              <span></span>
              <span></span>
            </button>
          </nav>
        </header>

        <div
          className={`flowing-menu-drawer${menuOpen ? ' is-open' : ''}`}
          id="aegis-navigation-drawer"
          aria-hidden={!menuOpen}
          inert={!menuOpen}
          onClick={() => setMenuOpen(false)}
        >
          <div className="flowing-menu-label">
            <span>AEGIS / NAVIGATION MENU</span>
          </div>
          <FlowingMenu
            items={FLOWING_MENU_ITEMS}
            speed={15}
            bgColor="#1a1a18"
            textColor="#f4f1eb"
            marqueeBgColor="#ff4f2f"
            marqueeTextColor="#1a1a18"
            borderColor="#7f7d78"
            onNavigate={() => setMenuOpen(false)}
          />
        </div>

        <main id="story">
          <section className="hero-stage" id="hero">
            <div className="visual-layer hero-thread-layer" aria-hidden="true">
              <WebThreads
                color1="#1a1a18"
                color2="#ff4f2f"
                color3="#7f7d78"
                speed={0.2}
                threadCount={6}
                frequency={5.0}
                spread={0.18}
                taper={1.0}
                position={0.5}
                fanMode="center"
                backgroundColor="#f4f1eb"
                lightMode={true}
              />
            </div>

            <div className="hero-grid">
              <div className="hero-content">
                <div className="meta-tag">
                  <span className="mono">01 / DETERMINISTIC AGENT</span>
                  <span className="badge">VERIFICATION-FIRST HARNESS</span>
                </div>

                <div className="tech-text-container">
                  <TechText
                    text="AEGIS HARNESS"
                    fontFamily="Inter, sans-serif"
                    fontWeight={800}
                    fontSize={110}
                    color="#1a1a18"
                    accentColor="#ff4f2f"
                    reveal="letter"
                    dashLength={4}
                    dashGap={2}
                    specks={15}
                  />
                </div>

                <h1 className="hero-title visually-hidden">Verify what AI writes. Before it breaks what you built.</h1>

                <p className="hero-headline-sub">
                  Every other AI coding agent terminates when the model says it's done. Aegis refuses this paradigm: it doesn't claim to be done, it proves it.
                </p>

                <p className="hero-body">
                  A deterministic verification-first AI coding agent for Gemini. Hard application-level verification gates, GateGuard security barriers, and transactional rollbacks guarantee only verified code survives.
                </p>

                <div className="hero-actions">
                  <button className="primary-btn" id="startDemoBtn" type="button">
                    <span className="btn-glow"></span>
                    <span>Scrub verification cycle</span>
                    <span className="btn-arrow" aria-hidden="true">→</span>
                  </button>

                  <a className="secondary-btn" href="#gateguard">
                    <span>Inspect GateGuard</span>
                    <span className="btn-icon mono" aria-hidden="true">[04]</span>
                  </a>
                </div>

                <div className="hero-stats">
                  <div className="stat-item">
                    <span className={`stat-num mono${stats.ready ? ' counted' : ''}`} data-target="99.9" data-suffix="%">{stats.faultRate}%</span>
                    <span className="stat-label">Fault Interception Rate</span>
                  </div>
                  <div className="stat-divider"></div>
                  <div className="stat-item">
                    <span className={`stat-num mono${stats.ready ? ' counted' : ''}`} data-target="14" data-suffix="ms">&lt;{stats.latency}ms</span>
                    <span className="stat-label">Average Gate Latency</span>
                  </div>
                  <div className="stat-divider"></div>
                  <div className="stat-item">
                    <span className={`stat-num mono${stats.ready ? ' counted' : ''}`} data-target="100" data-suffix="%">{stats.proofs}%</span>
                    <span className="stat-label">GateGuard Enforcement</span>
                  </div>
                </div>
              </div>

              <div className="hero-visual">
                <div className="engine-card 3d-tilt-card" data-tilt="15">
                  <div className="card-header">
                    <div className="card-dots" aria-hidden="true">
                      <span></span><span></span><span></span>
                    </div>
                    <div className="card-title mono">AEGIS_CORE_V3.9 // LIVE_CHAMBER</div>
                    <div className="card-badge mono" id="engineBadge">STANDBY</div>
                  </div>
                  <div className="canvas-wrapper">
                    <canvas id="engineCanvas" className="engine-canvas" aria-label="Aegis verification chamber visualization"></canvas>
                    <div className="canvas-overlay" aria-hidden="true">
                      <div className="view-tag mono">ISO_VIEW: 45° | LERP: 0.12</div>
                      <div className="view-grid-toggle mono">GRID: ACTIVE</div>
                    </div>
                  </div>
                  <div className="card-footer">
                    <div className="footer-left">
                      <span className="mono label">STATE:</span>
                      <span className="mono val" id="cardStateVal">IDLE</span>
                    </div>
                    <div className="footer-right">
                      <span className="mono label">INTEGRITY:</span>
                      <span className="mono val green" id="cardIntegrityVal">100%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="narrative-stage" id="narrative">
            <div className="visual-layer narrative-fiber-layer" aria-hidden="true">
              <GhostFibers
                lineColor="#1a1a18"
                glowColor="#ff4f2f"
                backgroundColor="#f4f1eb"
                speed={0.2}
                scale={2}
                layers={4}
                lightMode={true}
              />
            </div>

            <div className="narrative-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">02 / WORKFLOW</span>
                  <span className="badge">FINITE STATE MACHINE</span>
                </div>
                <h2 className="section-title">The anatomy of an Aegis verification pass</h2>
                <p className="section-desc">
                  Scrub through the lifecycle of an AI code edit — from Gemini plan generation through verification gates to verified completion.
                </p>
              </div>

              <div className="scrub-control-panel">
                <div className="scrub-panel-header">
                  <span className="scrub-label mono">SCRUB VERIFICATION PHASE // CLICK OR SCROLL TO STEP</span>
                  <div className="scrub-progress-track">
                    <div className="scrub-progress-bar" id="phaseProgressBar"></div>
                  </div>
                </div>
                <div className="scrub-buttons" role="group" aria-label="Verification Cycle States">
                  <button className="scrub-btn active" data-state="IDLE" type="button">
                    <span className="scrub-btn-dot"></span>00 Standby
                  </button>
                  <button className="scrub-btn" data-state="PLAN" type="button">
                    <span className="scrub-btn-dot"></span>01 Plan
                  </button>
                  <button className="scrub-btn" data-state="IMPLEMENT" type="button">
                    <span className="scrub-btn-dot"></span>02 Implement
                  </button>
                  <button className="scrub-btn" data-state="VERIFY" type="button">
                    <span className="scrub-btn-dot"></span>03 Verify
                  </button>
                  <button className="scrub-btn alert" data-state="FAIL" type="button">
                    <span className="scrub-btn-dot"></span>04 Breach
                  </button>
                  <button className="scrub-btn" data-state="DIAGNOSE" type="button">
                    <span className="scrub-btn-dot"></span>05 Diagnose
                  </button>
                  <button className="scrub-btn" data-state="REPAIR" type="button">
                    <span className="scrub-btn-dot"></span>06 Repair
                  </button>
                  <button className="scrub-btn success" data-state="PASS" type="button">
                    <span className="scrub-btn-dot"></span>07 Completed
                  </button>
                </div>
              </div>

              <div className="state-narrative-card">
                <div className="state-card-main">
                  <div className="state-badge-row">
                    <span className="phase-kicker mono" id="phaseKicker">PHASE 00 / STANDBY</span>
                    <span className="phase-status-badge mono" id="phaseBadge">SYSTEM READY</span>
                  </div>
                  <h3 className="phase-word" id="phaseWord">READY</h3>
                  <p className="phase-detail" id="phaseDetail">Scroll or run demo to scrub the verification cycle.</p>
                </div>

                <div className="phase-telemetry-deck">
                  <div className="phase-metrics-grid">
                    <div className="metric-box">
                      <div className="m-header">
                        <span className="m-label mono">AST DELTA RISK</span>
                        <span className="m-val mono" id="astRiskVal">0.00%</span>
                      </div>
                      <div className="m-bar-bg">
                        <div className="m-bar-fill" id="astRiskFill" style={{ width: '0%' }}></div>
                      </div>
                    </div>
                    <div className="metric-box">
                      <div className="m-header">
                        <span className="m-label mono">GATE COVERAGE</span>
                        <span className="m-val mono" id="coverageVal">100%</span>
                      </div>
                      <div className="m-bar-bg">
                        <div className="m-bar-fill green" id="coverageFill" style={{ width: '100%' }}></div>
                      </div>
                    </div>
                    <div className="metric-box">
                      <div className="m-header">
                        <span className="m-label mono">VERIFICATION GATES</span>
                        <span className="m-val mono" id="assertionsVal">ALL GATES PASS</span>
                      </div>
                      <div className="m-bar-bg">
                        <div className="m-bar-fill blue" style={{ width: '100%' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="gateguard-stage" id="gateguard">
            <div className="visual-layer gateguard-rings-layer" aria-hidden="true">
              <MagicRings
                color="#1a1a18"
                colorTwo="#ff4f2f"
                ringCount={6}
                speed={0.8}
                attenuation={14}
                lineThickness={1.6}
                baseRadius={0.3}
                radiusStep={0.08}
                followMouse={true}
                mouseInfluence={0.2}
                hoverScale={1.12}
                parallax={0.06}
                clickBurst={true}
                alphaMode="coverage"
              />
            </div>

            <div className="gateguard-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">03 / SECURITY BARRIER</span>
                  <span className="badge">GATEGUARD DEFENSE</span>
                </div>
                <h2 className="section-title">Deterministic protection against unsafe actions and security leaks</h2>
                <p className="section-desc">
                  GateGuard evaluates every agent tool call through a strict four-layer defense pipeline before execution.
                </p>
              </div>

              <div className="gateguard-grid">
                <div className="gateguard-card">
                  <div className="card-icon mono">[G1]</div>
                  <h3>PathGuard</h3>
                  <p>Blocks directory traversal (../, %2e%2e), symlink escapes, and protected paths (.git/**, .env*, secrets/**).</p>
                </div>
                <div className="gateguard-card">
                  <div className="card-icon mono">[G2]</div>
                  <h3>SecretGuard</h3>
                  <p>Strips API keys, high-entropy tokens, and credentials from subprocess environments, logs, and traces.</p>
                </div>
                <div className="gateguard-card">
                  <div className="card-icon mono">[G3]</div>
                  <h3>CommandGuard</h3>
                  <p>Safe shlex tokenization blocks shell chaining (&&, ;, |), substitution ($()), sudo, and destructive commands.</p>
                </div>
                <div className="gateguard-card">
                  <div className="card-icon mono">[G4]</div>
                  <h3>ASTRiskScanner</h3>
                  <p>Statically inspects Python patches before disk write; blocks dynamic code execution (eval, exec, __import__).</p>
                </div>
              </div>

              <div className="terminal-card">
                <div className="terminal-head">
                  <span className="terminal-title mono">GATEGUARD_EVALUATOR // LIVE_TERMINAL</span>
                  <span className="terminal-status mono" id="diagAudioStatus">MUTED</span>
                </div>
                <div className="terminal-body">
                  <div className="term-line mono"><span className="term-prompt">$</span> Enter command to test GateGuard evaluation:</div>
                  <div className="term-input-row">
                    <input type="text" className="term-input mono" id="evalInput" defaultValue="rm -rf /" placeholder="Type command..." aria-label="Command to evaluate" />
                    <button className="primary-btn compact" id="evalBtn" type="button">Evaluate</button>
                  </div>
                  <div className="term-output mono" id="evalOutput" role="status" aria-live="polite">
                    [GATEGUARD] Intercepted dangerous command: 'rm -rf /'. Action: BLOCKED. Risk score: 1.00.
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="trace-stage" id="trace">
            <div className="trace-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">04 / AUDIT LEDGER</span>
                  <span className="badge highlight-badge">SESSION EXECUTION TRACE</span>
                </div>
                <h2 className="section-title">Audit trace &amp; execution timeline inspector</h2>
                <p className="section-desc">
                  Every prompt, tool execution, gate evaluation, and repair attempt is recorded in a tamper-evident telemetry stream. Scrub the wheel to inspect each stage.
                </p>
              </div>

              <div className="trace-console-deck">
                <div className="console-topbar">
                  <div className="console-topbar-left">
                    <span className="console-live-dot"></span>
                    <span className="console-title mono">AEGIS_LEDGER // SESSION_TRACE_TELEMETRY</span>
                  </div>
                  <div className="console-topbar-right">
                    <span className="console-pill mono">ROOT: FSM_IDLE</span>
                    <span className="console-pill green mono">GATES: 100% VERIFIED</span>
                    <span className="console-pill badge-seal mono">GEMINI 3.8 FLASH</span>
                  </div>
                </div>

                <div className="trace-console-body">
                  <div className="console-wheel-column">
                    <div className="wheel-column-header">
                      <span className="wheel-sub mono">STAGE SELECTOR</span>
                      <span className="wheel-hint mono">DRAG OR SCROLL WHEEL</span>
                    </div>

                    <div className="option-wheel-wrapper dark-theme">
                      <div className="wheel-fade-overlay top"></div>
                      <OptionWheel
                        items={MERKLE_LEAF_DATA.map(d => `${d.step}. ${d.name}`)}
                        defaultSelected={selectedTraceState}
                        textColor="#68655e"
                        activeColor="#ff4f2f"
                        side="left"
                        fontSize={2.0}
                        spacing={1.35}
                        curve={0.9}
                        tilt={5}
                        blur={1.4}
                        fade={0.35}
                        onChange={setSelectedTraceState}
                      />
                      <div className="wheel-fade-overlay bottom"></div>
                    </div>

                    <div className="wheel-indicator-track">
                      {MERKLE_LEAF_DATA.map((item, idx) => (
                        <button
                          key={item.step}
                          className={`wheel-step-dot${selectedTraceState === idx ? ' active' : ''}`}
                          onClick={() => setSelectedTraceState(idx)}
                          type="button"
                          title={`Switch to ${item.name}`}
                        >
                          <span className="mono">{item.step}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="console-topology-column">
                    <div className="topology-header">
                      <span className="topology-title mono">FSM STATE TRANSITION TOPOLOGY</span>
                    </div>

                    <div className="topology-graph">
                      <div className="topo-node root-node">
                        <div className="node-badge mono">SESSION ROOT</div>
                        <div className="node-hash mono">AEGIS_INIT</div>
                      </div>

                      <div className="topo-connector">
                        <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="topo-svg-line">
                          <line x1="50" y1="0" x2="50" y2="40" stroke="rgba(255, 79, 47, 0.45)" strokeWidth="2" strokeDasharray="3 3" />
                        </svg>
                      </div>

                      <div className="topo-node branch-node">
                        <div className="node-badge mono">PARENT STATE</div>
                        <div className="node-hash mono">{activeLeaf.parentHash.slice(0, 14)}...</div>
                      </div>

                      <div className="topo-connector">
                        <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="topo-svg-line">
                          <line x1="50" y1="0" x2="50" y2="40" stroke="rgba(255, 79, 47, 0.75)" strokeWidth="2" />
                        </svg>
                      </div>

                      <div className="topo-node active-leaf-node">
                        <div className="node-pulse-ring"></div>
                        <div className="node-badge accent mono">ACTIVE STAGE #{activeLeaf.step}</div>
                        <div className="node-name">{activeLeaf.name}</div>
                        <div className="node-hash mono">{activeLeaf.leafHash.slice(0, 16)}...</div>
                      </div>
                    </div>

                    <div className="topology-path-readout mono">
                      <span className="path-label">PATH:</span>
                      <span className="path-val">{activeLeaf.merklePath}</span>
                    </div>
                  </div>

                  <div className="console-inspector-column">
                    <div className="inspector-card">
                      <div className="inspector-header">
                        <div className="ins-badge-row">
                          <span className="ins-step-tag mono">STAGE #{activeLeaf.step}</span>
                          <span className="ins-status-badge mono">{activeLeaf.status}</span>
                        </div>
                        <h3 className="ins-title">{activeLeaf.name}</h3>
                        <div className="ins-action-code mono">{activeLeaf.action}</div>
                      </div>

                      <p className="ins-summary">{activeLeaf.summary}</p>

                      <div className="ins-telemetry-grid">
                        <div className="ins-metric-box">
                          <span className="ins-m-label mono">NONCE AUDIT</span>
                          <span className="ins-m-val mono">#{activeLeaf.nonce}</span>
                        </div>
                        <div className="ins-metric-box">
                          <span className="ins-m-label mono">EXEC LATENCY</span>
                          <span className="ins-m-val mono green">{activeLeaf.duration}</span>
                        </div>
                        <div className="ins-metric-box">
                          <span className="ins-m-label mono">INODES SCANNED</span>
                          <span className="ins-m-val mono">{activeLeaf.inodes}</span>
                        </div>
                      </div>

                      <div className="ins-signature-block">
                        <div className="sig-header">
                          <span className="sig-label mono">CRYPTOGRAPHIC SIGNATURE (ED25519)</span>
                          <button
                            type="button"
                            className="sig-copy-btn mono"
                            onClick={handleCopyProof}
                            title="Copy proof signature"
                          >
                            {copiedHash ? '✓ COPIED' : 'COPY'}
                          </button>
                        </div>
                        <code className="sig-content mono">{activeLeaf.signature}</code>
                      </div>

                      <div className="ins-tag-list">
                        {activeLeaf.tags.map((tag, i) => (
                          <span key={i} className="ins-tag mono">{tag}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="rollback-stage" id="rollback">
            <div className="rollback-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">05 / RESTORATION</span>
                  <span className="badge">SURGICAL REVERT</span>
                </div>
                <h2 className="section-title">Surgical transactional rollback without losing untracked work</h2>
                <p className="section-desc">
                  When repairs exhaust, Aegis reverts only the files it touched — preserving pre-existing modifications, working tree state, and developer logs.
                </p>
              </div>

              <div className="diff-viewer-card">
                <div className="diff-header">
                  <span className="diff-title mono">PATCH_DIFF // src/auth_service.py</span>
                  <span className="diff-status mono text-alert">VERIFICATION GATE FAILED: test_cmd</span>
                </div>
                <div className="diff-body mono">
                  <div className="diff-line del">-  def validate_token(token: str) -&gt; bool:</div>
                  <div className="diff-line add">+  def validate_token(token: str = None) -&gt; bool:  # Model bug: bypassed gate</div>
                  <div className="diff-line plain">       return jwt_verify(token, secret_key)</div>
                </div>
                <div className="diff-footer">
                  <button className="primary-btn alert-btn" id="rollbackBtn" type="button">
                    <span>Execute Surgical Rollback</span>
                  </button>
                  <span className="diff-note mono">Zero Developer Disruption Guarantee</span>
                </div>
              </div>
            </div>
          </section>

          <section className="install-stage" id="install">
            <div className="install-container">
              <h2 className="install-title">Ready to run a deterministic AI coding agent?</h2>
              <p className="install-desc">Install Aegis in 60 seconds with pip and set your Gemini API key.</p>
              <div className="code-box mono">
                <code>pip install aegis-harness</code>
              </div>
            </div>
          </section>
        </main>

        <footer className="footer">
          <div className="footer-container">
            <div className="footer-brand">
              <span className="brand-mark">A</span>
              <span className="brand-name">AEGIS</span>
              <span className="brand-copy mono">© 2026 AEGIS HARNESS. OPEN SOURCE UNDER MIT LICENSE.</span>
            </div>
          </div>
        </footer>

        <div className="video-modal-overlay" id="videoModal" role="dialog" aria-modal="true" aria-labelledby="vmTitle" aria-hidden="true">
          <div className="video-modal-container">
            <div className="video-modal-header">
              <div className="vm-title-group">
                <span className="vm-badge mono">3D CINEMATIC TOUR</span>
                <span className="vm-title" id="vmTitle">CHAPTER 01 / ARCHITECTURE OVERVIEW</span>
              </div>
              <button className="vm-close-btn" id="vmCloseBtn" type="button" aria-label="Close Tour">×</button>
            </div>
            <div className="video-modal-body">
              <canvas id="cinemaCanvas" className="cinema-canvas" aria-label="Aegis cinematic tour visualization"></canvas>
            </div>
          </div>
        </div>
      </div>
    </ClickSpark>
  );
}
