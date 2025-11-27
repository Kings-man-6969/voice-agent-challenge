export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'ICICI Bank',
  pageTitle: 'ICICI Bank - Fraud Alert',
  pageDescription: 'Secure Fraud Detection Voice Agent',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg', // We will replace this later or use text
  accent: '#F37E20', // ICICI Orange
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#F37E20',
  startButtonText: 'Connect to Fraud Specialist',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
