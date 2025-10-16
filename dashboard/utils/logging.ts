type LogLevel = 'info' | 'warn' | 'error';

const PREFIX = '[dashboard]';

function log(level: LogLevel, component: string, message: string): void {
  const payload = `${PREFIX} ${component}: ${message}`;
  switch (level) {
    case 'warn':
      console.warn(payload);
      break;
    case 'error':
      console.error(payload);
      break;
    default:
      console.log(payload);
  }
}

export function logInfo(component: string, message: string): void {
  log('info', component, message);
}

export function logWarn(component: string, message: string): void {
  log('warn', component, message);
}

export function logError(component: string, message: string, error?: unknown): void {
  log('error', component, message);
  if (error) {
    console.error(error);
  }
}
