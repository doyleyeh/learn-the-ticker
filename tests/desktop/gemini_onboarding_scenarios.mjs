import assert from 'node:assert/strict';
import { completeFreeSetup, defaultFreeTier } from '../../scripts/gemini_onboarding_guard.mjs';
const offered = { allowedTiers: [{ id: 'free-tier', isDefault: true, userDefinedCloudaicompanionProject: false }] };
const complete = { done: true, response: { cloudaicompanionProject: { id: 'synthetic-project' } } };
class CodeAssistServer {
  constructor(client) { this.client = client; }
  async post(method, body) { return (await this.client.request({ url: 'https://cloudcode-pa.googleapis.com/v1internal:' + method, method: 'POST', body: JSON.stringify(body) })).data; }
  async loadCodeAssist(body) { return this.post('loadCodeAssist', body); }
  async onboardUser(body) { return this.post('onboardUser', body); }
  async getOperation(name) { return (await this.client.request({ url: 'https://cloudcode-pa.googleapis.com/v1internal/' + name, method: 'GET' })).data; }
}
assert.equal(defaultFreeTier(offered), true);
for (const value of [{}, { allowedTiers: [{ id: 'standard-tier', isDefault: true }] }, { allowedTiers: [{ id: 'free-tier' }] }, { allowedTiers: [...offered.allowedTiers, ...offered.allowedTiers] }, { allowedTiers: [{ id: 'free-tier', isDefault: true, userDefinedCloudaicompanionProject: true }] }]) {
  assert.throws(() => defaultFreeTier(value), (error) => error.code === 'free_tier_not_offered');
}
assert.throws(() => defaultFreeTier({ ...offered, validationUrl: 'https://private' }), (error) => error.code === 'account_validation_required');
const existing = { currentTier: { id: 'standard-tier' }, cloudaicompanionProject: 'synthetic-project' };
assert.equal(defaultFreeTier(existing), false);
async function exercise(responses) {
  const calls = []; const waits = [];
  const result = await completeFreeSetup({ CodeAssistServer }, { request: async (request) => {
    calls.push(request); assert.equal(request.retry, false); assert.equal(request.maxRedirects, 0); assert.equal(request.redirect, 'error');
    return { data: responses.shift() };
  } }, async (ms) => { waits.push(ms); });
  return { result, calls, waits };
}
const success = await exercise([offered, complete]);
assert.equal(success.result.status, 'onboarding_complete');
assert.equal(success.calls.length, 2);
assert.deepEqual(JSON.parse(success.calls[1].body), { tierId: 'free-tier', metadata: { ideType: 'IDE_UNSPECIFIED', platform: 'PLATFORM_UNSPECIFIED', pluginType: 'GEMINI' } });
assert.equal(JSON.stringify(success.result).includes('synthetic-project'), false);
const unchanged = await exercise([existing]);
assert.equal(unchanged.result.status, 'already_onboarded'); assert.equal(unchanged.calls.length, 1);
const pending = { done: false, name: 'operations/synthetic' };
const polled = await exercise([offered, pending, complete]);
assert.equal(polled.result.status, 'onboarding_complete'); assert.equal(polled.calls[2].method, 'GET'); assert.deepEqual(polled.waits, [5000]);
const bounded = await exercise([offered, ...Array(7).fill(pending)]);
assert.equal(bounded.result.status, 'onboarding_pending'); assert.equal(bounded.calls.length, 8);
for (const operation of [{ error: { message: 'private' } }, { name: 'https://other/operations' }, { name: 'operations/../escape' }, { done: true, response: {} }]) {
  await assert.rejects(exercise([offered, operation]));
}
let requests = 0;
await assert.rejects(completeFreeSetup({ CodeAssistServer }, { request: async () => { requests++; throw { response: { status: 429 } }; } }), (error) => error.code === 'quota_exhausted');
assert.equal(requests, 1);
process.stdout.write('onboarding_scenarios_passed\n');
