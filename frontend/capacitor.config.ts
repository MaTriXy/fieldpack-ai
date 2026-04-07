import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.fieldpackai.app',
  appName: 'FieldPack AI',
  webDir: 'dist',
  backgroundColor: '#1B4332',
  server: {
    cleartext: true, // Allow HTTP to LAN IP (Android 9+ blocks by default)
  },
  plugins: {
    CapacitorHttp: {
      enabled: false, // Disable to prevent WebSocket breakage (GH #7568)
    },
  },
};

export default config;
