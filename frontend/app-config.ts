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
  companyName: 'Improv Battle',
  pageTitle: 'Improv Battle - Voice AI Game Show',
  pageDescription: 'A voice-first improv game show powered by AI',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#9333ea',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#c084fc',
  startButtonText: 'Start Improv Battle',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
