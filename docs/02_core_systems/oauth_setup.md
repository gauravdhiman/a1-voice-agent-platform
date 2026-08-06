# OAuth Provider Setup Guide

This guide explains how to configure OAuth providers like Google for your SaaS application.

## Google OAuth Setup

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (required for OAuth)

### 2. Configure OAuth Consent Screen

1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (or "Internal" if using Google Workspace)
3. Fill in the required application information:
   - App name: Your application name
   - User support email: Your support email
   - Developer contact information: Your email
4. Add the following scopes:
   - `../auth/userinfo.email`
   - `../auth/userinfo.profile`
   - `openid`
5. Add your domain to "Authorized domains"
6. Save the consent screen

### 3. Create OAuth Credentials (redirect flow)

1. Go to **APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add **Authorized redirect URIs** for the **backend** callback (not the frontend):

```text
http://localhost:8000/api/v1/auth/google/callback
https://api.247ai.live/api/v1/auth/google/callback
```

4. Copy the Client ID and Client Secret into the root `.env`:

```text
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID=...
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET=...
API_BASE_URL=http://localhost:8000
```

See [Backend redirect OAuth](../02_features/authentication_rbac/backend-redirect-oauth.md)
for the full sequence diagram.

Optional **Authorized JavaScript origins** (not required for backend redirect, but
harmless if present):

```text
http://localhost:3000
https://www.247ai.live
```

### 4. Configure environment variables

Add to the root `.env` (Docker Compose):

```text
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000

SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID=...
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET=...
JWT_SECRET_KEY=...
```

The frontend does **not** need `NEXT_PUBLIC_GOOGLE_CLIENT_ID` for sign-in; buttons
link to the backend authorize route.

### 5. Local Supabase configuration

Local Supabase Auth can keep Google enabled in `supabase/config.toml` for
compatibility. The backend redirect flow mints sessions via the admin API and
does not rely on frontend `signInWithIdToken`.

Restart local Supabase after changing Google credentials:

```bash
supabase stop
supabase start
```

### 6. Test the integration

1. Start the dev stack: `./start.sh start dev`
2. Open the sign-in or sign-up page
3. Click **Sign in with Google**
4. Complete Google consent in the same browser window
5. You should briefly see `/auth/session` (“Completing sign-in…”) then land on
   `/dashboard`

## LinkedIn OAuth Setup

1. In the [LinkedIn Developer Portal](https://www.linkedin.com/developers/),
   enable **Sign In with LinkedIn using OpenID Connect**.
2. Register the **backend** redirect URI:

```text
http://localhost:8000/api/v1/auth/linkedin/callback
https://api.247ai.live/api/v1/auth/linkedin/callback
```

3. Add credentials to root `.env`:

```text
SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID=...
SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET=...
LINKEDIN_OAUTH_SCOPES=openid profile email
```

See [LinkedIn sign-in (backend redirect)](../02_features/authentication_rbac/linkedin-direct-oidc.md).

## Other OAuth Providers

The same pattern applies to other OAuth providers supported by Supabase:

- GitHub
- Facebook
- Twitter
- Azure
- GitLab
- Bitbucket

Each provider will have its own specific setup process, but the general steps are similar:

1. Create an application in the provider's developer console
2. Obtain client credentials
3. Configure the redirect URIs to use the Supabase callback URL
4. Add the credentials to your Supabase project
5. Enable the provider

## Security Considerations

1. Always use HTTPS in production
2. Keep your OAuth credentials secure and never commit them to version control
3. Use environment variables to manage credentials
4. Regularly rotate your OAuth credentials
5. Monitor your OAuth usage for suspicious activity

## Troubleshooting

### Common Issues

1. **Redirect URI mismatch**: Ensure provider redirect URIs match the **backend**
   callback URLs (`{API_BASE_URL}/api/v1/auth/{provider}/callback`), not the frontend
2. **OAuth consent screen not approved**: For external applications, the consent screen must be approved by Google
3. **Invalid client credentials**: Double-check that the Client ID and Secret are correct
4. **Handoff errors on `/auth/session`**: Confirm `JWT_SECRET_KEY` is set and matches
   between backend restarts; restart the dev stack after env changes
5. **CORS errors**: Ensure `NEXT_PUBLIC_API_URL` points at the backend origin

### Debugging Steps

1. Check the browser console for JavaScript errors
2. Verify network requests to ensure proper redirects
3. Check Supabase authentication logs
4. Review OAuth provider logs for any error messages

## How OAuth Works with Supabase

Detailed architecture (sequence diagrams, credential tables, Google vs LinkedIn):

**[Social OAuth architecture](../02_features/authentication_rbac/social-oauth-architecture.md)**

### Google (backend redirect)

1. **Frontend** links to `GET /api/v1/auth/google/authorize`.
2. **Backend** redirects to Google; Google returns to
   `/api/v1/auth/google/callback`.
3. **Backend** mints a Supabase session, provisions a default organization, and
   redirects to `/auth/session?handoff=...`.
4. **Frontend** `/auth/session` exchanges the handoff via
   `POST /api/v1/auth/session/handoff`, calls `setSession`, and navigates to
   `/dashboard`.

See [Backend redirect OAuth](../02_features/authentication_rbac/backend-redirect-oauth.md).

### LinkedIn (backend redirect)

1. **Frontend** links to `GET /api/v1/auth/linkedin/authorize`.
2. **Backend** redirects to LinkedIn; LinkedIn returns to
   `/api/v1/auth/linkedin/callback`.
3. **Backend** exchanges the code, mints a Supabase session, provisions a
   default organization, and redirects to `/auth/session?handoff=...`.
4. **Frontend** `/auth/session` exchanges the handoff, stores the session, and
   navigates to `/dashboard`.

See [Backend redirect OAuth](../02_features/authentication_rbac/backend-redirect-oauth.md).

Neither flow navigates the main page through Supabase's OAuth callback URL.
