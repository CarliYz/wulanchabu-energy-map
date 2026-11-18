import base from './e2e.config.js';
import { decisionExecutor } from '@e2e-dev/decision';
import { typeSafeAi } from '@ai-sdk/typesafe-ai';

if (!process.env.TYPESAFE_AI_API_KEY) {
  throw new Error('JEV_CREDENTIAL_MISSING: set TYPESAFE_AI_API_KEY in the invoking process. No model call was made.');
}

export default {
  ...base,
  tests: 'tests/vision/*.jev.js',
  output: '.e2e-jev',
  agents: {
    default: {
      executor: decisionExecutor({
        model: typeSafeAi.decisionModel(process.env.JEV_MODEL_ID || 'jev-latest'),
        vision: true,
      }),
      maxModelCalls: 12,
    },
  },
};
