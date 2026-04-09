import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.fieldpackai.app',
  appName: 'FieldPack AI',
  webDir: 'dist',
  backgroundColor: '#1B4332',
  server: {
    // Required: Android 9+ blocks cleartext HTTP by default.
    // FieldPack communicates over a private LAN hotspot (no TLS CA available).
    // Risk: accepted for closed-network field deployment.
    cleartext: true,
  },
  plugins: {
    CapacitorHttp: {
      // MUST stay false: Capacitor's HTTP plugin intercepts fetch() and breaks
      // WebSocket upgrade handshakes. See capacitor-community/http#7568.
      // Native fetch() works correctly for our use case.
      enabled: false,
    },
  },
};

export default config;
