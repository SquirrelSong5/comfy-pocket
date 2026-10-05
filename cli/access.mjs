import { isIP } from 'node:net';

function privateKind(host) {
  if (isIP(host) !== 4) return null;
  const [a,b] = host.split('.').map(Number);
  if (host === '127.0.0.1') return 'local';
  if (a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168)) return 'lan';
  if (a === 100 && b >= 64 && b <= 127) return 'vpn';
  return null;
}

export function getAccessCandidates(config, interfaces) {
  const addresses = new Map([['127.0.0.1', {host:'127.0.0.1',label:'本机 / Local'}]]);
  for (const [name, entries] of Object.entries(interfaces)) {
    for (const entry of entries || []) {
      const kind = privateKind(entry.address);
      if (!kind || (entry.internal && kind !== 'local')) continue;
      const tailscale = kind === 'vpn' && /tailscale/i.test(name);
      const virtual = /^(docker|veth|br-|virbr|vmnet|vboxnet|wg\d|tun\d|tap\d)|singbox|wintun/i.test(name);
      if (virtual && !tailscale && !(config.bind || []).includes(entry.address)) continue;
      const label = kind === 'local' ? '本机 / Local' : tailscale ? 'Tailscale' : virtual ? `虚拟网络 / Virtual (${name})` : kind === 'lan' ? `局域网 / LAN (${name})` : `VPN / CGNAT (${name})`;
      if (!addresses.has(entry.address) || tailscale) addresses.set(entry.address,{host:entry.address,label});
    }
  }
  for (const host of config.bind || []) {
    if (privateKind(host) && !addresses.has(host)) addresses.set(host,{host,label:'地址未检测到 / Interface not detected'});
  }
  return [...addresses.values()].map(address => ({...address, configured:(config.bind || []).includes(address.host) && (config.hosts || []).includes(address.host)}));
}

export function formatAccessSummary(candidates, readyHosts, configFile, port) {
  const lines=['\n访问地址 / Access addresses'];
  for (const {host,label,configured} of candidates) {
    const status = !configured ? '未开放 / Not enabled' : readyHosts.has(host) ? '本机探测成功 / Reachable locally' : '未就绪 / Not ready';
    lines.push(`  ${label}: http://${host}:${port}  [${status}]`);
  }
  if (!candidates.some(c => c.label === 'Tailscale')) lines.push('  未检测到 Tailscale 网卡 / No Tailscale interface detected.');
  if (candidates.some(c => !c.configured)) lines.push(`启用地址：编辑 ${configFile} 中的 bind、hosts、networks，然后重启。\nTo enable an address, edit bind, hosts and networks in that file, then restart.`);
  lines.push('手机需在同一局域网或连接 Tailscale；访问码在本机页面「手机访问」查看。',
    'Use the same LAN or Tailscale. Find the access code under Phone access on the local page.',
    '本机探测成功不代表已通过远端防火墙检查 / Local checks do not verify remote firewall access.');
  return lines.join('\n');
}

export async function printAccessSummary(config, configFile, interfaces, probe=fetch) {
  const candidates=getAccessCandidates(config,interfaces);
  const readyHosts=new Set();
  await Promise.all(candidates.filter(c=>c.configured).map(async c=>{
    try {
      const response=await probe(`http://${c.host}:${config.port}/api/session`,{signal:AbortSignal.timeout(1500)});
      if (response.ok && (await response.json()).product === 'comfy-pocket') readyHosts.add(c.host);
    } catch { /* A configured interface may not be connected yet. */ }
  }));
  console.log(formatAccessSummary(candidates,readyHosts,configFile,config.port));
}
