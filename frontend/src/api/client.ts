// Web app's API client instance. All logic lives in @lakasmarket/shared so the
// web and React Native apps stay in lock-step; this file only wires in the
// browser-specific base URL and (default in-memory) token storage.
import { createApiClient } from "@lakasmarket/shared";
export type { Offer, Subscription } from "@lakasmarket/shared";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = createApiClient(BASE_URL);
