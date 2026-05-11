# Frontend — Clinical Note Structuring Tool

React + Vite + TypeScript frontend.

## Getting started

```bash
npm install
npm run dev
```

Open http://localhost:5173.

## Build

```bash
npm run build
```

Output is emitted to `dist/` and can be hosted as static assets.

## Directory layout

- `src/pages/` — page components
- `src/components/` — reusable components
- `src/api/` — API call wrappers
- `src/store/` — zustand state management
- `src/lib/` — utility libraries (axios, queryClient)
- `src/routes.tsx` — routing configuration

## Environment variables

- `VITE_API_BASE_URL` — backend base URL (defaults to http://localhost:8000)

In dev mode, Vite proxies `/api` requests to the backend automatically.
