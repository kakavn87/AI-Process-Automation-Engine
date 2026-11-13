import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const frontendServiceHost = 'ai-process-automation-frontend-4bsh';
const backendServiceHost = 'ai-process-automation-backend-4bsh';
const productionApiBaseUrl = 'https://ai-process-automation-backend-4bsh.onrender.com';

function getHostname(value = '') {
  const input = value.trim();
  if (!input) return '';

  try {
    return input.includes('://') ? new URL(input).hostname : input.split('/')[0].split(':')[0];
  } catch {
    return '';
  }
}

function inferPreviewApiBaseUrl() {
  const host = getHostname(
    process.env.RENDER_EXTERNAL_HOSTNAME || process.env.RENDER_EXTERNAL_URL || ''
  );
  const match = host.match(
    new RegExp('^' + frontendServiceHost + '(-pr-[0-9]+)\\.onrender\\.com$', 'i')
  );

  if (!match) return '';
  return 'https://' + backendServiceHost + match[1] + '.onrender.com';
}

const isPullRequest = (process.env.IS_PULL_REQUEST || '').toLowerCase() === 'true';
const explicitApiBaseUrl = (process.env.API_BASE_URL || '').trim();
const previewApiBaseUrl = (process.env.PREVIEW_API_BASE_URL || '').trim();

const apiBaseUrl = isPullRequest
  ? (previewApiBaseUrl || inferPreviewApiBaseUrl())
  : (explicitApiBaseUrl || productionApiBaseUrl);

const runtimeConfig = {
  apiBaseUrl: apiBaseUrl.replace(/\/+$/, ''),
  isPreview: isPullRequest
};

if (isPullRequest && !runtimeConfig.apiBaseUrl) {
  console.warn(
    'Render PR preview detected, but its matching backend preview URL could not be derived. ' +
    'API calls are disabled rather than falling back to Production.'
  );
}

const target = fileURLToPath(new URL('../src/runtime-config.js', import.meta.url));
const output = 'window.__FLOWPILOT_RUNTIME_CONFIG__ = Object.freeze(' +
  JSON.stringify(runtimeConfig) +
  ');\n';

await writeFile(target, output, 'utf8');
console.info(
  isPullRequest
    ? 'Generated PR Preview runtime config: ' + (runtimeConfig.apiBaseUrl || 'API disabled (fail closed)')
    : 'Generated Production runtime config: ' + runtimeConfig.apiBaseUrl
);
