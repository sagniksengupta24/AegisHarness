import { readFile } from 'node:fs/promises';
import { access } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const requiredFiles = [
  'index.html',
  'package.json',
  'vite.config.js',
  'src/main.jsx',
  'src/App.jsx',
  'src/engine.js',
  'src/styles.css',
  'src/components/TechText.jsx',
  'src/components/GhostFibers.jsx',
  'src/components/WebThreads.jsx',
  'src/components/ClickSpark.jsx',
  'src/components/FlowingMenu.jsx',
  'src/components/MagicRings.jsx',
  'src/components/OptionWheel.jsx',
  'public/favicon.svg'
];

for (const file of requiredFiles) await access(resolve(root, file));

const app = await readFile(resolve(root, 'src/App.jsx'), 'utf8');
const main = await readFile(resolve(root, 'src/main.jsx'), 'utf8');
const engine = await readFile(resolve(root, 'src/engine.js'), 'utf8');
const pkg = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'));

const appIds = new Set([...app.matchAll(/id="([^"]+)"/g)].map(match => match[1]));
const engineIds = new Set([
  ...engine.matchAll(/byId\('([^']+)'\)/g),
  ...engine.matchAll(/byId\("([^"]+)"\)/g)
].map(match => match[1]));

const missingIds = [...engineIds].filter(id => !appIds.has(id));
if (missingIds.length) throw new Error(`Engine expects missing React IDs: ${missingIds.join(', ')}`);
if (!main.includes('React.StrictMode')) throw new Error('React StrictMode entry point is missing.');
if (!app.includes('aria-controls="aegis-navigation-drawer"')) throw new Error('Menu accessibility contract is missing.');
if (!app.includes('inert={!menuOpen}')) throw new Error('Closed navigation drawer is not inert.');
if (pkg.scripts?.check !== 'node scripts/check-aegis.mjs') throw new Error('Smoke-check script is not wired to package.json.');

console.log(`Aegis smoke check passed: ${requiredFiles.length} required files, ${appIds.size} DOM IDs, ${engineIds.size} engine bindings.`);
