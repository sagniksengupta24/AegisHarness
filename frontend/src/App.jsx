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
  { link: '#paradigm', text: 'Hard Gate Paradigm', image: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?q=80&w=600&h=400&fit=crop' },
  { link: '#narrative', text: 'Verification Cycle', image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=600&h=400&fit=crop' },
  { link: '#gateguard', text: 'GateGuard Barriers', image: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=600&h=400&fit=crop' },
  { link: '#trace', text: 'Trace Timeline', image: 'https://images.unsplash.com/photo-1504639725590-34d0984388bd?q=80&w=600&h=400&fit=crop' },
  { link: '#rollback', text: 'Surgical Rollback', image: 'https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=600&h=400&fit=crop' },
  { link: '#quickstart', text: 'Quickstart & Install', image: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=600&h=400&fit=crop' },
  { link: '#cli-reference', text: 'CLI Reference', image: 'https://images.unsplash.com/photo-1629654297299-c8506221ca97?q=80&w=600&h=400&fit=crop' },
  { link: '#config-skills', text: 'Config & Skills', image: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=600&h=400&fit=crop' },
  { link: '#matrix', text: 'Verification Matrix', image: 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?q=80&w=600&h=400&fit=crop' }
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

const CLI_COMMANDS = [
  {
    cmd: 'aegis init',
    tag: 'SCAFFOLDING',
    title: 'Initialize Aegis in Any Repository',
    desc: 'Auto-detects project stack (Python, Node.js, TypeScript, React, Next.js, Go, Rust), creates a documented .aegis.yaml, provisions .aegis/skills/ and .aegis/traces/, and generates .vscode/tasks.json for seamless IDE integration.',
    usage: 'aegis init',
    flags: [
      { name: '--stack <stack>', desc: 'Manually specify project stack (python, node, typescript, go, rust, generic)' },
      { name: '--force', desc: 'Overwrite existing .aegis.yaml if already present' }
    ],
    invariant: 'Invariant: Zero mutations to existing project code during initialization.',
    output: `[AEGIS] Scanning repository workspace...
[AEGIS] Detected stack: Python 3.12+ (pytest, ruff)
[AEGIS] Generated .aegis.yaml with fail-closed verification defaults
[AEGIS] Created .aegis/skills/ and .aegis/traces/
[AEGIS] Generated .vscode/tasks.json (Aegis Run, Aegis Verify, Aegis Commit)
[AEGIS] Repository armed for deterministic verification.`
  },
  {
    cmd: 'aegis run',
    tag: 'EXECUTION',
    title: 'Run Agent Task with Verification Loop',
    desc: 'Plans with Gemini 3.8 Flash, applies atomic code patches, and evaluates all configured verification gates. Only declares success when exit code 0 is proven across all required gates.',
    usage: 'aegis run --task "<instruction>" [--interactive]',
    flags: [
      { name: '--task <str>', desc: 'Required task prompt/instruction for the agent' },
      { name: '--interactive', desc: 'Shows unified diff; requires explicit human approval before any write' },
      { name: '--model <model>', desc: 'Override active model (e.g. gemini-3.5-flash)' }
    ],
    invariant: 'Invariant: Cannot exit to COMPLETED without passing all verification gates.',
    output: `[AEGIS] State: PLAN -> Formulated task specification with Gemini 3.8 Flash
[AEGIS] State: IMPLEMENT -> Applied patch to src/auth/signup.py
[AEGIS] State: VERIFY -> Running pre_flight, ruff lint, pytest test suite...
[AEGIS] Gate pre_flight: PASS (0.12s)
[AEGIS] Gate lint: PASS (0.34s)
[AEGIS] Gate test_cmd: PASS (tests/test_signup.py: 6 passed in 0.82s)
[AEGIS] GateGuard: NO SECURITY VIOLATIONS
[AEGIS] State: COMPLETED (Proof: 0x9e0a2f4c6b8d1e3a)`
  },
  {
    cmd: 'aegis verify',
    tag: 'GATES',
    title: 'Run Verification Suite (Zero LLM)',
    desc: 'Executes the full configured gate pipeline (pre_flight, lint, test_cmd, build_cmd) directly against the workspace without invoking the LLM. Displays exit codes, durations, and captured stdout/stderr.',
    usage: 'aegis verify',
    flags: [
      { name: '--verbose', desc: 'Show complete stdout/stderr even on passing gates' },
      { name: '--gate <name>', desc: 'Run only a specific gate (e.g. test_cmd)' }
    ],
    invariant: 'Invariant: Fast deterministic feedback loop with zero token consumption.',
    output: `[VERIFY] Evaluating configured gates from .aegis.yaml:
  ✔ pre_flight: python3 -m py_compile src/**/*.py (0.09s, exit 0)
  ✔ lint: ruff check . (0.28s, exit 0)
  ✔ test_cmd: pytest tests/ -q (0.76s, exit 0 - 112 passed)
  - build_cmd: [skipped - not configured]
[VERIFY] ALL REQUIRED GATES PASSED (Total: 1.13s)`
  },
  {
    cmd: 'aegis commit',
    tag: 'VERSIONING',
    title: 'Gate-Enforced Commit with Episodic Memory',
    desc: 'Stages and commits changes only after all verification gates pass. Optionally stores a distilled engineering lesson into persistent episodic memory (.aegis/memory.json) for future sessions.',
    usage: 'aegis commit -m "<msg>" [--lesson "<text>"]',
    flags: [
      { name: '-m <message>', desc: 'Git commit message' },
      { name: '--lesson <text>', desc: 'Engineering takeaway stored in .aegis/memory.json' },
      { name: '--dry-run', desc: 'Preview what would be committed without writing to git' },
      { name: '-y, --yes', desc: 'Bypass interactive confirmation prompt' }
    ],
    invariant: 'Invariant: Aegis NEVER auto-commits. Confirmation or -y flag is always required.',
    output: `[COMMIT] Running verification gates prior to commit... PASS
[COMMIT] Staged 3 touched files. Pre-existing untracked files preserved.
[COMMIT] Commit created: 64596ae ("feat: add token bucket rate limiter")
[MEMORY] Distilled lesson logged: "Rate limiters must handle zero burst; always test edge cases"
[MEMORY] Injected into .aegis/memory.json (top_k retrieval active)`
  },
  {
    cmd: 'aegis memory',
    tag: 'LEARNING',
    title: 'Manage Episodic Project Memory',
    desc: 'Lists, inspects, and adds persistent lessons stored in .aegis/memory.json. Lessons are retrieved and injected into new session prompts while maintaining untrusted memory invariants (sanitized against prompt injection).',
    usage: 'aegis memory [list|add]',
    flags: [
      { name: 'list', desc: 'Print stored lessons, tags, and hit frequencies' },
      { name: '--lesson <text>', desc: 'Lesson content to store' },
      { name: '--tags <csv>', desc: 'Comma-separated tags for relevance matching' }
    ],
    invariant: 'Invariant: Memory informs the agent; it can NEVER override security guards.',
    output: `[MEMORY] Stored lessons in .aegis/memory.json:
  [#01] "Always run pytest with -q flag in CI" (tags: pytest, ci)
  [#02] "DB connection pool exhausts under load; set pool_size=10 in tests" (tags: database, testing)
  [#03] "Rate limiters must handle zero burst; always test edge cases" (tags: ratelimit, auth)
[MEMORY] 3 lessons loaded. Prompt injection sanitizer armed.`
  },
  {
    cmd: 'aegis daemon',
    tag: 'SERVICE',
    title: 'Background Daemon & IPC Concurrency',
    desc: 'Starts a background daemon communicating over a secure Unix domain socket (mode 0600) with TCP fallback. Supports non-blocking ping, status, verify, run, and task cancellation.',
    usage: 'aegis daemon [start|status|stop]',
    flags: [
      { name: 'start', desc: 'Launch daemon in background' },
      { name: 'status', desc: 'Query daemon health, active session ID, and uptime' },
      { name: 'stop', desc: 'Gracefully shutdown daemon process' }
    ],
    invariant: 'Invariant: Socket permissions restricted to user mode 0600 to prevent local IPC tampering.',
    output: `[DAEMON] Starting Aegis daemon on /tmp/aegis-harness.sock...
[DAEMON] Socket permissions: 0600 (owner-only access)
[DAEMON] Background worker armed. Listening for IPC requests...
[DAEMON] Status: RUNNING (PID 49120, Memory: 28MB, Uptime: 0m)`
  }
];

const VERIFICATION_MATRIX = [
  { component: 'Core state machine & lifecycle', category: 'core', status: 'VERIFIED', evidence: 'IDLE→PLAN→IMPLEMENT→VERIFY→COMPLETE/ABORT unit tests' },
  { component: 'Fail-closed verification engine', category: 'core', status: 'VERIFIED', evidence: 'Gate evaluation, non-zero exits, timeouts, error snippets' },
  { component: 'Surgical rollback & checkpointing', category: 'core', status: 'VERIFIED', evidence: 'Reverts session changes; preserves pre-existing user files' },
  { component: 'Interactive diff approval', category: 'core', status: 'VERIFIED', evidence: 'Diff display + prompt before any filesystem write' },
  { component: 'CommandGuard & chaining', category: 'security', status: 'VERIFIED', evidence: ';, &&, ||, |, &, $(), backtick, fork bomb blocked' },
  { component: 'PathGuard & traversal', category: 'security', status: 'VERIFIED', evidence: 'Symlinks, nested links, %2e%2e, case variants blocked' },
  { component: 'Secret sanitization', category: 'security', status: 'VERIFIED', evidence: 'Scrubbing across stdout, stderr, logs, traces, memory' },
  { component: 'Episodic memory deduplication', category: 'core', status: 'VERIFIED', evidence: '20× dedup, prompt injection sanitization, corrupt JSON handling' },
  { component: 'Task cancellation & abort', category: 'core', status: 'VERIFIED', evidence: 'Threaded + daemon cancel → ABORTED + rollback' },
  { component: 'Daemon & IPC concurrency', category: 'core', status: 'VERIFIED', evidence: 'Unix socket/TCP, real task dispatch, cancel, malformed requests' },
  { component: 'MCP tool adapter & policy proxy', category: 'security', status: 'VERIFIED', evidence: 'Schema wrapping, GateGuard enforcement, output scrubbing' },
  { component: 'Antigravity workspace integration', category: 'core', status: 'CONFIG VERIFIED', evidence: 'Rules frontmatter, skill structure, VS Code tasks verified' },
  { component: 'Packaging & clean install', category: 'core', status: 'VERIFIED', evidence: 'Wheel built with python -m build, installed in clean venv' },
  { component: 'Live Gemini API (multi-turn)', category: 'live', status: 'LIVE VERIFIED', evidence: 'Real gemini-3.5-flash → tool calls → file creation → verify PASS' },
  { component: 'Live E2E success path', category: 'live', status: 'LIVE VERIFIED', evidence: 'Gemini → Orchestrator → write_patch → run_verification → COMPLETED' },
  { component: 'Live E2E repair loop', category: 'live', status: 'LIVE VERIFIED', evidence: 'Bug seeded → verify FAIL → Gemini diagnoses → patches → verify PASS' },
  { component: '503 overload resilience', category: 'live', status: 'LIVE VERIFIED', evidence: 'Exponential backoff (15s base + jitter) fired, recovered, session completed' },
  { component: 'Live Docker container', category: 'live', status: 'LIVE VERIFIED', evidence: 'Container exec, volume mount, timeout, --network none isolation' }
];

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedTraceState, setSelectedTraceState] = useState(2);
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedSnippetId, setCopiedSnippetId] = useState(null);
  const [quickstartTab, setQuickstartTab] = useState('quickstart');
  const [selectedCliCommand, setSelectedCliCommand] = useState(0);
  const [matrixFilter, setMatrixFilter] = useState('all');
  const [configTab, setConfigTab] = useState('yaml');
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

  const handleCopySnippet = (text, id) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedSnippetId(id);
        setTimeout(() => setCopiedSnippetId(null), 2000);
      }).catch(() => { });
    }
  };

  const filteredMatrix = useMemo(() => {
    if (matrixFilter === 'all') return VERIFICATION_MATRIX;
    return VERIFICATION_MATRIX.filter(item => item.category === matrixFilter);
  }, [matrixFilter]);

  const activeCli = CLI_COMMANDS[selectedCliCommand] || CLI_COMMANDS[0];

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
            <span id="cursorMode" className="visually-hidden">DEFAULT</span>
            <span id="cursorCoords" className="visually-hidden">X: 0 Y: 0</span>
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
            <a className="nav-link" href="#paradigm">Paradigm</a>
            <a className="nav-link" href="#narrative">Cycle</a>
            <a className="nav-link" href="#gateguard">GateGuard</a>
            <a className="nav-link" href="#quickstart">Quickstart</a>
            <a className="nav-link" href="#cli-reference">CLI</a>
            <a className="nav-link" href="#matrix">Matrix</a>

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

            <a className="primary-btn compact" href="#quickstart">
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

                <div className="hero-readme-badges">
                  <span className="readme-badge mono">PYTHON 3.12+</span>
                  <span className="readme-badge mono green">112 TESTS PASSING</span>
                  <span className="readme-badge mono live">LIVE E2E VERIFIED</span>
                  <span className="readme-badge mono orange">SECURITY: GATEGUARD</span>
                  <span className="readme-badge mono">LICENSE: MIT</span>
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
                  <a className="primary-btn" href="#quickstart">
                    <span className="btn-glow"></span>
                    <span>Quickstart (60s)</span>
                    <span className="btn-arrow" aria-hidden="true">→</span>
                  </a>

                  <button className="secondary-btn" id="startDemoBtn" type="button">
                    <span>Scrub Cycle</span>
                    <span className="btn-icon mono" aria-hidden="true">[02]</span>
                  </button>
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

          {/* PARADIGM COMPARISON SECTION */}
          <section className="paradigm-stage" id="paradigm">
            <div className="paradigm-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">02 / CORE PHILOSOPHY</span>
                  <span className="badge">DETERMINISTIC INVARIANT</span>
                </div>
                <h2 className="section-title">The problem with every other AI coding agent</h2>
                <p className="section-desc">
                  Every other AI coding agent on the market terminates when the model declares itself finished. Aegis refuses this paradigm entirely: a model claiming success is not a success.
                </p>
              </div>

              <div className="paradigm-grid">
                <div className="paradigm-card other-agents">
                  <div className="paradigm-badge mono">OTHER CODING AGENTS (CURSOR, COPILOT, AIDER)</div>
                  <h3>Model-Claimed Completion</h3>
                  <p>The agent relies on generative self-evaluation. When the model outputs natural language saying it is done, the task ends regardless of real compilation state or broken tests.</p>
                  <div className="paradigm-flow-box alert-box mono">
                    <div className="paradigm-flow-line dim">Model: "I've added the validation logic and tests."</div>
                    <div className="paradigm-flow-line fail">➔ Task marked complete &amp; session closed</div>
                    <div className="paradigm-flow-line fail">✖ Hallucinated correctness</div>
                    <div className="paradigm-flow-line fail">✖ Unexecuted tests or failing exit codes</div>
                    <div className="paradigm-flow-line fail">✖ Undetected directory or secret breaches</div>
                  </div>
                </div>

                <div className="paradigm-card aegis-paradigm">
                  <div className="paradigm-badge mono">AEGIS HARNESS (VERIFICATION-FIRST)</div>
                  <h3>Hard Application-Level Gate Transition</h3>
                  <p>Aegis completion is a checked state transition. The orchestrator cannot skip a state. The only route to COMPLETED requires hard proof across all verification gates.</p>
                  <div className="paradigm-flow-box success-box mono">
                    <div className="paradigm-flow-line pass">Gate: pre_flight ➔ PASS</div>
                    <div className="paradigm-flow-line pass">Gate: lint       ➔ PASS</div>
                    <div className="paradigm-flow-line pass">Gate: test_cmd   ➔ PASS (real test runner exit 0)</div>
                    <div className="paradigm-flow-line pass">Gate: build_cmd  ➔ PASS</div>
                    <div className="paradigm-flow-line pass">Security: GateGuard ➔ NO VIOLATIONS</div>
                    <div className="paradigm-flow-line pass">───────────────────────────────────────</div>
                    <div className="paradigm-flow-line pass">                      ↓ COMPLETED ✓</div>
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
                  <span className="mono">03 / WORKFLOW</span>
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
                  <span className="mono">04 / SECURITY BARRIER</span>
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
                  <p>Blocks directory traversal (../, %2e%2e), symlink escapes, and protected paths (.git/**, .env*, secrets/**, *.pem, *.key, id_rsa*).</p>
                </div>
                <div className="gateguard-card">
                  <div className="card-icon mono">[G2]</div>
                  <h3>SecretGuard</h3>
                  <p>Strips API keys, high-entropy tokens, and credentials from subprocess environments, stdout, stderr, logs, and telemetry traces.</p>
                </div>
                <div className="gateguard-card">
                  <div className="card-icon mono">[G3]</div>
                  <h3>CommandGuard</h3>
                  <p>Safe shlex tokenization blocks shell chaining (&&, ;, |), substitution ($(), backticks), sudo, and destructive commands (rm -rf /, mkfs, fork bombs).</p>
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
                  <span className="mono">05 / AUDIT LEDGER</span>
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
                  <span className="mono">06 / RESTORATION</span>
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

          {/* QUICKSTART & INSTALLATION SECTION */}
          <section className="quickstart-stage" id="quickstart">
            <div className="quickstart-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">07 / GET STARTED</span>
                  <span className="badge highlight-badge">60-SECOND QUICKSTART</span>
                </div>
                <h2 className="section-title">Install &amp; run your first verified agent task</h2>
                <p className="section-desc">
                  Get up and running in under a minute. Aegis supports Python 3.12+, macOS, and Linux with optional container isolation via Docker.
                </p>
              </div>

              <div className="section-tabs-bar" role="tablist">
                <button
                  className={`tab-pill-btn${quickstartTab === 'quickstart' ? ' active' : ''}`}
                  onClick={() => setQuickstartTab('quickstart')}
                  type="button"
                >
                  <span>Quickstart (60s)</span>
                  <span className="tab-pill-badge mono">RECOMMENDED</span>
                </button>
                <button
                  className={`tab-pill-btn${quickstartTab === 'source' ? ' active' : ''}`}
                  onClick={() => setQuickstartTab('source')}
                  type="button"
                >
                  <span>Install from Source</span>
                </button>
                <button
                  className={`tab-pill-btn${quickstartTab === 'pypi' ? ' active' : ''}`}
                  onClick={() => setQuickstartTab('pypi')}
                  type="button"
                >
                  <span>PyPI Package</span>
                </button>
                <button
                  className={`tab-pill-btn${quickstartTab === 'requirements' ? ' active' : ''}`}
                  onClick={() => setQuickstartTab('requirements')}
                  type="button"
                >
                  <span>System Requirements</span>
                </button>
              </div>

              {quickstartTab === 'quickstart' && (
                <>
                  <div className="quickstart-steps-grid">
                    <div className="qs-step-card">
                      <div className="qs-step-header">
                        <div className="qs-step-num mono">01</div>
                        <span className="qs-step-tag mono">CLONE &amp; SETUP</span>
                      </div>
                      <div className="qs-step-title">Clone Repository &amp; Install</div>
                      <p className="qs-step-desc">Create a clean virtual environment and install Aegis in editable mode with all CLI binaries.</p>
                      <div className="code-deck">
                        <div className="code-deck-header">
                          <div className="code-deck-meta">
                            <div className="code-deck-dots"><span></span><span></span><span></span></div>
                            <span className="code-deck-label mono">terminal</span>
                          </div>
                          <button
                            type="button"
                            className={`code-deck-copy-btn${copiedSnippetId === 'step1' ? ' copied' : ''}`}
                            onClick={() => handleCopySnippet('git clone https://github.com/sagniksengupta24/AegisHarness.git && cd Agehesi\npython3 -m venv .venv && source .venv/bin/activate\npip install -e .', 'step1')}
                          >
                            {copiedSnippetId === 'step1' ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>
                        <pre className="code-deck-body">
                          <code>git clone https://github.com/sagniksengupta24/AegisHarness.git && cd Agehesi{'\n'}python3 -m venv .venv && source .venv/bin/activate{'\n'}pip install -e .</code>
                        </pre>
                      </div>
                    </div>

                    <div className="qs-step-card">
                      <div className="qs-step-header">
                        <div className="qs-step-num mono">02</div>
                        <span className="qs-step-tag mono">AUTHENTICATE</span>
                      </div>
                      <div className="qs-step-title">Set Gemini API Key</div>
                      <p className="qs-step-desc">Export your key. SecretGuard actively scrubs this key from logs, subprocess envs, and telemetry.</p>
                      <div className="code-deck">
                        <div className="code-deck-header">
                          <div className="code-deck-meta">
                            <div className="code-deck-dots"><span></span><span></span><span></span></div>
                            <span className="code-deck-label mono">bash</span>
                          </div>
                          <button
                            type="button"
                            className={`code-deck-copy-btn${copiedSnippetId === 'step2' ? ' copied' : ''}`}
                            onClick={() => handleCopySnippet('export GEMINI_API_KEY="your-gemini-api-key"', 'step2')}
                          >
                            {copiedSnippetId === 'step2' ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>
                        <pre className="code-deck-body">
                          <code>export GEMINI_API_KEY="your-gemini-api-key"</code>
                        </pre>
                      </div>
                    </div>

                    <div className="qs-step-card">
                      <div className="qs-step-header">
                        <div className="qs-step-num mono">03</div>
                        <span className="qs-step-tag mono">INIT REPO</span>
                      </div>
                      <div className="qs-step-title">Initialize Inside Project</div>
                      <p className="qs-step-desc">Auto-detects project stack (Python, Node/TS, Go, Rust), creates .aegis.yaml and IDE tasks.</p>
                      <div className="code-deck">
                        <div className="code-deck-header">
                          <div className="code-deck-meta">
                            <div className="code-deck-dots"><span></span><span></span><span></span></div>
                            <span className="code-deck-label mono">terminal</span>
                          </div>
                          <button
                            type="button"
                            className={`code-deck-copy-btn${copiedSnippetId === 'step3' ? ' copied' : ''}`}
                            onClick={() => handleCopySnippet('cd /path/to/your/project\naegis init', 'step3')}
                          >
                            {copiedSnippetId === 'step3' ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>
                        <pre className="code-deck-body">
                          <code>cd /path/to/your/project{'\n'}aegis init</code>
                        </pre>
                      </div>
                    </div>

                    <div className="qs-step-card">
                      <div className="qs-step-header">
                        <div className="qs-step-num mono">04</div>
                        <span className="qs-step-tag mono">EXECUTE</span>
                      </div>
                      <div className="qs-step-title">Run Verified Agent Task</div>
                      <p className="qs-step-desc">Plans, edits, runs your test suite, and only declares victory when all gates pass with exit code 0.</p>
                      <div className="code-deck">
                        <div className="code-deck-header">
                          <div className="code-deck-meta">
                            <div className="code-deck-dots"><span></span><span></span><span></span></div>
                            <span className="code-deck-label mono">terminal</span>
                          </div>
                          <button
                            type="button"
                            className={`code-deck-copy-btn${copiedSnippetId === 'step4' ? ' copied' : ''}`}
                            onClick={() => handleCopySnippet('aegis run --task "Add input validation to the signup endpoint and write tests for it"', 'step4')}
                          >
                            {copiedSnippetId === 'step4' ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>
                        <pre className="code-deck-body">
                          <code>aegis run --task "Add input validation to the signup endpoint and write tests for it"</code>
                        </pre>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {quickstartTab === 'source' && (
                <div className="code-deck">
                  <div className="code-deck-header">
                    <div className="code-deck-meta">
                      <div className="code-deck-dots"><span></span><span></span><span></span></div>
                      <span className="code-deck-label mono">bash // source build &amp; dev dependencies</span>
                    </div>
                    <button
                      type="button"
                      className={`code-deck-copy-btn${copiedSnippetId === 'source' ? ' copied' : ''}`}
                      onClick={() => handleCopySnippet('git clone https://github.com/sagniksengupta24/AegisHarness.git\ncd Agehesi\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -e ".[dev]"\n\n# Verify installation\naegis --help', 'source')}
                    >
                      {copiedSnippetId === 'source' ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="code-deck-body">
                    <code>git clone https://github.com/sagniksengupta24/AegisHarness.git{'\n'}cd Agehesi{'\n'}python3 -m venv .venv{'\n'}source .venv/bin/activate{'\n'}pip install -e ".[dev]"{'\n\n'}# Verify installation{'\n'}aegis --help</code>
                  </pre>
                </div>
              )}

              {quickstartTab === 'pypi' && (
                <div className="code-deck">
                  <div className="code-deck-header">
                    <div className="code-deck-meta">
                      <div className="code-deck-dots"><span></span><span></span><span></span></div>
                      <span className="code-deck-label mono">bash // pypi release</span>
                    </div>
                    <button
                      type="button"
                      className={`code-deck-copy-btn${copiedSnippetId === 'pypi' ? ' copied' : ''}`}
                      onClick={() => handleCopySnippet('pip install aegis-harness\n\n# Test installation\naegis --version', 'pypi')}
                    >
                      {copiedSnippetId === 'pypi' ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="code-deck-body">
                    <code>pip install aegis-harness{'\n\n'}# Test installation{'\n'}aegis --version</code>
                  </pre>
                </div>
              )}

              {quickstartTab === 'requirements' && (
                <div className="specs-table-card">
                  <h3>Runtime &amp; System Specifications</h3>
                  <div className="table-responsive">
                    <table className="specs-table">
                      <thead>
                        <tr>
                          <th>REQUIREMENT</th>
                          <th>SUPPORTED VERSION</th>
                          <th>PURPOSE &amp; NOTES</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><strong>Python</strong></td>
                          <td><code>3.12+</code></td>
                          <td>Typed runtime, modern async FSM orchestrator, AST scanning</td>
                        </tr>
                        <tr>
                          <td><strong>Git</strong></td>
                          <td><code>2.0+</code></td>
                          <td>Diff inspection, transactional session checkpointing, clean rollbacks</td>
                        </tr>
                        <tr>
                          <td><strong>Operating System</strong></td>
                          <td><code>macOS / Linux</code></td>
                          <td>POSIX process boundaries, Unix domain socket IPC, signal trapping</td>
                        </tr>
                        <tr>
                          <td><strong>Docker (Optional)</strong></td>
                          <td><code>Any Engine</code></td>
                          <td>Container isolation backend with <code>--network none</code> and volume mounts</td>
                        </tr>
                        <tr>
                          <td><strong>Gemini API</strong></td>
                          <td><code>gemini-3.8-flash</code></td>
                          <td>Default LLM backend via <code>google-genai</code> SDK with 6-attempt backoff</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* CLI REFERENCE SECTION */}
          <section className="cli-stage" id="cli-reference">
            <div className="cli-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">08 / COMMAND SUITE</span>
                  <span className="badge">CLI REFERENCE</span>
                </div>
                <h2 className="section-title">Deterministic command-line tools for developers</h2>
                <p className="section-desc">
                  Every Aegis command enforces verification invariants. Select a command to explore flags, usage examples, and simulated output.
                </p>
              </div>

              <div className="cli-explorer-layout">
                <div className="cli-nav-list" role="tablist">
                  {CLI_COMMANDS.map((item, idx) => (
                    <button
                      key={item.cmd}
                      className={`cli-nav-item${selectedCliCommand === idx ? ' active' : ''}`}
                      onClick={() => setSelectedCliCommand(idx)}
                      type="button"
                    >
                      <span>{item.cmd}</span>
                      <span className="cli-nav-tag mono">{item.tag}</span>
                    </button>
                  ))}
                </div>

                <div className="cli-detail-panel">
                  <div className="cli-command-title">
                    <code>{activeCli.cmd}</code>
                    <span className="badge">{activeCli.tag}</span>
                  </div>

                  <p className="cli-command-desc">{activeCli.desc}</p>

                  <div className="cli-invariant-banner mono">
                    {activeCli.invariant}
                  </div>

                  <div className="code-deck">
                    <div className="code-deck-header">
                      <div className="code-deck-meta">
                        <div className="code-deck-dots"><span></span><span></span><span></span></div>
                        <span className="code-deck-label mono">usage</span>
                      </div>
                      <button
                        type="button"
                        className={`code-deck-copy-btn${copiedSnippetId === activeCli.cmd ? ' copied' : ''}`}
                        onClick={() => handleCopySnippet(activeCli.usage, activeCli.cmd)}
                      >
                        {copiedSnippetId === activeCli.cmd ? '✓ Copied' : 'Copy'}
                      </button>
                    </div>
                    <pre className="code-deck-body">
                      <code>{activeCli.usage}</code>
                    </pre>
                  </div>

                  {activeCli.flags && activeCli.flags.length > 0 && (
                    <div className="specs-table-card" style={{ marginTop: 0 }}>
                      <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Flags &amp; Options</h4>
                      <table className="specs-table">
                        <thead>
                          <tr>
                            <th>FLAG</th>
                            <th>DESCRIPTION</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeCli.flags.map((f, i) => (
                            <tr key={i}>
                              <td><code>{f.name}</code></td>
                              <td>{f.desc}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <div className="code-deck">
                    <div className="code-deck-header">
                      <div className="code-deck-meta">
                        <div className="code-deck-dots"><span></span><span></span><span></span></div>
                        <span className="code-deck-label mono">simulated console output</span>
                      </div>
                    </div>
                    <pre className="code-deck-body" style={{ color: '#a3e635' }}>
                      <code>{activeCli.output}</code>
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* CONFIGURATION & SKILLS SECTION */}
          <section className="config-stage" id="config-skills">
            <div className="config-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">09 / EXTENSIBILITY</span>
                  <span className="badge">CONFIG &amp; DYNAMIC SKILLS</span>
                </div>
                <h2 className="section-title">Zero-configuration defaults with granular project control</h2>
                <p className="section-desc">
                  Configured via .aegis.yaml in repository root. Context-aware dynamic skills auto-activate, and episodic memory stores project-specific lessons.
                </p>
              </div>

              <div className="section-tabs-bar" role="tablist">
                <button
                  className={`tab-pill-btn${configTab === 'yaml' ? ' active' : ''}`}
                  onClick={() => setConfigTab('yaml')}
                  type="button"
                >
                  <span>.aegis.yaml Schema</span>
                </button>
                <button
                  className={`tab-pill-btn${configTab === 'skills' ? ' active' : ''}`}
                  onClick={() => setConfigTab('skills')}
                  type="button"
                >
                  <span>Dynamic Skills (.aegis/skills/)</span>
                </button>
                <button
                  className={`tab-pill-btn${configTab === 'memory' ? ' active' : ''}`}
                  onClick={() => setConfigTab('memory')}
                  type="button"
                >
                  <span>Episodic Memory (.aegis/memory.json)</span>
                </button>
              </div>

              {configTab === 'yaml' && (
                <div className="config-deck-grid">
                  <div className="code-deck">
                    <div className="code-deck-header">
                      <div className="code-deck-meta">
                        <div className="code-deck-dots"><span></span><span></span><span></span></div>
                        <span className="code-deck-label mono">.aegis.yaml</span>
                      </div>
                      <button
                        type="button"
                        className={`code-deck-copy-btn${copiedSnippetId === 'yaml' ? ' copied' : ''}`}
                        onClick={() => handleCopySnippet(`version: 1\n\nproject:\n  name: "my-service"\n  stack: "python" # python | node | typescript | go | rust | generic\n\nmodel:\n  provider: "gemini"\n  model: null # null -> GEMINI_MODEL env var -> gemini-3.8-flash\n  temperature: 0.2\n\nagent:\n  max_turns: 24\n  max_repairs: 5\n  max_tool_calls: 100\n  max_command_runtime_seconds: 60\n  max_output_size_bytes: 100_000\n  max_files_touched: 20\n\nverification:\n  pre_flight: "python3 -m py_compile src/**/*.py"\n  lint: "ruff check ."\n  test_cmd: "pytest tests/ -q"\n  build_cmd: null\n  timeout_seconds: 60\n  required_gates:\n    - test_cmd\n\nguardrails:\n  deny_paths:\n    - ".git/**"\n    - ".env*"\n    - "secrets/**"\n    - "*.pem"\n    - "*.key"\n  fail_closed: true\n  blocked_commands:\n    - "rm -rf /"\n    - "sudo"\n    - "mkfs"\n\nexecution:\n  backend: "auto" # auto | local | docker\n  network: "none"\n\nmemory:\n  enabled: true\n  path: ".aegis/memory.json"\n  top_k: 5`, 'yaml')}
                      >
                        {copiedSnippetId === 'yaml' ? '✓ Copied' : 'Copy'}
                      </button>
                    </div>
                    <pre className="code-deck-body">
                      <code>{`version: 1

project:
  name: "my-service"
  stack: "python"          # python | node | typescript | go | rust

model:
  provider: "gemini"
  model: null              # defaults to gemini-3.8-flash
  temperature: 0.2

agent:
  max_turns: 24            # Hard cap on LLM turns
  max_repairs: 5           # Max repair loops before rollback
  max_tool_calls: 100
  max_command_runtime_seconds: 60
  max_files_touched: 20

verification:
  pre_flight: "python3 -m py_compile src/**/*.py"
  lint: "ruff check ."
  test_cmd: "pytest tests/ -q"     # Required gate by default
  build_cmd: null
  timeout_seconds: 60
  required_gates:
    - test_cmd

guardrails:
  deny_paths:
    - ".git/**"
    - ".env*"
    - "secrets/**"
    - "*.pem"
    - "*.key"
  fail_closed: true        # Any guard failure = blocked
  blocked_commands:
    - "rm -rf /"
    - "sudo"
    - "mkfs"

execution:
  backend: "auto"          # auto | local | docker
  network: "none"          # container network isolation`}</code>
                    </pre>
                  </div>

                  <div className="config-callouts-list">
                    <div className="config-callout-card">
                      <h4>Deterministic Guardrails</h4>
                      <p><code>fail_closed: true</code> guarantees that any ambiguity or unexpected tool behavior triggers an immediate hard block rather than permissive pass-through.</p>
                    </div>
                    <div className="config-callout-card">
                      <h4>Bounded Repair Loop</h4>
                      <p><code>max_repairs: 5</code> prevents infinite agent retry loops. If code cannot pass gates within 5 repair cycles, surgical rollback reverts to baseline.</p>
                    </div>
                    <div className="config-callout-card">
                      <h4>Key Sanitization Guarantee</h4>
                      <p>API keys are never written to disk. They are stripped from subprocess environments, stdout, stderr, logs, and telemetry traces before output.</p>
                    </div>
                  </div>
                </div>
              )}

              {configTab === 'skills' && (
                <div className="config-deck-grid">
                  <div className="code-deck">
                    <div className="code-deck-header">
                      <div className="code-deck-meta">
                        <div className="code-deck-dots"><span></span><span></span><span></span></div>
                        <span className="code-deck-label mono">.aegis/skills/pytest_conventions.yaml</span>
                      </div>
                      <button
                        type="button"
                        className={`code-deck-copy-btn${copiedSnippetId === 'skill' ? ' copied' : ''}`}
                        onClick={() => handleCopySnippet(`name: "pytest_testing"\ndescription: "Project pytest conventions"\ntriggers:\n  files: ["test_*.py", "conftest.py"]\n  keywords: ["test", "pytest", "fixture"]\n  stacks: ["python"]\ninstructions: |\n  Follow the arrange-act-assert pattern.\n  Use pytest fixtures, not unittest setUp/tearDown.\n  Do not mock verification gates.\n  All new test modules must import from src/, not aegis/ directly.`, 'skill')}
                      >
                        {copiedSnippetId === 'skill' ? '✓ Copied' : 'Copy'}
                      </button>
                    </div>
                    <pre className="code-deck-body">
                      <code>{`name: "pytest_testing"
description: "Project pytest conventions"
triggers:
  files: ["test_*.py", "conftest.py"]
  keywords: ["test", "pytest", "fixture"]
  stacks: ["python"]
instructions: |
  Follow the arrange-act-assert pattern.
  Use pytest fixtures, not unittest setUp/tearDown.
  Do not mock verification gates.
  All new test modules must import from src/, not aegis/ directly.`}</code>
                    </pre>
                  </div>

                  <div className="config-callouts-list">
                    <div className="config-callout-card">
                      <h4>Progressive Activation</h4>
                      <p>Skills are loaded selectively based on repository context and active file targets. The model only receives instructions relevant to the active task.</p>
                    </div>
                    <div className="config-callout-card">
                      <h4>Stack-Aware Triggering</h4>
                      <p>Triggers can match file globs, semantic prompt keywords, or detected project stacks (e.g. Python, TypeScript, Go).</p>
                    </div>
                  </div>
                </div>
              )}

              {configTab === 'memory' && (
                <div className="config-deck-grid">
                  <div className="code-deck">
                    <div className="code-deck-header">
                      <div className="code-deck-meta">
                        <div className="code-deck-dots"><span></span><span></span><span></span></div>
                        <span className="code-deck-label mono">.aegis/memory.json</span>
                      </div>
                    </div>
                    <pre className="code-deck-body">
                      <code>{`[
  {
    "lesson": "DB connection pool exhausts under load; set pool_size=10 in tests",
    "tags": ["database", "testing", "performance"],
    "created_at": "2026-09-28T04:12:00Z",
    "hit_count": 8
  },
  {
    "lesson": "Always run pytest with -q flag in CI to minimize log buffer size",
    "tags": ["pytest", "ci"],
    "created_at": "2026-09-28T05:30:00Z",
    "hit_count": 4
  }
]`}</code>
                    </pre>
                  </div>

                  <div className="config-callouts-list">
                    <div className="config-callout-card">
                      <h4>Untrusted Memory Invariant</h4>
                      <p>Episodic memory informs the agent, but memory can never override security guards, path rules, or verification gates. Stored lessons are sanitized against prompt injection.</p>
                    </div>
                    <div className="config-callout-card">
                      <h4>Deduplication Engine</h4>
                      <p>Built-in 20× deduplication prevents lesson bloat and preserves strict prompt token budgets.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* VERIFICATION MATRIX SECTION */}
          <section className="matrix-stage" id="matrix">
            <div className="matrix-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">10 / EMPIRICAL PROOF</span>
                  <span className="badge">112 TESTS PASSING</span>
                </div>
                <h2 className="section-title">Empirical verification matrix: real systems, zero simulations</h2>
                <p className="section-desc">
                  Every component in this table is verified by running real code against real systems — including multi-turn Gemini APIs, Docker container exec, and adversarial security tests.
                </p>
              </div>

              <div className="matrix-filter-bar">
                <button
                  type="button"
                  className={`matrix-filter-btn${matrixFilter === 'all' ? ' active' : ''}`}
                  onClick={() => setMatrixFilter('all')}
                >
                  All Components (18)
                </button>
                <button
                  type="button"
                  className={`matrix-filter-btn${matrixFilter === 'live' ? ' active' : ''}`}
                  onClick={() => setMatrixFilter('live')}
                >
                  Live E2E &amp; Docker (5)
                </button>
                <button
                  type="button"
                  className={`matrix-filter-btn${matrixFilter === 'security' ? ' active' : ''}`}
                  onClick={() => setMatrixFilter('security')}
                >
                  GateGuard Security (4)
                </button>
                <button
                  type="button"
                  className={`matrix-filter-btn${matrixFilter === 'core' ? ' active' : ''}`}
                  onClick={() => setMatrixFilter('core')}
                >
                  Core State Machine (9)
                </button>
              </div>

              <div className="matrix-table-wrap">
                <table className="matrix-table">
                  <thead>
                    <tr>
                      <th>COMPONENT</th>
                      <th>VERIFICATION STATUS</th>
                      <th>EMPIRICAL EVIDENCE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMatrix.map((item, idx) => (
                      <tr key={idx}>
                        <td><strong>{item.component}</strong></td>
                        <td>
                          {item.status === 'LIVE VERIFIED' ? (
                            <span className="matrix-badge-live mono">✔ LIVE VERIFIED</span>
                          ) : (
                            <span className="matrix-badge-verified mono">✔ {item.status}</span>
                          )}
                        </td>
                        <td className="mono" style={{ fontSize: '12px', color: '#484641' }}>{item.evidence}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="specs-table-card" style={{ marginTop: '28px' }}>
                <h3>Run the Test Suite Locally</h3>
                <div className="code-deck">
                  <div className="code-deck-header">
                    <div className="code-deck-meta">
                      <div className="code-deck-dots"><span></span><span></span><span></span></div>
                      <span className="code-deck-label mono">pytest commands</span>
                    </div>
                    <button
                      type="button"
                      className={`code-deck-copy-btn${copiedSnippetId === 'tests' ? ' copied' : ''}`}
                      onClick={() => handleCopySnippet('source .venv/bin/activate\n\n# All unit, security, and scenario tests (~3s)\npytest tests/ --ignore=tests/integration -v\n\n# Live Gemini E2E test (~3 min)\nGEMINI_API_KEY="..." GEMINI_MODEL="gemini-3.5-flash" pytest tests/integration/test_gemini_live_e2e.py -v -s\n\n# Security adversarial test suite\npytest tests/security/ -v\n\n# Live Docker isolation tests\npytest tests/integration/test_docker_live.py -v -s', 'tests')}
                    >
                      {copiedSnippetId === 'tests' ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="code-deck-body">
                    <code>{`# All unit, security, and scenario tests (~3s)
pytest tests/ --ignore=tests/integration -v

# Live Gemini E2E test (~3 min)
GEMINI_API_KEY="..." GEMINI_MODEL="gemini-3.5-flash" pytest tests/integration/test_gemini_live_e2e.py -v -s

# Security adversarial test suite
pytest tests/security/ -v

# Live Docker isolation tests
pytest tests/integration/test_docker_live.py -v -s`}</code>
                  </pre>
                </div>
              </div>
            </div>
          </section>

          {/* KNOWN LIMITATIONS SECTION */}
          <section className="limitations-stage" id="limitations">
            <div className="limitations-container">
              <div className="section-head">
                <div className="meta-tag">
                  <span className="mono">11 / TRANSPARENCY</span>
                  <span className="badge">KNOWN LIMITATIONS &amp; MITIGATIONS</span>
                </div>
                <h2 className="section-title">Transparent engineering boundaries</h2>
                <p className="section-desc">
                  Deterministic guarantees require clarity on boundaries. Here is how Aegis mitigates runtime constraints.
                </p>
              </div>

              <div className="limitations-grid">
                <div className="limitation-card">
                  <h4>LocalExecutor Sandboxing</h4>
                  <div className="limitation-impact">
                    <strong>Impact:</strong> Process groups lack kernel-level isolation against hostile binaries.
                  </div>
                  <div className="limitation-mitigation">
                    <strong>Mitigation:</strong> Set <code>execution.backend: docker</code> for untrusted tasks. Automatically falls back cleanly.
                  </div>
                </div>

                <div className="limitation-card">
                  <h4>Filesystem TOCTOU</h4>
                  <div className="limitation-impact">
                    <strong>Impact:</strong> Concurrent host processes could swap symlinks between check and write.
                  </div>
                  <div className="limitation-mitigation">
                    <strong>Mitigation:</strong> Use containerized runners with dedicated volume mounts in hostile environments.
                  </div>
                </div>

                <div className="limitation-card">
                  <h4>Free-Tier Gemini Quotas</h4>
                  <div className="limitation-impact">
                    <strong>Impact:</strong> Free quotas (20 req/day) can trigger 429 RESOURCE_EXHAUSTED errors.
                  </div>
                  <div className="limitation-mitigation">
                    <strong>Mitigation:</strong> Built-in 6-attempt exponential backoff with jitter; model switching via GEMINI_MODEL.
                  </div>
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
