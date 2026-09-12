const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const { analyzeContext, assertResultIntegrity } = require('./src/contextproof');
const { ContextSourceError, DATA_MODES, loadContext } = require('./src/context-provider');
const { AnalysisModelError, analyzeWithOpenAI } = require('./src/openai-analyzer');

const HOST = '127.0.0.1';
const DEFAULT_PORT = 4173;
const MAX_BODY_BYTES = 16 * 1024;
const PUBLIC_DIR = path.join(__dirname, 'public');
const STATIC_FILES = new Map([
  ['/', { file: 'index.html', type: 'text/html; charset=utf-8' }],
  ['/index.html', { file: 'index.html', type: 'text/html; charset=utf-8' }],
  ['/app.js', { file: 'app.js', type: 'text/javascript; charset=utf-8' }],
  ['/styles.css', { file: 'styles.css', type: 'text/css; charset=utf-8' }],
]);

function setSecurityHeaders(response) {
  response.setHeader(
    'content-security-policy',
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
  );
  response.setHeader('x-content-type-options', 'nosniff');
  response.setHeader('referrer-policy', 'no-referrer');
  response.setHeader('x-frame-options', 'DENY');
}

function sendJson(response, statusCode, payload) {
  setSecurityHeaders(response);
  response.writeHead(statusCode, {
    'cache-control': 'no-store',
    'content-type': 'application/json; charset=utf-8',
  });
  response.end(JSON.stringify(payload));
}

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    let body = '';
    let bytes = 0;

    request.setEncoding('utf8');
    request.on('data', (chunk) => {
      bytes += Buffer.byteLength(chunk);
      if (bytes > MAX_BODY_BYTES) {
        reject(new TypeError('Request body is too large.'));
        request.destroy();
        return;
      }
      body += chunk;
    });
    request.on('end', () => {
      if (!body) {
        reject(new TypeError('A JSON request body is required.'));
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new TypeError('Request body must be valid JSON.'));
      }
    });
    request.on('error', reject);
  });
}

async function runAnalysis(context, options) {
  if (typeof options.analyzer === 'function') {
    const result = await options.analyzer(context);
    return {
      analysisMode: options.analysisMode || 'INJECTED_ANALYZER',
      result: assertResultIntegrity(result, context.posts),
    };
  }

  if (context.data_mode === DATA_MODES.LIVE_THREADS) {
    return {
      analysisMode: 'OPENAI_STRUCTURED',
      result: await analyzeWithOpenAI(context, options.openaiOptions || {}),
    };
  }

  return {
    analysisMode: 'DETERMINISTIC_FALLBACK',
    result: analyzeContext(context),
  };
}

async function serveStatic(pathname, response) {
  const asset = STATIC_FILES.get(pathname);
  if (!asset) {
    sendJson(response, 404, { error: 'NOT_FOUND', message: 'Route not found.' });
    return;
  }

  const content = await fs.promises.readFile(path.join(PUBLIC_DIR, asset.file));
  setSecurityHeaders(response);
  response.writeHead(200, {
    'cache-control': 'no-cache',
    'content-type': asset.type,
  });
  response.end(content);
}

function createAppServer(options = {}) {
  const dataMode = options.dataMode || process.env.CONTEXT_DATA_MODE || DATA_MODES.DEMO_FALLBACK_DATA;

  return http.createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url, 'http://' + (request.headers.host || 'localhost'));

      if (request.method === 'GET' && requestUrl.pathname === '/api/health') {
        sendJson(response, 200, {
          status: 'ok',
          data_mode: dataMode,
          analysis_engine: dataMode === DATA_MODES.LIVE_THREADS
            ? (process.env.OPENAI_API_KEY ? 'OPENAI_STRUCTURED' : 'BLOCKED_MISSING_OPENAI_CREDENTIALS')
            : 'DETERMINISTIC_FALLBACK',
          threads_status: process.env.THREADS_ACCESS_TOKEN
            ? 'CREDENTIAL_PRESENT_LIVE_ADAPTER_READY'
            : 'BLOCKED_MISSING_CREDENTIALS',
        });
        return;
      }

      if (request.method === 'GET' && requestUrl.pathname === '/favicon.ico') {
        setSecurityHeaders(response);
        response.writeHead(204, { 'cache-control': 'public, max-age=86400' });
        response.end();
        return;
      }

      if (request.method === 'POST' && requestUrl.pathname === '/api/analyze') {
        const body = await readJsonBody(request);
        const context = await loadContext(body.query, {
          dataMode,
          liveProvider: options.liveProvider,
          threadsOptions: options.threadsOptions,
        });
        const analysis = await runAnalysis(context, options);

        sendJson(response, 200, {
          query: context.query,
          data_mode: context.data_mode,
          analysis_mode: analysis.analysisMode,
          source_notice: context.source_notice,
          result: analysis.result,
          sources: context.posts.map((item) => ({
            id: item.id,
            text: item.text,
            author: item.author,
            url: item.url,
            created_at: item.created_at,
          })),
        });
        return;
      }

      if (request.method === 'GET') {
        await serveStatic(requestUrl.pathname, response);
        return;
      }

      sendJson(response, 405, { error: 'METHOD_NOT_ALLOWED', message: 'Method not allowed.' });
    } catch (error) {
      if (error instanceof ContextSourceError) {
        sendJson(response, 503, { error: error.code, message: error.message });
        return;
      }

      if (error instanceof AnalysisModelError) {
        sendJson(response, 503, { error: error.code, message: error.message });
        return;
      }

      if (error instanceof TypeError) {
        sendJson(response, 400, { error: 'INVALID_REQUEST', message: error.message });
        return;
      }

      console.error(error);
      sendJson(response, 500, { error: 'INTERNAL_ERROR', message: 'Context analysis failed.' });
    }
  });
}

if (require.main === module) {
  const port = Number.parseInt(process.env.PORT || String(DEFAULT_PORT), 10);
  const server = createAppServer();
  server.listen(port, HOST, () => {
    console.log('ContextProof running at http://' + HOST + ':' + port);
    console.log('Data mode: ' + (process.env.CONTEXT_DATA_MODE || DATA_MODES.DEMO_FALLBACK_DATA));
  });
}

module.exports = {
  createAppServer,
};
