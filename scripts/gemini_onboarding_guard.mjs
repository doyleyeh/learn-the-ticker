import { accountProject, PreflightFailure, providerHeaders } from './gemini_preflight_guard.mjs';

const ROOT = 'https://cloudcode-pa.googleapis.com/v1internal';
const METADATA = { ideType: 'IDE_UNSPECIFIED', platform: 'PLATFORM_UNSPECIFIED', pluginType: 'GEMINI' };
const fail = (code) => { throw new PreflightFailure(code); };

export function defaultFreeTier(account) {
  if (!account || typeof account !== 'object' || Array.isArray(account) || account.error) fail('invalid_account');
  if (account.currentTier) { accountProject(account); return false; }
  const defaults = Array.isArray(account.allowedTiers) ? account.allowedTiers.filter((tier) => tier?.isDefault === true) : [];
  if (defaults.length !== 1 || defaults[0].id !== 'free-tier' || defaults[0].userDefinedCloudaicompanionProject === true) fail('free_tier_not_offered');
  if (account.validationUrl || account.validationLink || (Array.isArray(account.ineligibleTiers) && account.ineligibleTiers.some(
    (tier) => tier?.reasonCode === 'VALIDATION_REQUIRED' || tier?.tierId === 'free-tier'))) fail('account_validation_required');
  return true;
}

export async function completeFreeSetup(core, client, sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))) {
  let stage = 0; let operation = null; let polls = 0;
  const transport = { request: async (request) => {
    let method; let body;
    if (stage < 2) {
      method = stage === 0 ? 'loadCodeAssist' : 'onboardUser';
      body = stage === 0 ? { metadata: METADATA } : { tierId: 'free-tier', metadata: METADATA };
      if (request.method !== 'POST' || request.url !== `${ROOT}:${method}` || request.body !== JSON.stringify(body)) fail('transport_scope');
      stage++;
    } else if (operation && polls < 6 && request.method === 'GET' && request.url === `${ROOT}/${operation}`) {
      polls++;
    } else fail('transport_scope');
    try {
      return await client.request({ url: request.url, method: request.method,
        ...(body ? { body: JSON.stringify(body) } : {}), headers: providerHeaders(),
        responseType: 'json', retry: false, retryConfig: { retry: 0, noResponseRetries: 0 },
        maxRedirects: 0, redirect: 'error', timeout: 15_000, maxContentLength: 65_536 });
    } catch (error) {
      fail(error?.response?.status === 429 ? 'quota_exhausted' : 'onboarding_failed');
    }
  } };
  const server = new core.CodeAssistServer(transport);
  const account = await server.loadCodeAssist({ metadata: METADATA });
  const base = { generation_qualified: false, inference_requested: false, credits_enabled: false };
  if (!defaultFreeTier(account)) return { ...base, status: 'already_onboarded' };
  let result = await server.onboardUser({ tierId: 'free-tier', metadata: METADATA });
  for (;;) {
    if (!result || typeof result !== 'object' || Array.isArray(result) || result.error) fail('onboarding_failed');
    if (result.done === true) {
      // Confirm only completion of free setup; a separate metadata check verifies tier/quota.
      const project = result.response?.cloudaicompanionProject?.id;
      if (typeof project !== 'string' || !/^[a-z][a-z0-9-]{4,62}$/.test(project)) fail('project_unverified');
      return { ...base, status: 'onboarding_complete' };
    }
    if (result.done !== undefined && result.done !== false) fail('onboarding_failed');
    if (typeof result.name !== 'string' || !/^operations\/[a-zA-Z0-9_-]{1,160}$/.test(result.name)
        || (operation && operation !== result.name)) fail('onboarding_failed');
    operation = result.name;
    if (polls >= 6) return { ...base, status: 'onboarding_pending' };
    await sleep(5000);
    result = await server.getOperation(operation);
  }
}
