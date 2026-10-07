import assert from 'node:assert/strict';
import { loginOnly, nativeOnlyStorage, SERVICE } from '../../scripts/gemini_login_guard.mjs';

function fixture({ available = true, writeFails = false } = {}) {
  const reads = []; const writes = []; const values = new Map();
  const native = {
    getPassword: async (service, account) => { reads.push([service, account]); return values.get(account); },
    setPassword: async (service, account, value) => {
      writes.push([service, account]);
      if (writeFails) throw new Error('synthetic private diagnostic');
      values.set(account, value);
    },
  };
  class KeychainService {
    constructor(service) { this.serviceName = service; }
    async getNativeKeychain() { assert.equal(this.serviceName, SERVICE); return available ? native : null; }
    async getKeychainOrThrow() { return this.cached ??= await this.initializeKeychain(); }
    async getPassword(account) { const key = await this.getKeychainOrThrow(); return key.getPassword(this.serviceName, account); }
    async setPassword(account, value) { const key = await this.getKeychainOrThrow(); return key.setPassword(this.serviceName, account, value); }
    async initializeKeychain() { throw new Error('Unprotected fallback reached'); }
  }
  let authCalls = 0;
  const core = { KeychainService, AuthType: { LOGIN_WITH_GOOGLE: 'oauth-personal' },
    getOauthClient: async (type, config) => {
      authCalls++;
      assert.equal(type, 'oauth-personal');
      assert.equal(config.isBrowserLaunchSuppressed(), false);
      assert.equal(config.getAcpMode(), true);
      assert.equal(config.getProxy(), undefined);
      await new KeychainService('gemini-cli-oauth').setPassword('main-account', JSON.stringify({ token: { accessToken: 'synthetic' } }));
      return { credentials: { access_token: 'synthetic' } };
    },
  };
  return { core, reads, writes, authCalls: () => authCalls };
}

const check = fixture();
assert.equal(await loginOnly(check.core, '--check'), 'native_storage_ready');
assert.equal(check.authCalls(), 0);
assert.equal(check.reads.length, 0);
assert.equal(check.writes.length, 0);

const unavailable = fixture({ available: false });
await assert.rejects(loginOnly(unavailable.core, '--login'), /Native credential storage unavailable/);
assert.equal(unavailable.authCalls(), 0);

const valid = fixture();
assert.equal(await loginOnly(valid.core, '--login'), 'authenticated');
assert.equal(valid.authCalls(), 1);
assert.deepEqual(valid.writes, [[SERVICE, 'main-account']]);
assert.deepEqual(valid.reads, [[SERVICE, 'main-account']]);

const failed = fixture({ writeFails: true });
const settle = nativeOnlyStorage(failed.core.KeychainService);
await assert.rejects(new failed.core.KeychainService('gemini-cli-oauth').setPassword('main-account', 'synthetic'));
await assert.rejects(settle(), /Credential storage failed/);
await assert.rejects(new failed.core.KeychainService('foreign-service').getKeychainOrThrow(), /Unexpected credential service/);

const missing = fixture();
missing.core.getOauthClient = async () => ({ credentials: { access_token: 'synthetic' } });
await assert.rejects(loginOnly(missing.core, '--login'), /persistence unverified/);
await assert.rejects(loginOnly(fixture().core, '--unknown'), /Explicit mode required/);
process.stdout.write('guard_scenarios_passed\n');
