# Local Demo Guide

Welcome! This guide walks you through experiencing the Voice AI Agents platform on your own computer. No engineering background required.

---

## 1. Prerequisites

Before you start, install the following:

### Docker Desktop
Docker runs the platform on your computer. Download and install it from:
**https://www.docker.com/products/docker-desktop/**

After installing, open Docker Desktop and make sure it shows the green "Running" status in the menu bar.

### Git
Git lets you download the project code. Check if you have it:
```bash
git --version
```
If not installed, download from **https://git-scm.com/downloads**

### A Free Supabase Account
Supabase provides the database and user authentication. Sign up for free at:
**https://supabase.com**

Once signed in, create a new project (pick any name and region). After the project is created, go to **Project Settings → API** and keep that page open — you'll need values from it in step 3.

### Clone the Repository
Open a terminal and run:
```bash
git clone <your-repo-url>
cd a1-voice-agent-platform
```

---

## 2. Quick-Start: Static Landing Page (No Server Needed)

You can preview the marketing landing page right now — no setup required.

```bash
open docs/index.html
```

This opens the CogniNets landing page in your browser. Things to explore:
- **Pricing section** — four-tier plan (Starter, Growth, Professional, Enterprise)
- **Waitlist form** — simulates the lead capture flow for prospective customers

---

## 3. Full Platform Setup

### Step 1 — Create Your Environment File

Copy the example configuration file:
```bash
cp .env.example .env
```

Now open `.env` in a text editor. Find the lines below and replace the placeholder values with your actual Supabase credentials (from **Project Settings → API** in Supabase):

```bash
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_KEY=<service role key>
SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

> **Where to find these values in Supabase:**
> - **SUPABASE_URL** and **NEXT_PUBLIC_SUPABASE_URL**: The "Project URL" field
> - **SUPABASE_ANON_KEY** and **NEXT_PUBLIC_SUPABASE_ANON_KEY**: The "anon public" key
> - **SUPABASE_SERVICE_KEY**: The "service_role" key (keep this secret!)

All other values in `.env` can remain as-is. You do **not** need Stripe, Twilio, or other third-party keys to browse the platform UI (voice calls need `GEMINI_API_KEY` and voice-ws).

### Step 2 — Start the Platform

```bash
./start.sh start dev
```

The first run downloads and builds all the pieces of the platform — this takes about 5 minutes. Subsequent starts are much faster.

When you see "Development containers started successfully!" the platform is ready.

### Step 3 — Open in Browser

Navigate to: **http://localhost:3000**

---

## 4. Demo Walkthrough (Guided Path)

Follow these steps for a complete tour of the platform:

**1. Landing Page**
Open `docs/index.html` in your browser. Review the pricing tiers and try the waitlist form.

**2. Sign Up**
Go to **http://localhost:3000** and create an account using any email address.

**3. Onboarding Wizard**
You'll be guided through a 5-step SMB onboarding wizard at `/onboarding`. This simulates the setup flow a new customer (e.g., a plumber or HVAC company) would experience.

**4. Dashboard**
After onboarding, explore the main dashboard at `/dashboard`. This is the customer's home base — activity overview, quick stats, and navigation.

**5. Agents List**
Navigate to `/agents` to see the list of configured AI voice agents.

**6. Create a Voice Agent**
Go to `/agents/create` to explore how an SMB would configure a new AI agent — voice settings, personality, knowledge base, and call handling rules.

**7. Organization Settings**
Visit `/organization` to see multi-tenant settings — team members, billing info, and account configuration.

---

## 5. Known Limitations in Local Mode

The following features require third-party account credentials that are not needed for the UI walkthrough:

| Feature | Status | What You'll See |
|---|---|---|
| **Voice Calls (Pipecat)** | Partial | UI visible; calls need `GEMINI_API_KEY` + voice-ws running |
| **Phone Numbers (Twilio)** | Not functional | Purchase UI is disabled without a Twilio account upgrade |
| **Billing (Stripe)** | Not functional | Payment flows are visible but won't process |
| **Email Notifications (Resend)** | Not functional | Emails won't send without a Resend API key |
| **Observability (New Relic)** | Not functional | Telemetry collection disabled without a New Relic license key |

All of these are normal in a local demo environment. The UI and navigation work fully.

---

## 6. Stopping the Platform

When you're done, stop all containers with:
```bash
./start.sh stop dev
```

---

## 7. Troubleshooting

**Port 3000 or 8000 is already in use**
Another application is using that port. Find and stop it, or restart your computer, then try again.

**Check what's running**
```bash
./start.sh status
```

**View logs for errors**
```bash
./start.sh logs dev
```
Press `Ctrl+C` to stop watching the logs.

**"Error: .env file not found"**
You skipped Step 1. Run `cp .env.example .env` and fill in your Supabase credentials.

**"Missing required environment variables"**
Your `.env` file is missing Supabase values. Re-check Step 1 and make sure `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are all set.

**Docker Desktop not running**
Make sure Docker Desktop is open and shows a green "Running" status before running `./start.sh start dev`.
