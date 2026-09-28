# Aegis — Verification Engine

Aegis is a React/Vite implementation of the existing verification-engine website. The visual language, section order, copy, palette, canvas effects, and interaction concept are preserved; the React shell and runtime contracts are hardened for real use.

## Run locally

```bash
npm install
npm run dev
```

Production build:

```bash
npm run build
npm run preview
```

Dependency-free project smoke check:

```bash
npm run check
```

## Structure

- `src/main.jsx` — React entry point
- `src/App.jsx` — page composition, navigation state, and section markup
- `src/components/` — reusable WebGL/canvas interaction components
- `src/engine.js` — mount-safe imperative runtime for shared canvas, scroll, audio, evaluator, rollback, and cinematic interactions
- `src/styles.css` — visual system, responsive rules, accessibility states, and React shell refinements
- `scripts/check-aegis.mjs` — dependency-free DOM/runtime contract check
- `vite.config.js` — Vite configuration

## Runtime notes

The page uses client-side canvas/WebGL effects and optional Web Audio. The runtime cleans up event listeners, timers, observers/animation loops, audio, and WebGL resources when the React app unmounts, preventing duplicate effects under development StrictMode.

The experience also respects reduced-motion preferences for the cursor/ambient effects and keeps keyboard navigation available when the custom pointer is enabled.
