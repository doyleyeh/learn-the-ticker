import assert from 'node:assert/strict';
import { accountProject, quotaSnapshot, metadataTransport, existingAccount, accountPreflight, isolatedConfig, onboardingSummary } from '../../scripts/gemini_preflight_guard.mjs';

const now = Date.parse('2026-10-06T00:00:00Z');
const account = { currentTier: { id: 'standard-tier' }, cloudaicompanionProject: 'synthetic-project', paidTier: { name: 'private account field' } };
const bucket = { modelId: 'gemini-2.5-flash', remainingFraction: 0.75, remainingAmount: '75', resetTime: '2026-10-07T00:00:00Z', tokenType: 'REQUESTS' };
const quota = { buckets: [bucket] };
const request = (method, body) => ({ url: 'https://cloudcode-pa.googleapis.com/v1internal:' + method, method: 'POST', body: JSON.stringify(body), responseType: 'json' });
const load = request('loadCodeAssist', { metadata: { ideType: 'IDE_UNSPECIFIED', platform: 'PLATFORM_UNSPECIFIED', pluginType: 'GEMINI' } });
const query = request('retrieveUserQuota', { project: 'synthetic-project' });
const expect = (fn, code) => assert.throws(fn, (error) => error.code === code);
assert.deepEqual(onboardingSummary({ allowedTiers: [{ id: 'standard-tier', isDefault: true, userDefinedCloudaicompanionProject: true, name: 'private' }] }),
  { default_tier: 'standard-tier', free_tier_offered: false, user_project_required: true, paid_tier_present: false });
assert.equal(onboardingSummary({ allowedTiers: [{ id: 'private', isDefault: true }] }).default_tier, 'unknown');
assert.equal(onboardingSummary({ allowedTiers: [] }).default_tier, 'none');

assert.equal(accountProject(account), 'synthetic-project');
for (const value of [null, [], { error: { message: 'private' } }, { ineligibleTiers: {} }]) expect(() => accountProject(value), 'invalid_account');
expect(() => accountProject({}), 'onboarding_required');
expect(() => accountProject({ ...account, currentTier: { id: 'unknown-tier' } }), 'unsupported_tier');
expect(() => accountProject({ ...account, validationUrl: 'https://private' }), 'account_validation_required');
expect(() => accountProject({ ...account, cloudaicompanionProject: 'https://other' }), 'project_unverified');
expect(() => accountProject({ ineligibleTiers: [{ reasonCode: 'VALIDATION_REQUIRED' }] }), 'account_validation_required');

const normalized = quotaSnapshot(quota, now);
assert.equal(normalized.status, 'metadata_verified');
assert.equal(normalized.generation_qualified, false);
assert.equal(quotaSnapshot({ buckets: [{ ...bucket, remainingFraction: 0, remainingAmount: '0' }] }, now).status, 'quota_exhausted');
for (const patch of [{ modelId: 'auto' }, { modelId: 'private diagnostic /' }, { remainingFraction: true }, { remainingFraction: -1 }, { remainingFraction: 2 }, { remainingFraction: NaN }, { remainingAmount: '0' }, { remainingAmount: '1.5' }, { remainingAmount: 1 }, { resetTime: 'private' }, { tokenType: 'UNKNOWN' }]) {
  expect(() => quotaSnapshot({ buckets: [{ ...bucket, ...patch }] }, now), 'invalid_quota');
}
for (const value of [{}, { buckets: [] }, { error: 'private', buckets: [bucket] }, { buckets: Array(129).fill(bucket) }]) expect(() => quotaSnapshot(value, now), 'invalid_quota');
expect(() => quotaSnapshot({ buckets: [bucket, bucket] }, now), 'ambiguous_quota');
expect(() => quotaSnapshot(quota, now + 86400_000), 'stale_quota');

const calls = [];
const client = { request: async (value) => { calls.push(value); return { data: calls.length === 1 ? account : quota }; } };
class CodeAssistServer {
  constructor(transport) { this.transport = transport; }
  async loadCodeAssist(body) { return (await this.transport.request(request('loadCodeAssist', body))).data; }
  async retrieveUserQuota(body) { return (await this.transport.request(request('retrieveUserQuota', body))).data; }
}
const report = await accountPreflight({ CodeAssistServer }, client, now);
assert.equal(report.status, 'metadata_verified');
assert.equal(calls.length, 2);
assert.ok(!JSON.stringify(report).includes('synthetic-project'));
assert.ok(!JSON.stringify(report).includes('private account field'));
let onboardingReads = 0;
const needsSetup = await accountPreflight({ CodeAssistServer }, { request: async () => { onboardingReads++; return { data: { allowedTiers: [] } }; } }, now);
assert.equal(needsSetup.status, 'onboarding_required'); assert.equal(onboardingReads, 1);
for (const call of calls) {
  assert.equal(call.headers['User-Agent'], `GeminiCLI/0.62.0/gemini-2.5-flash (${process.platform}; ${process.arch}; terminal)`);
  assert.deepEqual(Object.keys(call.headers).sort(), ['Content-Type', 'User-Agent']);
  assert.equal(call.retry, false); assert.equal(call.maxRedirects, 0); assert.equal(call.redirect, 'error');
  assert.equal(call.retryConfig.retry, 0); assert.equal(call.maxContentLength, 65536); assert.equal(call.timeout, 15000);
  assert.equal(call.body.includes('enabledCreditTypes'), false);
}

for (const bad of [{ ...load, url: 'https://other/loadCodeAssist' }, { ...load, method: 'GET' }, request('generateContent', {}), request('onboardUser', {}), request('loadCodeAssist', { ...JSON.parse(load.body), enabledCreditTypes: ['g1-credits'] }), query]) {
  let invoked = false;
  await assert.rejects(metadataTransport({ request: async () => { invoked = true; } }).request(bad), (error) => error.code === 'transport_scope');
  assert.equal(invoked, false);
}
const bounded = metadataTransport({ request: async () => ({ data: {} }) });
await bounded.request(load); await bounded.request(query);
await assert.rejects(bounded.request(query), (error) => error.code === 'transport_scope');
for (const status of [401, 403, 429, 500, 302]) {
  let count = 0;
  const transport = metadataTransport({ request: async () => { count++; throw { response: { status, data: 'private' } }; } });
  await assert.rejects(transport.request(load), (error) => error.code === (status === 429 ? 'quota_exhausted' : status === 401 || status === 403 ? 'account_access_denied' : 'metadata_transport_failed'));
  assert.equal(count, 1);
}
for (const [reason, code] of [['SERVICE_DISABLED', 'account_service_unavailable'], ['ACCESS_TOKEN_SCOPE_INSUFFICIENT', 'account_scope_denied'], ['USER_PROJECT_DENIED', 'project_access_denied'], ['PRIVATE_DIAGNOSTIC', 'account_access_denied']]) {
  const transport = metadataTransport({ request: async () => { throw { response: { status: 403, data: { error: { details: [{ '@type': 'type.googleapis.com/google.rpc.ErrorInfo', domain: 'googleapis.com', reason, metadata: { consumer: 'private-account' } }] } } } }; } });
  await assert.rejects(transport.request(load), (error) => error.code === code && !error.message.includes('private-account'));
}

let authCalls = 0;
class KeychainService {
  constructor(service) { this.serviceName = service; }
  async getNativeKeychain() { return {}; }
  async getKeychainOrThrow() { return this.initializeKeychain(); }
  async getPassword() { return null; }
}
const core = { KeychainService, AuthType: { LOGIN_WITH_GOOGLE: 'google' }, getOauthClient: async () => { authCalls++; } };
await assert.rejects(existingAccount(core), (error) => error.code === 'sign_in_required');
assert.equal(authCalls, 0);
KeychainService.prototype.getPassword = async () => JSON.stringify({ token: { accessToken: 'synthetic' } });
core.getOauthClient = async (_type, config) => {
  assert.equal(config.isBrowserLaunchSuppressed(), true); assert.equal(config.isInteractive(), false);
  return { credentials: { access_token: 'synthetic' } };
};
assert.equal((await existingAccount(core)).credentials.access_token, 'synthetic');
core.getOauthClient = async () => { throw new Error('private auth diagnostics'); };
await assert.rejects(existingAccount(core), (error) => error.code === 'sign_in_required');

for (const browsing of [false, true]) {
  const config = isolatedConfig('/synthetic', browsing);
  assert.deepEqual(config.coreTools, browsing ? ['google_web_search', 'web_fetch'] : []);
  for (const flag of ['mcpEnabled', 'extensionsEnabled', 'enableAgents', 'enableHooks', 'skillsSupport', 'usageStatisticsEnabled', 'retryFetchErrors']) assert.equal(config[flag], false);
  assert.equal(config.billing.overageStrategy, 'never');
  assert.equal(config.policyEngineConfig.defaultDecision, 'deny');
  assert.equal(config.policyEngineConfig.nonInteractive, true);
}
process.stdout.write('preflight_scenarios_passed\n');
