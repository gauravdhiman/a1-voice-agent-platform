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

### 3. Create OAuth Credentials for Google Identity Services

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application" as the application type
4. Add these **Authorized JavaScript origins**:
   - `https://www.247ai.live`
   - `http://localhost:3000` (local development)
5. Keep the Supabase callback URL in **Authorized redirect URIs** for any
   remaining redirect-based provider flows:
   - Format: `https://YOUR_SUPABASE_PROJECT_ID.supabase.co/auth/v1/callback`
   - Example: `https://ufyknvcmswkxowpvsazd.supabase.co/auth/v1/callback`
   - You can find this URL in your Supabase dashboard under Authentication → Settings
6. Save the credentials and note the Client ID and Client Secret

### 4. Configure Supabase OAuth Provider

1. Go to your Supabase project dashboard
2. Navigate to "Authentication" → "Providers"
3. Find "Google" in the list and click it
4. Toggle the provider to "Enabled"
5. Enter the Google Client ID and Client Secret from step 3
6. Save the configuration

The frontend uses the Web Client ID as `NEXT_PUBLIC_GOOGLE_CLIENT_ID`. This is
safe to expose in the browser; do not expose the Client Secret.

### Local Supabase configuration

Local Supabase Auth must also have Google enabled before it will accept the
ID token from the frontend. Add the same Web Client ID and the Client Secret
to the root `.env` file:

```bash
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET=your-google-web-client-secret
```

The committed `supabase/config.toml` references the two
`SUPABASE_AUTH_EXTERNAL_GOOGLE_*` values with `env(...)` and keeps nonce
validation enabled. Restart local Supabase after changing the values:

```bash
supabase stop
supabase start
```

### 5. Test the Integration

1. Start your application
2. Navigate to the sign-in or sign-up page
3. Click the "Sign in with Google" or "Sign up with Google" button
4. Google should open its branded sign-in popup while the main page remains on
   `www.247ai.live`
5. After authenticating, the frontend sends Google's ID token to Supabase with
   `supabase.auth.signInWithIdToken`
6. The application should continue to the dashboard or organization setup

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

1. **Redirect URI mismatch**: Ensure the redirect URIs in your OAuth provider match exactly with the Supabase callback URL
2. **OAuth consent screen not approved**: For external applications, the consent screen must be approved by Google
3. **Invalid client credentials**: Double-check that the Client ID and Secret are correct
4. **CORS errors**: Ensure your application domains are properly configured in Supabase

### Debugging Steps

1. Check the browser console for JavaScript errors
2. Verify network requests to ensure proper redirects
3. Check Supabase authentication logs
4. Review OAuth provider logs for any error messages

## How OAuth Works with Supabase

For Google on the web, the frontend uses Google's Identity Services popup and
then hands the returned ID token to Supabase:

1. **Frontend** loads Google's Identity Services client and renders the
   official branded button.
2. **Google** opens a popup and returns an ID token to the frontend callback.
3. **Frontend** calls
   `supabase.auth.signInWithIdToken({ provider: 'google', token, nonce })`.
4. **Supabase** validates the token and returns the application session.
5. **Frontend** receives the session through the auth state change listener.

This Google flow does not navigate the main page through the Supabase callback
URL. LinkedIn and other redirect-based providers continue to use
`signInWithOAuth`.
