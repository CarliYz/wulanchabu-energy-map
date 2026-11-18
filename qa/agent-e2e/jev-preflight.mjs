import { writeFile, mkdir } from 'node:fs/promises';
import { decisionExecutor } from '@e2e-dev/decision';
import { typeSafeAi } from '@ai-sdk/typesafe-ai';

const credentialPresent = Boolean(process.env.TYPESAFE_AI_API_KEY);
const executor = decisionExecutor({ model: typeSafeAi.decisionModel('jev-latest'), vision: true });
const receipt = {
  capturedAt: new Date().toISOString(),
  adapterConstruction: executor ? 'pass' : 'fail',
  credentialPresent,
  credentialScope: 'current process environment only; no secret files searched',
  modelId: 'jev-latest',
  actualModelVersion: null,
  liveModelCall: 'not_run',
  liveVisualVerdict: credentialPresent ? 'not_run' : 'blocked',
  reason: credentialPresent ? 'This preflight never calls a provider.' : 'TYPESAFE_AI_API_KEY absent from invoking environment',
  coordinateActions: 'not_configured; requires an additional text model',
};
await mkdir(new URL('../../outputs/reference-study-20261116/', import.meta.url), { recursive: true });
await writeFile(new URL('../../outputs/reference-study-20261116/jev-preflight.json', import.meta.url), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt, null, 2));
if (!credentialPresent) process.exitCode = 2;
