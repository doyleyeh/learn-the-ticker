import { existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { loginOnly } from './gemini_login_guard.mjs';

// Invoked only by connect_gemini.py after package/hash/environment validation.
const emit = process.stdout.write.bind(process.stdout);
const discard = (_chunk, encoding, callback) => {
  if (typeof encoding === 'function') encoding();
  if (typeof callback === 'function') callback();
  return true;
};
process.stdout.write = discard;
process.stderr.write = discard;
const finish = (status, code) => {
  emit(`${status}\n`, () => process.exit(code));
};
process.on('unhandledRejection', () => finish('sign_in_failed', 2));
process.on('uncaughtException', () => finish('sign_in_failed', 2));
process.on('SIGINT', () => finish('sign_in_cancelled', 2));
const deadline = setTimeout(() => finish('sign_in_timed_out', 2), 320_000);
try {
  const [mode, entry] = process.argv.slice(2);
  const profile = process.env.GEMINI_CLI_HOME;
  if (!profile || process.env.GEMINI_FORCE_ENCRYPTED_FILE_STORAGE !== 'true'
      || process.env.GEMINI_FORCE_FILE_STORAGE || !['--check', '--login'].includes(mode)) {
    throw new Error('Invalid launcher');
  }
  // Never import/migrate an existing file credential, including a prior fallback.
  for (const name of ['oauth_creds.json', 'gemini-credentials.json']) {
    if (existsSync(join(profile, '.gemini', name))) throw new Error('File credentials present');
  }
  mkdirSync(join(profile, 'workspace'), { recursive: true });
  process.chdir(join(profile, 'workspace'));
  const core = await import(pathToFileURL(entry).href);
  const status = await loginOnly(core, mode);
  clearTimeout(deadline);
  finish(status, 0);
} catch {
  finish('sign_in_failed', 2);
}
