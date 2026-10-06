import { createHash } from 'node:crypto';
import { nativeOnlyStorage } from './gemini_login_guard.mjs';

export class PreflightFailure extends Error {
  constructor(code) { super(code); this.code = code; }
}
const fail = (code) => { throw new PreflightFailure(code); };
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const ENDPOINT = 'https://cloudcode-pa.googleapis.com/v1internal:';
const METADATA = { ideType: 'IDE_UNSPECIFIED', platform: 'PLATFORM_UNSPECIFIED', pluginType: 'GEMINI' };
const TIERS = new Set(['free-tier', 'legacy-tier', 'standard-tier']);
// Match the pinned CLI's client-identification header for its inspection model.
// This is metadata only; no model is invoked or selected for the application.
export const providerHeaders = () => ({ 'Content-Type': 'application/json',
  'User-Agent': `GeminiCLI/0.62.0/gemini-2.5-flash (${process.platform}; ${process.arch}; terminal)` });

export function onboardingSummary(account) {
  if (!object(account) || account.error || !Array.isArray(account.allowedTiers) || account.allowedTiers.length > 16) fail('invalid_account');
  const defaults = account.allowedTiers.filter((tier) => object(tier) && tier.isDefault === true);
  const choice = defaults.length === 1 ? defaults[0] : null;
  return {
    default_tier: choice ? (TIERS.has(choice.id) ? choice.id : 'unknown') : defaults.length ? 'ambiguous' : 'none',
    free_tier_offered: account.allowedTiers.some((tier) => tier?.id === 'free-tier'),
    user_project_required: typeof choice?.userDefinedCloudaicompanionProject === 'boolean' ? choice.userDefinedCloudaicompanionProject : null,
    paid_tier_present: Boolean(account.paidTier),
  };
}

export function accountProject(value) {
  if (!object(value) || value.error || (value.ineligibleTiers !== undefined && !Array.isArray(value.ineligibleTiers))) fail('invalid_account');
  if (value.validationUrl || value.validationLink || value.ineligibleTiers?.some(
    (tier) => tier.reasonCode === 'VALIDATION_REQUIRED')) fail('account_validation_required');
  if (!value.currentTier) fail('onboarding_required');
  if (!TIERS.has(value.currentTier.id)) fail('unsupported_tier');
  const project = value.cloudaicompanionProject;
  if (typeof project !== 'string' || !/^[a-z][a-z0-9-]{4,62}$/.test(project)) fail('project_unverified');
  return project;
}

export function quotaSnapshot(value, now = Date.now()) {
  if (!object(value) || value.error || !Array.isArray(value.buckets) || !value.buckets.length || value.buckets.length > 128) fail('invalid_quota');
  const seen = new Set();
  const rows = value.buckets.map((bucket) => {
    if (!object(bucket) || typeof bucket.modelId !== 'string'
        || !/^gemini-[a-z0-9][a-z0-9.-]{0,78}$/.test(bucket.modelId)) fail('invalid_quota');
    const fraction = bucket.remainingFraction;
    if (typeof fraction !== 'number' || !Number.isFinite(fraction) || fraction < 0 || fraction > 1) fail('invalid_quota');
    if (bucket.remainingAmount !== undefined && (typeof bucket.remainingAmount !== 'string'
        || !/^(0|[1-9][0-9]{0,12})$/.test(bucket.remainingAmount))) fail('invalid_quota');
    if (bucket.remainingAmount === '0' && fraction > 0) fail('invalid_quota');
    if (typeof bucket.resetTime !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/.test(bucket.resetTime)) fail('invalid_quota');
    const reset = Date.parse(bucket.resetTime);
    if (!Number.isFinite(reset) || reset <= now || reset > now + 35 * 86400_000) fail('stale_quota');
    const key = `${bucket.modelId}:${bucket.tokenType ?? ''}`;
    if (seen.has(key)) fail('ambiguous_quota');
    seen.add(key);
    if (bucket.tokenType !== undefined && !['REQUESTS', 'INPUT', 'OUTPUT', 'INPUT_TOKENS', 'OUTPUT_TOKENS'].includes(bucket.tokenType)) fail('invalid_quota');
    return { model: bucket.modelId, remaining_fraction: fraction, reset_at: bucket.resetTime };
  });
  // A quota bucket is evidence of usage availability, not an authenticated model catalog.
  return { status: rows.every((row) => row.remaining_fraction === 0) ? 'quota_exhausted' : 'metadata_verified',
    quota_models: rows, generation_qualified: false, inference_requested: false, credits_enabled: false };
}

export function metadataTransport(client) {
  let stage = 0;
  return { request: async (request) => {
    const method = stage === 0 ? 'loadCodeAssist' : stage === 1 ? 'retrieveUserQuota' : null;
    if (!method || request.url !== ENDPOINT + method || request.method !== 'POST'
        || request.responseType !== 'json' || typeof request.body !== 'string') fail('transport_scope');
    let body;
    try { body = JSON.parse(request.body); } catch { fail('transport_scope'); }
    if (method === 'loadCodeAssist') {
      if (JSON.stringify(body) !== JSON.stringify({ metadata: METADATA })) fail('transport_scope');
    } else if (!object(body) || Object.keys(body).length !== 1 || typeof body.project !== 'string'
        || !/^[a-z][a-z0-9-]{4,62}$/.test(body.project)) fail('transport_scope');
    stage++;
    try {
      // Replace every upstream transport option: no retry, redirect, proxy or credit fallback.
      return await client.request({ url: ENDPOINT + method, method: 'POST', body: JSON.stringify(body),
        headers: providerHeaders(), responseType: 'json', retry: false,
        retryConfig: { retry: 0, noResponseRetries: 0 }, maxRedirects: 0, redirect: 'error',
        timeout: 15_000, maxContentLength: 65_536 });
    } catch (error) {
      const status = error?.response?.status;
      const details = error?.response?.data?.error?.details;
      const reasons = Array.isArray(details) ? details.slice(0, 16).filter((item) =>
        item?.['@type'] === 'type.googleapis.com/google.rpc.ErrorInfo' && item.domain === 'googleapis.com'
      ).map((item) => item.reason) : [];
      if (status === 403 && reasons.includes('SERVICE_DISABLED')) fail('account_service_unavailable');
      if (status === 403 && reasons.includes('ACCESS_TOKEN_SCOPE_INSUFFICIENT')) fail('account_scope_denied');
      if (status === 403 && reasons.includes('USER_PROJECT_DENIED')) fail('project_access_denied');
      fail(status === 429 ? 'quota_exhausted' : status === 401 || status === 403 ? 'account_access_denied' : 'metadata_transport_failed');
    }
  } };
}

export async function existingAccount(core) {
  const settle = nativeOnlyStorage(core.KeychainService);
  const storage = new core.KeychainService('gemini-cli-oauth');
  await storage.getKeychainOrThrow();
  if (!await storage.getPassword('main-account')) fail('sign_in_required');
  let client;
  try {
    client = await core.getOauthClient(core.AuthType.LOGIN_WITH_GOOGLE, {
      getProxy: () => undefined, isBrowserLaunchSuppressed: () => true, isInteractive: () => false,
    });
    await settle();
    const saved = await storage.getPassword('main-account');
    if (!client.credentials?.access_token || !saved || JSON.parse(saved).token?.accessToken !== client.credentials.access_token) fail('credential_persistence_failed');
  } catch { fail('sign_in_required'); }
  return client;
}

export async function accountPreflight(core, client, now = Date.now()) {
  const server = new core.CodeAssistServer(metadataTransport(client));
  // Match the pinned CLI's initial account discovery. HEALTH_CHECK is used only
  // for later credit refresh with an already-known project, not initial discovery.
  const account = await server.loadCodeAssist({ metadata: METADATA });
  if (object(account) && !account.currentTier) {
    return { status: 'onboarding_required', onboarding: onboardingSummary(account),
      generation_qualified: false, inference_requested: false, credits_enabled: false };
  }
  const project = accountProject(account);
  const quota = await server.retrieveUserQuota({ project });
  return { ...quotaSnapshot(quota, now), tier: account.currentTier.id, paid_tier_present: Boolean(account.paidTier) };
}

export function isolatedConfig(workspace, browsing) {
  return {
    sessionId: 'ltt-inventory-only', targetDir: workspace, cwd: workspace, model: 'gemini-2.5-flash',
    coreTools: browsing ? ['google_web_search', 'web_fetch'] : [], mainAgentTools: browsing ? ['google_web_search', 'web_fetch'] : [],
    mcpEnabled: false, mcpServers: {}, extensionsEnabled: false, extensionManagement: false,
    enabledExtensions: [], includeDirectories: [], userMemory: '', geminiMdFilePaths: [],
    enableAgents: false, agents: {}, plan: false, tracker: false, skillsSupport: false, adminSkillsEnabled: false,
    enableHooks: false, enableHooksUI: false, hooks: {}, projectHooks: {}, enableConseca: false,
    experimentalAutoMemory: false, dynamicModelConfiguration: false, checkpointing: false,
    telemetry: { enabled: false }, usageStatisticsEnabled: false, interactive: false, acpMode: true,
    noBrowser: true, useRipgrep: false, useWriteTodos: false, includeDirectoryTree: false,
    retryFetchErrors: false, maxAttempts: 1, billing: { overageStrategy: 'never' },
    disableYoloMode: true, disableAlwaysAllow: true, approvalMode: 'default',
    policyEngineConfig: { defaultDecision: 'deny', nonInteractive: true,
      rules: browsing ? ['google_web_search', 'web_fetch'].map((toolName) => ({ toolName, decision: 'allow', priority: 10 })) : [],
      checkers: [], hookCheckers: [] },
  };
}

export async function toolInventory(core, workspace) {
  const inventories = [];
  for (const browsing of [false, true]) {
    const config = new core.Config(isolatedConfig(workspace, browsing));
    // Deliberately do not initialize sessions, agents, extension loaders or authentication.
    const registry = await config.createToolRegistry();
    const declarations = registry.getFunctionDeclarations();
    const expected = browsing ? ['google_web_search', 'web_fetch'] : [];
    const names = declarations.map((tool) => tool.name).sort();
    if (JSON.stringify(names) !== JSON.stringify(expected)
        || JSON.stringify(registry.getAllTools().map((tool) => tool.name).sort()) !== JSON.stringify(expected)) fail('tool_inventory_drift');
    const denied = ['run_shell_command', 'read_file', 'write_file', 'replace', 'activate_skill', 'agent', 'mcp__hostile__tool', 'unknown_tool'];
    for (const name of [...denied, ...expected]) {
      const result = await config.getPolicyEngine().check({ name, args: {} });
      if (result.decision !== (expected.includes(name) ? 'allow' : 'deny')) fail('tool_policy_drift');
    }
    inventories.push({ browsing, names, declarations_sha256: createHash('sha256').update(JSON.stringify(declarations)).digest('hex'), denied_checks: denied.length });
  }
  return { status: 'inventory_verified', inventories, generation_qualified: false, inference_requested: false, credits_enabled: false };
}
