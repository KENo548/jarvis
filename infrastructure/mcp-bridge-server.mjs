import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const registryPath = join(__dirname, '..', 'mcp-servers', 'mcp-registry.json');
const processes = new Map();

async function loadRegistry() {
  const raw = await readFile(registryPath, 'utf8');
  return JSON.parse(raw);
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) });
  res.end(body);
}

async function startServer(name) {
  const payload = await loadRegistry();
  const cfg = payload.mcp_servers?.[name];
  const cmd = cfg?.install_command;
  if (!cmd) {
    throw new Error(`Unknown MCP server: ${name}`);
  }
  const [binary, ...args] = cmd.split(' ');
  const proc = process.platform === 'win32'
    ? spawn('cmd.exe', ['/c', cmd], { stdio: ['pipe', 'pipe', 'pipe'] })
    : spawn(binary, args, { stdio: ['pipe', 'pipe', 'pipe'] });
  proc.stderr.on('data', chunk => process.stderr.write(chunk));

  const initialize = JSON.stringify({
    jsonrpc: '2.0',
    id: 0,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'jarvis-bridge', version: '1.0.0' },
    },
  }) + '\n';

  proc.stdin.write(initialize);
  await new Promise((resolve, reject) => {
    let buffer = '';
    const onData = chunk => {
      buffer += chunk.toString('utf8');
      const lineEnd = buffer.indexOf('\n');
      if (lineEnd !== -1) {
        proc.stdout.off('data', onData);
        resolve();
      }
    };
    proc.stdout.on('data', onData);
    proc.once('error', reject);
    proc.once('exit', code => reject(new Error(`MCP server exited during initialize with code ${code}`)));
  });

  return proc;
}

async function mcpRequest(proc, method, params) {
  const request = JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) + '\n';
  return await new Promise((resolve, reject) => {
    let buffer = '';
    const onData = chunk => {
      buffer += chunk.toString('utf8');
      const lineEnd = buffer.indexOf('\n');
      if (lineEnd === -1) {
        return;
      }
      proc.stdout.off('data', onData);
      const line = buffer.slice(0, lineEnd).trim();
      if (!line) {
        reject(new Error('Empty response from MCP server'));
        return;
      }
      const resp = JSON.parse(line);
      if (resp.error) {
        reject(new Error(`MCP error: ${JSON.stringify(resp.error)}`));
        return;
      }
      resolve(resp.result ?? {});
    };
    proc.stdout.on('data', onData);
    proc.stdin.write(request);
    proc.once('error', reject);
    proc.once('exit', code => reject(new Error(`MCP server exited with code ${code}`)));
  });
}

const server = createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    sendJson(res, 200, { status: 'ok', servers: [...processes.keys()] });
    return;
  }

  if (req.method === 'POST' && (req.url === '/call' || req.url === '/tools/call')) {
    let body = '';
    for await (const chunk of req) {
      body += chunk.toString('utf8');
    }

    let data;
    try {
      data = body ? JSON.parse(body) : {};
    } catch (error) {
      sendJson(res, 400, { error: { code: -32700, message: 'Invalid JSON body' } });
      return;
    }

    const serverName = data.server ?? 'search-mcp';
    const tool = data.tool ?? 'search';
    const argumentsObject = data.arguments ?? {};

    try {
      if (!processes.has(serverName)) {
        processes.set(serverName, await startServer(serverName));
      }
      const result = await mcpRequest(processes.get(serverName), 'tools/call', { name: tool, arguments: argumentsObject });
      sendJson(res, 200, { jsonrpc: '2.0', id: 1, result });
    } catch (error) {
      sendJson(res, 502, { jsonrpc: '2.0', id: 1, error: { code: -1, message: String(error.message ?? error) } });
    }
    return;
  }

  sendJson(res, 404, { error: { code: 404, message: 'Not Found' } });
});

const port = Number(process.argv[2] ?? 8099);
server.listen(port, '0.0.0.0', () => {
  console.log(`MCP bridge listening on ${port}`);
});
