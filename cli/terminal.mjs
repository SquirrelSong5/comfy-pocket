// Keep redirected output readable and respect terminals that disable ANSI colors.
const enabled = process.stdout.isTTY && !('NO_COLOR' in process.env) && process.env.TERM !== 'dumb';
const paint = code => text => enabled ? `\x1b[${code}m${text}\x1b[0m` : String(text);

export const terminal = {
  title: paint('1;36'),
  link: paint('36'),
  success: paint('32'),
  warning: paint('33'),
  muted: paint('90'),
  command: paint('1'),
};
