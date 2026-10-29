import { createApiClient } from "@lakasmarket/shared";

// Point at your backend. For the Android emulator, 10.0.2.2 maps to the host
// machine's localhost; for a physical device use your machine's LAN IP.
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8000";

// Uses the default in-memory token store. Swap in a SecureStore-backed
// TokenStore here to persist the session across app restarts.
export const api = createApiClient(BASE_URL);
