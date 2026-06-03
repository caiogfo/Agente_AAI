// Headless runner for the corrected Rivet graph (Anthropic Claude).
//
// Usage (from the repo root, so relative file reads resolve):
//   python -m engine.run --emit-facts        # produce build/facts.json
//   node --env-file=.env rivet_runner/run_graph.mjs
//
// Requires ANTHROPIC_API_KEY in the environment (.env is loaded by --env-file).
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  loadProjectFromFile,
  runGraph,
  NodeNativeApi,
  anthropicPlugin,
  globalRivetNodeRegistry,
} from '@ironclad/rivet-node';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
process.chdir(repoRoot); // so the readFile node resolves build/facts.json, Input/...

const PROJECT = path.join(repoRoot, 'enter_challenge.rivet-project');
const GRAPH = 'main_challenge_v2';

if (!process.env.ANTHROPIC_API_KEY) {
  console.error('✗ ANTHROPIC_API_KEY not set. Run: node --env-file=.env rivet_runner/run_graph.mjs');
  process.exit(2);
}

// Register the built-in Anthropic plugin so the `chatAnthropic` nodes resolve.
globalRivetNodeRegistry.registerPlugin(anthropicPlugin);

console.log('• Loading project…');
const project = await loadProjectFromFile(PROJECT);

console.log(`• Running graph "${GRAPH}" with Claude…`);
const outputs = await runGraph(project, {
  graph: GRAPH,
  inputs: {},
  nativeApi: new NodeNativeApi(),
  pluginSettings: {
    anthropic: { anthropicApiKey: process.env.ANTHROPIC_API_KEY },
  },
  openAiKey: process.env.OPENAI_API_KEY ?? '',
  onUserEvent: {},
});

const letter = outputs?.letter?.value;
if (letter) {
  console.log('\n===== CARTA FINAL (Rivet · Claude) =====\n');
  console.log(letter);
  console.log('\n=======================================');
} else {
  console.log('\n(no `letter` graph output found; raw outputs below)');
  console.log(JSON.stringify(outputs, null, 2).slice(0, 2000));
}
