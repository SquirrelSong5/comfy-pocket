import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatAccessSummary, getAccessCandidates } from '../cli/access.mjs';

function interfaceEntry(address, internal = false) {
  return { address, family: 'IPv4', internal };
}

test('getAccessCandidates keeps loopback and classifies LAN, Tailscale, and CGNAT addresses', () => {
  const candidates = getAccessCandidates(
    {
      bind: ['127.0.0.1', '192.168.50.20', '100.64.20.8', '192.168.50.99'],
      hosts: ['127.0.0.1', '192.168.50.20', '100.64.20.8', '192.168.50.99'],
    },
    {
      Ethernet: [interfaceEntry('192.168.50.20')],
      Tailscale: [interfaceEntry('100.64.20.8')],
      WireGuard: [interfaceEntry('100.100.20.9')],
      Public: [interfaceEntry('198.51.100.4')],
      Loopback: [interfaceEntry('127.0.0.1', true)],
      IPv6: [{ address: '2001:db8::20', family: 'IPv6', internal: false }],
      LinkLocal: [interfaceEntry('169.254.20.8')],
    },
  );

  assert.deepEqual(
    candidates.map(({ host, label, configured }) => ({ host, label, configured })),
    [
      { host: '127.0.0.1', label: '本机 / Local', configured: true },
      { host: '192.168.50.20', label: '局域网 / LAN (Ethernet)', configured: true },
      { host: '100.64.20.8', label: 'Tailscale', configured: true },
      { host: '100.100.20.9', label: 'VPN / CGNAT (WireGuard)', configured: false },
      { host: '192.168.50.99', label: '地址未检测到 / Interface not detected', configured: true },
    ],
  );
});

test('getAccessCandidates de-duplicates interface addresses and requires bind plus hosts', () => {
  const candidates = getAccessCandidates(
    { bind: ['127.0.0.1', '10.20.30.40'], hosts: ['127.0.0.1'] },
    {
      Ethernet: [interfaceEntry('10.20.30.40'), interfaceEntry('10.20.30.40')],
      WiFi: [interfaceEntry('10.20.30.40')],
    },
  );

  assert.equal(candidates.filter(({ host }) => host === '10.20.30.40').length, 1);
  assert.equal(candidates.find(({ host }) => host === '10.20.30.40').configured, false);
});

test('getAccessCandidates enforces RFC1918 and CGNAT boundaries', () => {
  const addresses = [
    '10.0.0.1', '10.255.255.254',
    '172.15.255.255', '172.16.0.1', '172.31.255.254', '172.32.0.1',
    '192.167.255.255', '192.168.0.1', '192.168.255.254',
    '100.63.255.255', '100.64.0.1', '100.127.255.254', '100.128.0.1',
  ];
  const interfaces = Object.fromEntries(addresses.map((address, index) => [
    `Adapter-${index}`,
    [interfaceEntry(address)],
  ]));
  const hosts = getAccessCandidates({ bind: ['127.0.0.1'], hosts: ['127.0.0.1'] }, interfaces)
    .map(({ host }) => host);

  assert.deepEqual(hosts, [
    '127.0.0.1',
    '10.0.0.1', '10.255.255.254',
    '172.16.0.1', '172.31.255.254',
    '192.168.0.1', '192.168.255.254',
    '100.64.0.1', '100.127.255.254',
  ]);
});

test('formatAccessSummary reports reachable, not-ready, and unopened addresses', () => {
  const candidates = [
    { host: '127.0.0.1', label: '本机 / Local', configured: true },
    { host: '192.168.50.20', label: '局域网 / LAN (Ethernet)', configured: true },
    { host: '100.64.20.8', label: 'Tailscale', configured: false },
  ];
  const summary = formatAccessSummary(candidates, new Set(['127.0.0.1']), 'C:\\Users\\me\\.comfy-pocket\\config.json', 8189);

  assert.match(summary, /http:\/\/127\.0\.0\.1:8189/);
  assert.match(summary, /本机探测成功 \/ Reachable locally/);
  assert.match(summary, /http:\/\/192\.168\.50\.20:8189/);
  assert.match(summary, /未就绪 \/ Not ready/);
  assert.match(summary, /Tailscale/);
  assert.match(summary, /未开放 \/ Not enabled/);
  assert.match(summary, /config\.json/);
  assert.match(summary, /手机需在同一局域网或连接 Tailscale/);
  assert.doesNotMatch(summary, /未检测到 Tailscale 网卡/);
});

test('getAccessCandidates hides unconfigured virtual adapters but keeps an explicitly bound one', () => {
  const candidates = getAccessCandidates(
    { bind: ['127.0.0.1', '172.20.0.3'], hosts: ['127.0.0.1', '172.20.0.3'] },
    {
      'vEthernet (Default Switch)': [interfaceEntry('172.20.0.3')],
      docker0: [interfaceEntry('172.18.0.2')],
    },
  );

  assert.deepEqual(
    candidates.map(({ host, label, configured }) => ({ host, label, configured })),
    [
      { host: '127.0.0.1', label: '本机 / Local', configured: true },
      { host: '172.20.0.3', label: '虚拟网络 / Virtual (vEthernet (Default Switch))', configured: true },
    ],
  );
});

test('formatAccessSummary reminds the user when Tailscale is absent', () => {
  const summary = formatAccessSummary(
    [{ host: '127.0.0.1', label: '本机 / Local', configured: true }],
    new Set(),
    'C:\\Users\\me\\.comfy-pocket\\config.json',
    8189,
  );

  assert.match(summary, /未检测到 Tailscale 网卡 \/ No Tailscale interface detected/);
  assert.match(summary, /未就绪 \/ Not ready/);
});
