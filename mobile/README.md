# LakasMarket Mobile (React Native / Expo)

The mobile client. It **reuses `@lakasmarket/shared`** — the same API client,
domain types, and anti-lowball logic that power the web dashboard — so the two
apps never drift apart.

## Why it's separate from the npm workspace

Expo/React Native pull in a large, platform-specific dependency tree, so this
package is intentionally **not** part of the root `workspaces` (that keeps web
CI fast). It resolves the shared package directly from source via Metro (see
`metro.config.js`) and TypeScript path mapping (see `tsconfig.json`).

## Running

```bash
cd mobile
npm install
EXPO_PUBLIC_API_URL=http://<your-machine-ip>:8000 npm start
```

- **Android emulator:** the default `http://10.0.2.2:8000` reaches the host's
  backend automatically.
- **Physical device:** set `EXPO_PUBLIC_API_URL` to your machine's LAN IP.

## What's here

- `App.tsx` — auth gate switching between Login and Browse.
- `src/api.ts` — one line: `createApiClient(BASE_URL)` from the shared package.
- `src/screens/LoginScreen.tsx` — sign in.
- `src/screens/BrowseScreen.tsx` — active listings with seller Adab and the
  hard-floor notice, rendered from the shared `Listing` type.

## Next steps

Wire in the offer/quiz flow and Specs Guard screens — all the client methods
(`makeOffer`, `askSpecsGuard`, `offerAction`, …) already exist in the shared
client, so the screens are all that's left to build.
