# Vercel Backend Docs

This folder only contains the operational docs for running, testing, debugging, and deploying the backend on Vercel.

## Docs In This Folder

- [Deployment Guide](./deployment-guide.md)
  - Local Python setup.
  - Required commands before deploy.
  - Recommended Vercel settings.
- [Verification And Health Checks](./verification-and-health-checks.md)
  - How to run the backend locally.
  - How to test imports, health endpoints, auth, and matching.
- [Manual Vercel Debug Session](./manual-vercel-debug-session.md)
  - What to inspect in Vercel when deploys succeed but runtime still fails.

## Recommended Order

1. Use [Deployment Guide](./deployment-guide.md) to set up the correct Python environment and deploy settings.
2. Use [Verification And Health Checks](./verification-and-health-checks.md) to run and test locally before deploy.
3. If Vercel still fails, use [Manual Vercel Debug Session](./manual-vercel-debug-session.md).
