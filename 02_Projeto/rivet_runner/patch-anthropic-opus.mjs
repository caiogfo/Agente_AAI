// Make the bundled Rivet Anthropic node compatible with Opus 4.8.
//
// Why: @ironclad/rivet-core (up to 1.25.0, the latest) always sends either
// `temperature` or `top_p` to the Anthropic API. Newer models such as
// claude-opus-4-8 DEPRECATE both sampling params and reject the request with a
// 400. This patch makes the node omit both when the model is an opus-4-8, so the
// graph can run on the most powerful Opus. It is idempotent and runs on
// `postinstall`, so it survives `npm install`.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const target = path.resolve(
  here,
  'node_modules/@ironclad/rivet-core/dist/esm/plugins/anthropic/nodes/ChatAnthropicNode.js',
);

if (!fs.existsSync(target)) {
  // Dependencies not installed yet (or layout changed); nothing to do.
  process.exit(0);
}

let src = fs.readFileSync(target, 'utf8');

const FROM_TEMP = 'temperature: useTopP ? undefined : temperature,';
const TO_TEMP = 'temperature: (useTopP || /opus-4-8/.test(model)) ? undefined : temperature,';
const FROM_TOPP = 'top_p: useTopP ? topP : undefined,';
const TO_TOPP = 'top_p: (useTopP && !/opus-4-8/.test(model)) ? topP : undefined,';

if (src.includes(TO_TEMP) && src.includes(TO_TOPP)) {
  console.log('• rivet Opus patch already applied.');
  process.exit(0);
}

const before = src;
src = src.split(FROM_TEMP).join(TO_TEMP).split(FROM_TOPP).join(TO_TOPP);

if (src === before) {
  console.warn('⚠ rivet Opus patch: target lines not found (rivet-core version changed?). Skipping.');
  process.exit(0);
}

fs.writeFileSync(target, src);
console.log('✓ rivet Opus patch applied (omits deprecated temperature/top_p for claude-opus-4-8).');
