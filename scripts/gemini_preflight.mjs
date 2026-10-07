import { existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { accountPreflight, existingAccount, toolInventory, PreflightFailure } from './gemini_preflight_guard.mjs';

const emit = process.stdout.write.bind(process.stdout);
const discard = (_chunk, encoding, callback) => {
  if (typeof encoding === 'function') encoding();
  if (typeof callback === 'function') callback();
  return true;
};
process.stdout.write = discard;
process.stderr.write = discard;
let phase = 'runtime_load';
const finish = (value, code) => emit(`${JSON.stringify(value)}\n`, () => process.exit(code));
const failed = (status) => finish({ status, phase, generation_qualified: false, inference_requested: false, credits_enabled: false }, 2);
process.on('uncaughtException', () => failed('unexpected_failure'));
process.on('unhandledRejection', () => failed('unexpected_failure'));
process.on('SIGINT', () => failed('cancelled'));
setTimeout(() => failed('timed_out'), 75_000);
try {
  const [mode, entry] = process.argv.slice(2);
  // Google's consumer CLI service ended on 2026-06-18. Stop before loading
  // any runtime, touching its profile/keyring or attempting account setup.
  if (mode === '--complete-free-setup') throw new PreflightFailure('consumer_setup_retired');
  const profile = process.env.GEMINI_CLI_HOME;
  if (!['--inventory', '--live'].includes(mode) || !profile
      || process.env.GEMINI_FORCE_ENCRYPTED_FILE_STORAGE !== 'true' || process.env.GEMINI_FORCE_FILE_STORAGE) {
    throw new PreflightFailure('invalid_launcher');
  }
  for (const name of ['oauth_creds.json', 'gemini-credentials.json']) {
    if (existsSync(join(profile, '.gemini', name))) throw new PreflightFailure('file_credentials_present');
  }
  const workspace = join(profile, 'workspace');
  mkdirSync(workspace, { recursive: true });
  process.chdir(workspace);
  const core = await import(pathToFileURL(entry).href);
  if (mode === '--inventory') {
    phase = 'inventory';
    finish(await toolInventory(core, workspace), 0);
  } else {
    phase = 'authentication';
    const client = await existingAccount(core);
    phase = 'metadata';
    const report = await accountPreflight(core, client);
    finish(report, report.status === 'metadata_verified' ? 0 : 2);
  }
} catch (error) {
  failed(error instanceof PreflightFailure ? error.code : 'unexpected_failure');
}
