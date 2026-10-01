import assert from 'node:assert/strict';
import path from 'node:path';
import { test } from 'node:test';

import { makeConfig, parseArgs } from '../cli/options.mjs';

test('parseArgs keeps safe defaults for an existing local ComfyUI', () => {
  const options = parseArgs([]);

  assert.deepEqual(options.hosts, []);
  assert.equal(options.open, true);
  assert.equal(options.setupOnly, undefined);
  assert.equal(options.help, undefined);
});

test('parseArgs accepts all supported launcher options and repeatable hosts', () => {
  const options = parseArgs([
    '--home', 'C:\\Users\\me\\.comfy-pocket',
    '--python', 'E:\\ExampleEngine\\.venv\\Scripts\\python.exe',
    '--comfy-dir', 'E:\\ExampleEngine',
    '--comfy-url', 'http://127.0.0.1:8188',
    '--port', '8200',
    '--host', '100.80.20.10',
    '--host', '192.168.1.20',
    '--no-open',
    '--setup-only',
    '--help',
  ]);

  assert.deepEqual(options, {
    home: 'C:\\Users\\me\\.comfy-pocket',
    python: 'E:\\ExampleEngine\\.venv\\Scripts\\python.exe',
    comfyDir: 'E:\\ExampleEngine',
    comfyUrl: 'http://127.0.0.1:8188',
    port: 8200,
    hosts: ['100.80.20.10', '192.168.1.20'],
    open: false,
    setupOnly: true,
    help: true,
  });
});

test('makeConfig defaults to loopback-only access and no runtime controller', () => {
  assert.deepEqual(makeConfig(parseArgs([])), {
    comfy_url: 'http://127.0.0.1:8188',
    port: 8189,
    bind: ['127.0.0.1'],
    hosts: ['127.0.0.1', 'localhost'],
    networks: ['127.0.0.0/8'],
    runtime: null,
  });
});

test('makeConfig expands repeatable IPv4 hosts to the matching access networks', () => {
  const config = makeConfig(parseArgs([
    '--host', '100.80.20.10',
    '--host', '100.80.20.10',
    '--host', '192.168.1.20',
  ]));

  assert.deepEqual(config.bind, ['127.0.0.1', '100.80.20.10', '192.168.1.20']);
  assert.deepEqual(config.hosts, [
    '127.0.0.1',
    '100.80.20.10',
    '192.168.1.20',
    'localhost',
  ]);
  assert.deepEqual(config.networks, [
    '127.0.0.0/8',
    '100.64.0.0/10',
    '192.168.1.0/24',
  ]);
});

test('makeConfig creates a guarded ComfyUI runtime only when comfyDir is supplied', () => {
  const options = parseArgs([
    '--comfy-dir', 'E:\\ExampleEngine',
    '--python', 'E:\\ExampleEngine\\.venv\\Scripts\\python.exe',
    '--comfy-url', 'http://127.0.0.1:8188',
    '--port', '8201',
  ]);
  const config = makeConfig(options);
  const comfyDir = path.resolve('E:\\ExampleEngine');

  assert.equal(config.port, 8201);
  assert.deepEqual(config.runtime, {
    cwd: comfyDir,
    executable: 'E:\\ExampleEngine\\.venv\\Scripts\\python.exe',
    args: [
      '-s',
      path.join(comfyDir, 'main.py'),
      '--disable-auto-launch',
      '--listen',
      '127.0.0.1',
      '--port',
      '8188',
    ],
  });
  assert.equal(makeConfig(parseArgs([])).runtime, null);
});

test('parseArgs rejects unknown options, missing values, and illegal ports', () => {
  assert.throws(() => parseArgs(['--unknown']), /Unknown option/);
  assert.throws(() => parseArgs(['--port']), /Missing value for --port/);

  for (const value of ['not-a-number', '1023', '65536', '8200.5']) {
    assert.throws(
      () => parseArgs(['--port', value]),
      /--port must be an integer from 1024 to 65535/,
      `port ${value} should be rejected`,
    );
  }
});

test('parseArgs only accepts concrete IPv4 host bindings', () => {
  assert.throws(() => parseArgs(['--host']), /--host requires a specific IPv4 address/);
  assert.throws(() => parseArgs(['--host', '0.0.0.0']), /--host requires a specific IPv4 address/);
  assert.throws(() => parseArgs(['--host', '::1']), /--host requires a specific IPv4 address/);
  assert.throws(() => parseArgs(['--host', 'example.test']), /--host requires a specific IPv4 address/);
});

test('parseArgs normalizes a backend URL to its origin and rejects unsafe URL forms', () => {
  assert.equal(
    parseArgs(['--comfy-url', 'https://localhost:8188/']).comfyUrl,
    'https://localhost:8188',
  );
  assert.throws(() => parseArgs(['--comfy-url', 'http://user:pass@127.0.0.1:8188']), /--comfy-url/);
  assert.throws(() => parseArgs(['--comfy-url', 'http://127.0.0.1:8188/api']), /--comfy-url/);
  assert.throws(() => parseArgs(['--comfy-url', 'ftp://127.0.0.1:8188']), /--comfy-url/);
});

test('makeConfig refuses remote process control targets', () => {
  assert.throws(
    () => makeConfig(parseArgs([
      '--comfy-dir', 'E:\\ExampleEngine',
      '--python', 'E:\\ExampleEngine\\.venv\\Scripts\\python.exe',
      '--comfy-url', 'http://192.168.1.20:8188',
    ])),
    /Local process control requires a loopback --comfy-url/,
  );
  assert.throws(
    () => makeConfig(parseArgs(['--comfy-dir', 'E:\\ExampleEngine'])),
    /Local process control requires a ComfyUI Python executable/,
  );
});
