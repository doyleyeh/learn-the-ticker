// Developer-only bridge for the pinned Gemini OAuth implementation. No model/session API.
export const SERVICE = 'LearnTheTicker.Gemini.Qualification';

export function nativeOnlyStorage(KeychainService) {
  const pending = new Set();
  let failed = false;
  KeychainService.prototype.initializeKeychain = async function () {
    if (this.serviceName !== 'gemini-cli-oauth') throw new Error('Unexpected credential service');
    this.serviceName = SERVICE;
    const native = await this.getNativeKeychain();
    if (!native) throw new Error('Native credential storage unavailable');
    return {
      getPassword: (service, account) => native.getPassword(service, account),
      deletePassword: (service, account) => native.deletePassword(service, account),
      findCredentials: (service) => native.findCredentials(service),
      setPassword: (service, account, value) => {
        const write = Promise.resolve().then(() => native.setPassword(service, account, value));
        pending.add(write);
        // The provider's token event is asynchronous; retain failure even after it settles.
        write.then(() => pending.delete(write), () => { failed = true; pending.delete(write); });
        return write;
      },
    };
  };
  return async () => {
    await Promise.allSettled([...pending]);
    if (failed) throw new Error('Credential storage failed');
  };
}

export async function loginOnly(core, mode) {
  if (!['--check', '--login'].includes(mode)) throw new Error('Explicit mode required');
  const settle = nativeOnlyStorage(core.KeychainService);
  // Native synthetic write/read/delete happens before opening a browser or reading auth.
  const storage = new core.KeychainService('gemini-cli-oauth');
  await storage.getKeychainOrThrow();
  if (mode === '--check') return 'native_storage_ready';
  const client = await core.getOauthClient(core.AuthType.LOGIN_WITH_GOOGLE, {
    getProxy: () => undefined,
    isBrowserLaunchSuppressed: () => false,
    // The caller explicitly requested login; Google still asks for account/consent.
    getAcpMode: () => true,
  });
  await settle();
  const saved = await storage.getPassword('main-account');
  if (!client.credentials?.access_token || !saved
      || JSON.parse(saved).token?.accessToken !== client.credentials.access_token) {
    throw new Error('Native credential persistence unverified');
  }
  return 'authenticated';
}
