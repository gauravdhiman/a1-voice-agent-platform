/**
 * Data for the "Small Business AI Toolbox" directory at /ai-tools.
 *
 * Curated AI tools for small businesses, organized by category. Pricing was
 * researched in October 2026 and is summarized as "from" figures — vendors
 * change pricing often, so every tool page links to the official pricing page.
 * No vendor paid for placement.
 */

export interface ToolFaq {
  q: string;
  a: string;
}

export interface QuickFacts {
  /** e.g. "From $49/mo (250 min); most service businesses need $149/mo" */
  price: string;
  /** Free trial / free plan details, plain English. */
  freeTier: string;
  /** Setup difficulty in plain English. */
  setup: string;
}

export interface BusinessScenario {
  title: string;
  description: string;
}

export interface ComparisonRow {
  tool: string;
  price: string;
  difference: string;
}

export interface GoingDeeper {
  /** Direct/native integrations, plain English. */
  integrations: string[];
  /** API availability, plain English. Omit when none is published. */
  api?: string;
  /** Data privacy and security facts, plain English, verified only. */
  privacy: string[];
  /** One advanced workflow idea, concrete and buildable. */
  advancedWorkflowTitle: string;
  advancedWorkflow: string;
}

export interface Tool {
  name: string;
  slug: string;
  tagline: string;
  /** Category slug this tool belongs to. */
  category: string;
  /** Short pricing summary, e.g. "From $49/mo". */
  pricing: string;
  pros: string[];
  cons: string[];
  bestFor: string;
  /** Official vendor homepage. No affiliate links. */
  url: string;
  /** 1-2 sentence honest verdict. */
  verdict: string;
  faqs: ToolFaq[];
  /** Featured tools render first with an "Our pick" badge. */
  featured?: boolean;
  // ---- Deep template fields (all optional; pages without them render the classic layout) ----
  /** 2-3 sentence verdict box. Falls back to `verdict`. */
  verdictBox?: string;
  /** Quick-facts grid (price / free tier / setup). Rendered with `bestFor` as the 4th card. */
  quickFacts?: QuickFacts;
  /** "What is it" in plain English, one paragraph per entry. */
  whatIsIt?: string[];
  /** Concrete "what it will do for your business" scenarios. */
  businessScenarios?: BusinessScenario[];
  /** Numbered "how it works" steps. */
  howItWorks?: string[];
  /** Pricing explained in plain English, catches included. */
  pricingExplained?: string[];
  /** Specific catches/limits called out as a list. */
  pricingCatches?: string[];
  /** Who should get it. */
  whoShouldGet?: string[];
  /** Who should skip it. */
  whoShouldSkip?: string[];
  /** Mini comparison table vs alternatives. */
  comparison?: ComparisonRow[];
  /** "Going deeper" section for tech-curious readers. Rendered only when present. */
  goingDeeper?: GoingDeeper;
}

export interface ToolCategory {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  /** Intro paragraphs shown at the top of the category page. */
  intro: string[];
  faqs: ToolFaq[];
}

export const TOOL_CATEGORIES: ToolCategory[] = [
  {
    slug: "ai-receptionists",
    name: "AI Receptionists",
    tagline: "AI that answers your business phone",
    description:
      "AI receptionists that answer every call, take messages, and book appointments for small businesses — compared on price, minutes, and human backup.",
    intro: [
      "A missed call is the most expensive thing that happens in a small business week. AI receptionists fix that for $29 to $165 a month — a fraction of a human answering service, available 24/7.",
      "Below are the services we would shortlist for a local business in 2026, including our own. We built 24x7 AI, so we are biased — but every competitor here is listed honestly, because a comparison you cannot trust is worthless.",
    ],
    faqs: [
      {
        q: "How much does an AI receptionist cost?",
        a: "Most small businesses pay $29 to $165 a month in 2026. Simple AI-only services start around $29; hybrid AI-plus-human services run $150 and up.",
      },
      {
        q: "Will callers know it is AI?",
        a: "Modern AI receptionists sound natural enough that most callers do not notice. Every serious provider lets you listen to real call recordings before you commit, so test it yourself.",
      },
      {
        q: "Can an AI receptionist book appointments?",
        a: "Yes — the good ones book straight into your calendar, take messages, and answer FAQs. Check whether booking is included in the base plan or sold as an add-on.",
      },
    ],
  },
  {
    slug: "ai-chatbots",
    name: "AI Chatbots",
    tagline: "AI chat for your website",
    description:
      "AI chatbots that answer website visitors, capture leads, and deflect support tickets — compared for small business budgets and setup effort.",
    intro: [
      "A website chatbot turns passive browsers into conversations: it answers the ten questions everyone asks, captures lead details, and hands the tricky stuff to a human.",
      "Pricing models differ wildly — flat monthly, per conversation, per resolution — so compare on your actual chat volume, not the headline number.",
    ],
    faqs: [
      {
        q: "How much does an AI chatbot cost?",
        a: "From $15 a month for simple bots to $0.99 per AI resolution plus platform seats for premium options. Most small businesses land between $29 and $80 a month.",
      },
      {
        q: "Will a chatbot replace my support team?",
        a: "No — it deflects the repetitive 50 to 70 percent so your team handles the rest. Plan for human handoff from day one.",
      },
      {
        q: "How long does setup take?",
        a: "Content-trained bots like Chatbase go live in minutes. Deeper platforms like Intercom take days to train well on your knowledge base.",
      },
    ],
  },
  {
    slug: "ai-scheduling",
    name: "AI Scheduling",
    tagline: "AI that manages your calendar",
    description:
      "AI scheduling tools for bookings, focus time, and calendar defense — from simple booking links to AI that plans your whole day.",
    intro: [
      "Two different jobs live under 'scheduling'. Booking tools let the outside world pick a time with you. AI schedulers plan your own day — tasks, focus time, and meetings arranged by priority.",
      "Figure out which problem hurts more, then pick from the matching half of this list. Many owners end up with one of each.",
    ],
    faqs: [
      {
        q: "What is the difference between booking and AI scheduling?",
        a: "Booking tools (Calendly, Cal.com) let others pick a time. AI schedulers (Motion, Reclaim) plan your own day — tasks, focus time, and meetings together.",
      },
      {
        q: "Which is best for client bookings?",
        a: "Calendly remains the standard for external booking, Cal.com is the value pick, and SavvyCal wins on polish.",
      },
      {
        q: "Do I need both a booking tool and an AI scheduler?",
        a: "Many owners do: Calendly or Cal.com for the outside world, Reclaim or Motion to defend the inside of the calendar.",
      },
    ],
  },
  {
    slug: "ai-review-management",
    name: "AI Review Management",
    tagline: "More 5-star reviews on autopilot",
    description:
      "Review management software that automatically requests reviews, drafts responses, and protects your Google rating.",
    intro: [
      "Eighty-nine percent of consumers expect businesses to respond to reviews, and almost none do. Review software automates the asking — every customer gets a text or email after their visit — and AI drafts the responses.",
      "Pricing splits into two camps: published tiers for SMB tools, and quote-based annual contracts for the enterprise suites. Do not pay enterprise prices for a single location.",
    ],
    faqs: [
      {
        q: "How much does review software cost?",
        a: "NiceJob starts at $75 a month with no contract. Birdeye and Podium run $300 to $500+ a month per location on annual contracts.",
      },
      {
        q: "Can I just ask for reviews manually?",
        a: "You can — until you are busy. The whole value is automatic requests after every job, so reviews keep coming on your busiest days.",
      },
      {
        q: "Do I need review software with one location?",
        a: "If you serve more customers daily than you can personally ask, yes. A few customers a week? A direct review link in a text works fine.",
      },
    ],
  },
  {
    slug: "ai-marketing",
    name: "AI Marketing Tools",
    tagline: "AI for content, email, and campaigns",
    description:
      "AI marketing tools for content creation, email, and CRM — what actually saves time for a small business in 2026.",
    intro: [
      "The honest 2026 playbook: a general AI assistant handles research and first drafts, a dedicated platform handles high-volume templated formats, and a human editor touches anything public.",
      "Start with one tool, use it for 30 days, measure whether it saved time — then add the next one. The stack below is ordered by where most small businesses should start.",
    ],
    faqs: [
      {
        q: "What is the cheapest way to start with AI marketing?",
        a: "A $20-a-month chat assistant plus Mailchimp's free tier covers most solo businesses. Add Jasper or HubSpot when volume justifies it.",
      },
      {
        q: "Will AI content hurt my brand?",
        a: "Unedited AI content, yes. The 2026 playbook is AI drafts, human decides — keep an editor on anything that carries your reputation.",
      },
      {
        q: "HubSpot vs Mailchimp vs Constant Contact?",
        a: "HubSpot when you want CRM plus marketing together, Mailchimp as the safe all-rounder, Constant Contact for the simplest possible start.",
      },
    ],
  },
];

export const TOOLS: Tool[] = [
  // ------------------------------------------------------------------
  // AI receptionists
  // ------------------------------------------------------------------
  {
    name: "24x7 AI",
    slug: "24x7-ai",
    tagline:
      "The AI front desk for small business: answers every call, books appointments, live in 48 hours.",
    category: "ai-receptionists",
    pricing: "Free plan; paid plans from $49/mo",
    pros: [
      "Answers on your existing business number plus a website voice widget",
      "Books appointments into your calendar and captures leads 24/7",
      "Concierge setup done for you — live in 48 hours",
      "Free plan to try before you pay; no setup fee",
    ],
    cons: [
      "Built for SMBs — not the pick for enterprises needing custom on-premise deployments",
      "Newer brand than the legacy answering services",
    ],
    bestFor:
      "Local service businesses (HVAC, dental, plumbing, salons) losing jobs to missed after-hours calls",
    url: "https://www.247ai.live",
    verdict:
      "Disclosure: we build 24x7 AI, so take this with a grain of salt. The pitch is simple — most AI receptionists charge per minute and leave setup to you. We do concierge setup in 48 hours and start at $49 a month. If your problem is missed calls costing you jobs, this is the fastest fix we know.",
    faqs: [
      {
        q: "How fast can 24x7 AI go live?",
        a: "Concierge setup gets most businesses live in 48 hours — the team configures your greeting, calendar, and FAQs for you.",
      },
      {
        q: "Does it work with my existing business number?",
        a: "Yes. Calls to your current number are answered by the AI, and you can also add the voice widget to your website.",
      },
      {
        q: "Is there a free plan?",
        a: "Yes — 100 credits (about 10 minutes) free with no card required. Paid plans start at $49 a month.",
      },
    ],
    featured: true,
  },
  {
    name: "Rosie",
    slug: "rosie",
    tagline: "Simple AI phone answering built for home-service businesses.",
    category: "ai-receptionists",
    pricing: "From $49/mo (250 minutes included)",
    pros: [
      "Cheapest credible entry point: $49 a month is less than one decent job for most trades",
      "Setup genuinely takes under 30 minutes: Rosie reads your website and Google profile herself",
      "Bilingual English/Spanish on every call, included, not an add-on",
      "Handles unlimited simultaneous calls, so there is no busy signal during your busiest hour",
      "No contracts, cancel anytime, 7-day free trial with all features",
    ],
    cons: [
      "The $49 plan is basic on purpose: no direct calendar booking, no live transfers, which means most service businesses need the $149 plan",
      "Minutes are metered and round up to 60 seconds; heavy months push you into higher tiers",
      "No published overage rate, so you have to ask what over-limit minutes cost",
      "No native CRM integrations and only two languages; inbound calls only, no outbound",
      "Young company with no G2, Capterra, or Trustpilot track record yet",
    ],
    bestFor: "Solo owners and small shops replacing voicemail with real 24/7 coverage",
    url: "https://heyrosie.com",
    verdict:
      "Rosie is the value pick for simple coverage: $49 gets you 250 minutes and a setup a contractor can finish between jobs. If you need deep calendar booking or complex call flows, look upmarket.",
    verdictBox:
      "Rosie is the cheapest way to make sure a real-sounding voice answers your business phone around the clock: $49 a month gets you 250 minutes, setup takes under 30 minutes, and there is no contract. The catch is that the $49 plan is deliberately basic: no direct calendar booking or live call transfers, so most service businesses will realistically land on the $149 plan. If your needs are simple and your call volume is light, it is genuinely hard to beat on price.",
    quickFacts: {
      price: "From $49/mo (250 min); most service businesses need $149/mo",
      freeTier: "7-day free trial with all features; no free plan",
      setup: "Under 30 minutes, no tech skills needed",
    },
    whatIsIt: [
      "Rosie is an AI answering service for your business phone. When you cannot pick up because you are on a job, it is after hours, or you are already on another call, Rosie answers instead.",
      "She talks with your customer in a natural voice, in English or Spanish, figures out what they need, takes a detailed message or books them in, and then texts or emails you a summary. Your customers call the same number they have always called; from their side, nothing changes except someone always picks up.",
    ],
    businessScenarios: [
      {
        title: "Never lose the after-hours caller",
        description:
          "It is 8pm, you are at dinner, and a homeowner's AC just died. They call you, Rosie answers, learns it is an emergency, and texts you the details instantly. Without Rosie, that caller leaves no voicemail and calls your competitor.",
      },
      {
        title: "Book jobs while you are on a job",
        description:
          "You are under a sink and cannot answer. Rosie takes the call and, on the Scale plan and up, puts the appointment straight on your calendar. You finish the job, check your phone, and there is a new booking waiting.",
      },
      {
        title: "Stop the spam from reaching you",
        description:
          "Robocalls and telemarketers get filtered out automatically before they ever bother you. You only hear about real customers.",
      },
      {
        title: "Sound bigger than you are",
        description:
          "Every call answered professionally, 24/7, even when it is just you. Customers cannot tell whether you have a front office or a phone in your truck.",
      },
      {
        title: "Know what happened without listening to voicemails",
        description:
          "After every call you get a text or email with a summary, a transcript, and a recording. Scan it in ten seconds between jobs instead of playing phone tag with your voicemail.",
      },
    ],
    howItWorks: [
      "Rosie gives you a phone number, and you forward your business calls to it. You keep your existing number, so customers notice nothing. You choose when Rosie picks up: all calls, only when you are busy, or only after hours, and you can change this anytime.",
      "You teach Rosie about your business. She reads your website and Google Business Profile herself, then you answer a few questions about your services, hours, and pricing. Most owners finish in under 30 minutes, and there is a free setup call if you want help.",
      "Connect your calendar (Scale plan and up). Link Google Calendar or Outlook once, and Rosie can book appointments directly into your real availability.",
      "Rosie answers, and you get a text after every call. She handles the conversation, takes messages using the specific questions you chose, transfers urgent calls to you live (Scale plan and up), and sends you a summary by text or email the moment the call ends.",
    ],
    pricingExplained: [
      "Rosie sells minutes, not seats: it does not matter whether it is just you or five techs; what matters is how long callers talk to the AI. Three plans: Professional at $49 a month for 250 minutes, Scale at $149 for 1,000 minutes, Growth at $299 for 2,000 minutes. Pay yearly and you save about two months. Every plan includes a 7-day free trial with all features, and there are no contracts.",
      "A typical service call runs 2 to 4 minutes, so 250 minutes covers roughly 60 to 120 calls a month: plenty for a solo operator, tight for a busy shop.",
    ],
    pricingCatches: [
      "The $49 plan does not include direct calendar booking or live call transfers. Instead, it sends the customer a booking link by text. If you want Rosie to put jobs directly on your calendar or patch urgent calls through live, that is the $149 plan.",
      "Minutes round up to the full minute, so a 20-second call still costs you a minute.",
      "Rosie does not publish what happens when you go over your minutes. Ask that question during your trial week, not after your first busy month.",
      "The only paid add-on is Website Texting at $50 a month; the website chat widget is free.",
    ],
    whoShouldGet: [
      "Solo owners and contractors who currently send everything to voicemail",
      "Shops losing after-hours and weekend calls to competitors",
      "Anyone who wants the cheapest real 24/7 coverage and is comfortable with simple, predictable call flows",
    ],
    whoShouldSkip: [
      "Businesses that need direct calendar booking on day one but will not pay $149 a month",
      "Teams that need deep CRM integration, more than two languages, or outbound calling",
      "Anyone who wants a human backup for tricky calls (Rosie is AI-only)",
    ],
    comparison: [
      {
        tool: "Rosie",
        price: "$49/mo (250 min)",
        difference: "Cheapest entry; metered minutes; booking and live transfers need the $149 tier",
      },
      {
        tool: "Goodcall",
        price: "$79/mo per agent",
        difference: "Unlimited minutes per agent, which is better if your phone never stops ringing; priced per agent though",
      },
      {
        tool: "Smith.ai",
        price: "From $150/mo",
        difference: "AI plus real human receptionists as backup. Costs more, but handles the tricky calls",
      },
      {
        tool: "24x7 AI (our product)",
        price: "From $49/mo",
        difference: "Our own AI front desk with concierge setup; compare it honestly in our full review",
      },
    ],
    goingDeeper: {
      integrations: [
        "Direct connections, no extra tools needed: Google Calendar and Outlook for appointment booking, instant email and text notifications after every call, native iPhone and Android apps, and Google Voice.",
        "Everything else runs through Zapier. Rosie has an official Zapier app with New Call and New Booking triggers, which connects it to 1,000+ apps: log calls to Google Sheets, create customers in Jobber or Housecall Pro, ping a Slack channel, add leads to HubSpot. There are no native CRM integrations inside Rosie itself; Zapier is the bridge.",
      ],
      api: "Rosie does not publish a public developer API. If you are technical, the practical route is Zapier's webhooks, which can push Rosie call data into your own systems.",
      privacy: [
        "Every call is recorded and transcribed, and recordings live in your Rosie calls inbox. The recordings and transcripts belong to you, not Rosie: you decide how they are used and how long they are kept.",
        "From Rosie's own privacy notice: deidentified call data may be used to train and improve their AI. Rosie never collects or stores payment information; payments go through a PCI-compliant processor.",
        "The legal part is on you. You are responsible for telling callers they are being recorded and for complying with your state's recording-consent laws. Rosie provides template recording notices you can switch on in settings; you decide whether to use them.",
      ],
      advancedWorkflowTitle: "Hands-free call log with emergency alerts",
      advancedWorkflow:
        "Connect Rosie's New Call trigger in Zapier to Google Sheets: every call lands as a row with the caller, time, and summary, no data entry, giving you a searchable history of every conversation. Add a second step that posts to a Slack channel only when the summary mentions words like emergency or urgent. You get instant alerts for the calls that matter and a full log of the rest, without listening to a single recording.",
    },
    faqs: [
      {
        q: "How many minutes do I actually get for $49?",
        a: "250 minutes a month. A typical service call runs 2 to 4 minutes, so that is roughly 60 to 120 calls: plenty for a solo operator, tight for a busy shop. And remember: minutes round up to the full minute.",
      },
      {
        q: "Can Rosie book appointments directly on my calendar?",
        a: "Only on the Scale plan ($149 a month) and up. The $49 Professional plan sends the customer a booking link by text instead, so they book themselves. If direct booking matters to you, start your trial on Scale.",
      },
      {
        q: "Do I have to change my business phone number?",
        a: "No. Rosie gives you a new number and you forward your existing business line to it. Your customers call the same number they always have, and you control when Rosie answers: all calls, only when you are busy, or only after hours.",
      },
      {
        q: "What happens when Rosie cannot answer a question?",
        a: "She says so honestly instead of guessing, takes a detailed message using the questions you chose, and texts or emails you immediately so you can follow up.",
      },
      {
        q: "Does Rosie work in Spanish?",
        a: "Yes. Every call can be handled in English or Spanish, on all plans, at no extra charge.",
      },
      {
        q: "What happens if I go over my minutes?",
        a: "Rosie does not publish an overage rate, which is the one thing to pin down during your 7-day trial. Ask support directly what a minute costs past your allowance before your first busy month.",
      },
      {
        q: "Is there a contract or a setup fee?",
        a: "No contract, no setup fee, cancel anytime. There is a 7-day free trial with all features, and they offer a free setup consultation when you sign up.",
      },
    ],
  },
  {
    name: "Goodcall",
    slug: "goodcall",
    tagline: "Customizable AI agents with unlimited minutes per agent.",
    category: "ai-receptionists",
    pricing: "From $79/mo per agent (100 unique callers, unlimited minutes)",
    pros: [
      "Unlimited minutes — pricing is per agent, not per minute",
      "Deep workflow customization for repeat callers",
      "Good fit for high-call-volume local shops",
    ],
    cons: [
      "Priced per agent, so multi-location costs add up",
      "Setup takes more thought than plug-and-play options",
    ],
    bestFor: "High-call-volume shops that hate per-minute metering",
    url: "https://goodcall.com",
    verdict:
      "Goodcall's per-agent pricing is the antidote to per-minute anxiety: talk all month, pay $79. The trade is a more involved setup and per-agent math that penalizes multi-location businesses.",
    faqs: [
      {
        q: "What does 100 unique callers mean?",
        a: "Each plan covers 100 distinct caller numbers per agent per month; minutes are unlimited within that.",
      },
      {
        q: "Can I customize what the agent says?",
        a: "Yes — Goodcall is built around customizable call flows and workflows.",
      },
      {
        q: "Is there a free trial?",
        a: "Goodcall periodically offers first-time-customer discounts; check their site for current offers.",
      },
    ],
  },
  {
    name: "Smith.ai",
    slug: "smith-ai",
    tagline: "AI answering backed by real human receptionists.",
    category: "ai-receptionists",
    pricing: "Free 25 calls/mo; Pro from $150/mo (75 AI calls)",
    pros: [
      "Human agents behind the AI for tricky calls",
      "Strong lead qualification and intake, especially for law firms",
      "Free tier lets you test with real calls",
    ],
    cons: [
      "Pricier than pure-AI options once you scale",
      "Human-agent plans can reach $300+ a month",
    ],
    bestFor:
      "Law firms and consultation businesses where every intake call matters",
    url: "https://smith.ai",
    verdict:
      "Smith.ai is the hybrid done right: AI handles the routine, trained humans catch the rest. You pay for that safety net — $150 and up — but for intake-driven businesses it pays for itself with one saved client.",
    faqs: [
      {
        q: "What do I get free?",
        a: "25 AI-answered calls per month on the free tier.",
      },
      {
        q: "When does a human step in?",
        a: "AI answers first; trained receptionists take over for complex calls or when you configure human-first answering.",
      },
      {
        q: "Is Smith.ai good for law firms?",
        a: "It is one of the strongest picks — intake and lead qualification are its home turf.",
      },
    ],
  },
  {
    name: "Abby Connect",
    slug: "abby-connect",
    tagline: "Blended AI and human answering with on-demand takeover.",
    category: "ai-receptionists",
    pricing: "From $165/mo (50 live minutes or 100 AI minutes)",
    pros: [
      "On-demand human takeover when AI hits its limit",
      "Custom call flows and bilingual answering",
      "Good bridge for teams nervous about going full-AI",
    ],
    cons: [
      "One of the pricier options in the category",
      "Minute bundles get expensive at volume",
    ],
    bestFor: "Teams easing from a human answering service into AI",
    url: "https://abbyconnect.com",
    verdict:
      "Abby Connect is the comfort blanket: AI most of the time, a human one button away. At $165 and up it is premium-priced, but for businesses transitioning off a legacy answering service it removes the fear factor.",
    faqs: [
      {
        q: "What is an Abby Minute?",
        a: "Their billing unit: the $165 plan includes 50 live-agent minutes or 100 AI minutes.",
      },
      {
        q: "Can a human take over mid-call?",
        a: "Yes — on-demand human takeover is the headline feature.",
      },
      {
        q: "Is there a free tier?",
        a: "Entry paid plans start at $165 a month; trial allocations vary by current offer.",
      },
    ],
  },
  {
    name: "Dialzara",
    slug: "dialzara",
    tagline: "Budget AI phone answering from $29 a month.",
    category: "ai-receptionists",
    pricing: "From $29/mo (60 minutes included)",
    pros: [
      "Lowest entry price among serious options",
      "Fast setup with a wide integration catalog",
      "50+ voice options",
    ],
    cons: [
      "No human backup — transfers to your team only",
      "60 minutes goes fast for busy businesses",
    ],
    bestFor: "Budget-first businesses with light call volume",
    url: "https://dialzara.com",
    verdict:
      "Dialzara wins the price war at $29 a month. It is AI-only with no human safety net, and 60 minutes is a starter allowance — but for a solo operator watching every dollar, it is a legitimate way to stop missing calls.",
    faqs: [
      {
        q: "How many minutes do I get for $29?",
        a: "60 minutes per month on the entry plan; overage is metered.",
      },
      {
        q: "Does Dialzara have human backup?",
        a: "No — it is AI-only, with call transfers to your team.",
      },
      {
        q: "How fast is setup?",
        a: "Most accounts are answering calls within hours; the AI learns from your website.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI chatbots
  // ------------------------------------------------------------------
  {
    name: "Tidio",
    slug: "tidio",
    tagline: "Live chat plus the Lyro AI bot for small stores.",
    category: "ai-chatbots",
    pricing: "From $29/mo (Lyro AI billed per conversation)",
    pros: [
      "Live chat and AI in one widget",
      "Trains on your website content in minutes",
      "Free plan with 50 conversations to start",
    ],
    cons: [
      "AI conversations are metered on top of the base plan",
      "Advanced automation needs higher tiers",
    ],
    bestFor: "Ecommerce stores and small sites that want chat plus AI together",
    url: "https://www.tidio.com",
    verdict:
      "Tidio is the SMB default for a reason: one widget covers live chat and AI, and the free plan is enough to prove value. Watch the Lyro per-conversation metering once volume grows.",
    faqs: [
      {
        q: "What is Lyro?",
        a: "Tidio's AI agent, billed per AI-handled conversation on top of the base plan.",
      },
      {
        q: "Is there a free plan?",
        a: "Yes — 50 conversations per month free.",
      },
      {
        q: "Does Tidio work with Shopify?",
        a: "Yes — it is one of the most popular chat widgets for Shopify stores.",
      },
    ],
  },
  {
    name: "Chatbase",
    slug: "chatbase",
    tagline: "Train a chatbot on your content in minutes.",
    category: "ai-chatbots",
    pricing: "From $40/mo",
    pros: [
      "Easiest setup in the category — paste a URL, get a bot",
      "Embeds on any website with no code",
      "Message credits scale with usage",
    ],
    cons: [
      "Support-bot focused, not a full helpdesk",
      "Heavy usage burns credits fast",
    ],
    bestFor: "Businesses that want a Q&A bot on their site this afternoon",
    url: "https://www.chatbase.co",
    verdict:
      "Chatbase is the fastest path from 'we should have a chatbot' to a working one: paste your URL, embed the widget, done. It is a Q&A bot, not a helpdesk — buy it for that job and it delivers.",
    faqs: [
      {
        q: "How long does setup take?",
        a: "Paste your website URL and you have a working bot in minutes.",
      },
      {
        q: "What does $40 a month include?",
        a: "A message-credit bundle; heavier usage needs bigger plans or top-ups.",
      },
      {
        q: "Can it do more than answer questions?",
        a: "Yes — actions, integrations, and lead capture are built in.",
      },
    ],
  },
  {
    name: "Intercom Fin",
    slug: "intercom-fin",
    tagline: "The most capable AI support agent, billed per resolution.",
    category: "ai-chatbots",
    pricing: "$0.99 per resolution + Intercom seats from $29/mo",
    pros: [
      "Highest autonomous resolution rates in the industry (50-70%)",
      "Deep knowledge-base training and 45+ languages",
      "Seamless handoff to human agents with full context",
    ],
    cons: [
      "Requires an Intercom subscription underneath",
      "Per-resolution billing adds up at high volume",
    ],
    bestFor: "Support teams where ticket deflection directly saves headcount",
    url: "https://www.intercom.com",
    verdict:
      "Fin is the best AI support agent money can buy — 50 to 70 percent of tickets resolved without a human is a real number. It is also the priciest path here: you need Intercom seats plus $0.99 per resolution. Worth it when deflection replaces headcount.",
    faqs: [
      {
        q: "What counts as a resolution?",
        a: "A conversation Fin handles end-to-end without human help — billed at $0.99 each.",
      },
      {
        q: "Do I need Intercom to use Fin?",
        a: "Yes — Fin runs on Intercom seats, which start at $29 a month.",
      },
      {
        q: "How accurate is it?",
        a: "Intercom reports 50 to 70 percent autonomous resolution when trained on a solid knowledge base.",
      },
    ],
  },
  {
    name: "Drift",
    slug: "drift",
    tagline: "Conversational marketing and meeting booking for B2B.",
    category: "ai-chatbots",
    pricing: "Enterprise pricing (contact sales)",
    pros: [
      "Purpose-built for pipeline and meeting booking",
      "Strong account-based playbooks",
      "Now part of Salesloft's sales platform",
    ],
    cons: [
      "Enterprise pricing — overkill for most SMBs",
      "No transparent self-serve plans",
    ],
    bestFor: "B2B teams that live on demo bookings",
    url: "https://www.drift.com",
    verdict:
      "Drift practically invented the B2B chatbot playbook, and inside Salesloft it is a serious pipeline machine. For a small business it is almost always overkill — this entry is here so you can rule it out confidently.",
    faqs: [
      {
        q: "How much does Drift cost?",
        a: "Drift does not publish pricing — it is quote-based enterprise sales.",
      },
      {
        q: "Is Drift still independent?",
        a: "Drift is now part of Salesloft's sales engagement platform.",
      },
      {
        q: "Is Drift overkill for a small business?",
        a: "Usually yes — it is built for B2B pipeline teams, not solo shops.",
      },
    ],
  },
  {
    name: "ManyChat",
    slug: "manychat",
    tagline: "Automated DM conversations for Instagram and Messenger.",
    category: "ai-chatbots",
    pricing: "From $15/mo",
    pros: [
      "Owns the Instagram and Facebook DM automation lane",
      "Visual flow builder, no code",
      "Free plan to start",
    ],
    cons: [
      "Social-channel only — not a website chatbot",
      "Pricing scales with contacts",
    ],
    bestFor: "Businesses that get customers through Instagram DMs",
    url: "https://manychat.com",
    verdict:
      "If your customers find you on Instagram, ManyChat is the highest-ROI chatbot here: $15 turns DMs into booked appointments on autopilot. It does nothing for your website — pair it with a web bot if you need both.",
    faqs: [
      {
        q: "Which channels does ManyChat support?",
        a: "Instagram DMs, Facebook Messenger, WhatsApp, and SMS.",
      },
      {
        q: "Is there a free plan?",
        a: "Yes — free to start, Pro from $15 a month scaled by contacts.",
      },
      {
        q: "Do I need to code?",
        a: "No — the visual flow builder is fully no-code.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI scheduling
  // ------------------------------------------------------------------
  {
    name: "Calendly",
    slug: "calendly",
    tagline: "The standard booking link for client scheduling.",
    category: "ai-scheduling",
    pricing: "Free; Standard from $10/seat/mo",
    pros: [
      "Everyone recognizes and trusts a Calendly link",
      "Mature routing, round-robin, and CRM integrations",
      "Free tier covers basic booking",
    ],
    cons: [
      "Free tier limited to one event type",
      "AI features are incremental, not transformative",
    ],
    bestFor: "Client-facing booking where reliability matters most",
    url: "https://calendly.com",
    verdict:
      "Calendly is the default for a reason: recipients trust the link, the integrations are mature, and the free tier handles basic booking. It will not plan your day — that is a different tool's job.",
    faqs: [
      {
        q: "Is Calendly free?",
        a: "Yes — one event type and one calendar on the free plan.",
      },
      {
        q: "What does $10 a month add?",
        a: "Standard adds unlimited event types, group events, and more integrations.",
      },
      {
        q: "Does Calendly have AI features?",
        a: "Yes — newer Plus tiers add AI meeting prep, notetaking, and follow-ups.",
      },
    ],
  },
  {
    name: "Cal.com",
    slug: "cal-com",
    tagline: "Open-source scheduling you can self-host.",
    category: "ai-scheduling",
    pricing: "Free for individuals; Teams from $12/user/mo",
    pros: [
      "Generous free tier with unlimited event types",
      "Open source — self-host for full control",
      "No per-booking fees",
    ],
    cons: [
      "Team features are cloud-only",
      "Less polished than Calendly out of the box",
    ],
    bestFor: "Businesses that want booking without subscription lock-in",
    url: "https://cal.com",
    verdict:
      "Cal.com is the value rebellion: unlimited event types free, open source, self-hostable. It is slightly less polished than Calendly, but at these prices most small businesses will not care.",
    faqs: [
      {
        q: "Is Cal.com really free?",
        a: "Yes for individuals — unlimited event types and bookings. Teams start at $12 a user a month.",
      },
      {
        q: "Can I self-host it?",
        a: "Yes — the core is open source under AGPLv3.",
      },
      {
        q: "How does it compare to Calendly?",
        a: "Less polished, more control, and much cheaper. The trade is yours to make.",
      },
    ],
  },
  {
    name: "Motion",
    slug: "motion",
    tagline: "AI that plans your entire day around priorities.",
    category: "ai-scheduling",
    pricing: "From $19/seat/mo (annual)",
    pros: [
      "Auto-schedules tasks, meetings, and deadlines together",
      "Genuinely intelligent calendar defense",
      "Project management built in",
    ],
    cons: [
      "No free tier — 7-day trial only, card required",
      "AI credit metering can surprise you",
      "3 to 4 week learning curve, per user reports",
    ],
    bestFor: "Chaotic days where tasks and meetings fight for the same hours",
    url: "https://www.usemotion.com",
    verdict:
      "Motion is the only tool here that plans your day instead of just booking it — tasks, deadlines, and meetings rearranged by priority. The $19 price and credit metering demand commitment; dabblers should start with Reclaim's free tier.",
    faqs: [
      {
        q: "Why is Motion $19 a month?",
        a: "It auto-schedules your tasks and meetings by priority — it is a planner, not just a booking link.",
      },
      {
        q: "Is there a free plan?",
        a: "No — 7-day trial only, and it requires a card.",
      },
      {
        q: "What is the catch with AI credits?",
        a: "Each seat gets a monthly AI credit allowance; heavy AI use can trigger overage charges.",
      },
    ],
  },
  {
    name: "Reclaim.ai",
    slug: "reclaim-ai",
    tagline: "Defends your focus time from meeting creep.",
    category: "ai-scheduling",
    pricing: "Free Lite; Starter from $10/seat/mo",
    pros: [
      "Best-in-class focus-time protection",
      "Owned by Dropbox since 2024 — stable parent",
      "Free tier is genuinely useful",
    ],
    cons: [
      "Free tier limited to one calendar and a short scheduling range",
      "Less of a booking-link tool than Calendly",
    ],
    bestFor: "Protecting deep work when meetings keep winning",
    url: "https://reclaim.ai",
    verdict:
      "Reclaim does one thing better than anyone: keeping meetings from eating your focus time. Dropbox's ownership makes it the safest bet in the category, and the free tier is enough for most solo owners.",
    faqs: [
      {
        q: "Is Reclaim.ai free?",
        a: "Yes — a Lite tier is free forever; paid plans start at $10 a seat a month.",
      },
      {
        q: "Who owns Reclaim?",
        a: "Dropbox acquired Reclaim in 2024, making it the most stable bet in the category.",
      },
      {
        q: "Does it replace Calendly?",
        a: "Not quite — Reclaim defends your calendar; Calendly-style booking links are secondary.",
      },
    ],
  },
  {
    name: "SavvyCal",
    slug: "savvycal",
    tagline: "Booking links designed for the recipient's experience.",
    category: "ai-scheduling",
    pricing: "From $10/user/mo",
    pros: [
      "Best-in-class scheduling page UX",
      "Overlay views that respect the guest's calendar",
      "Simple flat pricing",
    ],
    cons: ["No free tier", "Fewer enterprise integrations than Calendly"],
    bestFor: "Solo professionals who want booking to feel premium",
    url: "https://savvycal.com",
    verdict:
      "SavvyCal is the connoisseur's booking link: every interaction feels considered, from overlay views to sensible defaults. At $10 flat it is an easy upgrade for anyone whose calendar is a first impression.",
    faqs: [
      {
        q: "What makes SavvyCal different?",
        a: "The scheduling page itself — overlay views and a recipient-first UX nobody else matches.",
      },
      {
        q: "Is there a free plan?",
        a: "No — paid plans start at $10 a user a month.",
      },
      {
        q: "Who is it for?",
        a: "Solo professionals and consultants who want booking to feel premium.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI review management
  // ------------------------------------------------------------------
  {
    name: "NiceJob",
    slug: "nicejob",
    tagline: "The simplest review flow for single-location SMBs.",
    category: "ai-review-management",
    pricing: "From $75/mo (no contract)",
    pros: [
      "Easiest setup in the category",
      "Month-to-month, no contract",
      "Strong review-volume lift per dollar for small shops",
    ],
    cons: [
      "Single-location focus; multi-location is not its strength",
      "Fewer all-in-one features than Podium or Birdeye",
    ],
    bestFor: "Single-location service businesses that just need more Google reviews",
    url: "https://nicejob.com",
    verdict:
      "NiceJob is the 'just get me more reviews' tool: $75, no contract, automatic asks after every job. Single-location shops should start here and only look upmarket when they outgrow it.",
    faqs: [
      {
        q: "How much is NiceJob?",
        a: "$75 a month Starter, $125 a month Pro — month-to-month, no contract.",
      },
      {
        q: "How does it get reviews?",
        a: "Automatic SMS and email requests after each job, with Google and Facebook integration.",
      },
      {
        q: "Is it good for multi-location?",
        a: "It is built for single-location SMBs; multi-location brands should look at Birdeye.",
      },
    ],
  },
  {
    name: "Broadly",
    slug: "broadly",
    tagline: "Reviews plus webchat and payments for local business.",
    category: "ai-review-management",
    pricing: "From $79/mo",
    pros: [
      "Bundles reviews, webchat, and payments",
      "Good mid-market value between NiceJob and Birdeye",
      "Strong for home services",
    ],
    cons: [
      "Less depth on review analytics than Birdeye",
      "Full automation tier is quote-based",
    ],
    bestFor: "Home-service businesses that want reviews plus payments in one bill",
    url: "https://broadly.com",
    verdict:
      "Broadly sits in the sweet spot between NiceJob's simplicity and the enterprise suites: reviews plus webchat plus payments from $79. Home-service businesses that want one bill should shortlist it.",
    faqs: [
      {
        q: "What does $79 a month include?",
        a: "The Reputation AI tier covers Google and Facebook review management.",
      },
      {
        q: "Does Broadly do payments?",
        a: "Yes — payments and webchat are bundled on higher tiers.",
      },
      {
        q: "Who is Broadly for?",
        a: "Home-service and local businesses that want reviews plus payments in one bill.",
      },
    ],
  },
  {
    name: "Birdeye",
    slug: "birdeye",
    tagline: "The full reputation suite for multi-location brands.",
    category: "ai-review-management",
    pricing: "From ~$299/mo per location (quote-based)",
    pros: [
      "200+ review sites tracked in one dashboard",
      "AI response drafting at scale",
      "Multi-location management that works past 10 locations",
    ],
    cons: [
      "Overkill and overpriced for single-location SMBs",
      "Quote-based pricing with annual contracts",
      "Steep learning curve",
    ],
    bestFor: "Multi-location brands with serious reputation operations",
    url: "https://birdeye.com",
    verdict:
      "Birdeye is the enterprise answer: every review site, competitive intel, dashboards that survive 10+ locations. At ~$299 per location per month on annual contracts, single-location shops should not be here.",
    faqs: [
      {
        q: "Why is Birdeye so expensive?",
        a: "It is priced per location (around $299 a month) for multi-location brands — overkill for a single shop.",
      },
      {
        q: "Can I see pricing without a sales call?",
        a: "No — Birdeye is quote-based; third parties report roughly $299 to $499 per location per month.",
      },
      {
        q: "What do I get over NiceJob?",
        a: "200+ review sites, competitive intelligence, and dashboards that work past 10 locations.",
      },
    ],
  },
  {
    name: "Podium",
    slug: "podium",
    tagline: "SMS-first review and messaging platform for local business.",
    category: "ai-review-management",
    pricing: "From ~$399/mo (quote-based)",
    pros: [
      "Best SMS review-request workflows in the business",
      "Webchat, payments, and AI messaging in one platform",
      "Dominant with dealerships and home services",
    ],
    cons: [
      "Expensive — hard to justify on reviews alone under 500 customers a month",
      "Pricing hidden behind sales calls",
    ],
    bestFor: "High-volume local businesses that live on text messaging",
    url: "https://podium.com",
    verdict:
      "Podium is a messaging platform that happens to do reviews brilliantly — SMS requests convert, and webchat plus payments ride along. The ~$399+ price only makes sense when texting is already how you run the business.",
    faqs: [
      {
        q: "How much does Podium cost?",
        a: "List pricing is quote-based; third parties report roughly $399 to $599 a month.",
      },
      {
        q: "Is Podium just reviews?",
        a: "No — it is a messaging platform: reviews via SMS, webchat, payments, and AI agents.",
      },
      {
        q: "Who should buy Podium?",
        a: "High-volume local businesses (dealerships, home services) that live on texting.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI marketing
  // ------------------------------------------------------------------
  {
    name: "Jasper",
    slug: "jasper",
    tagline: "On-brand AI content at scale for marketing teams.",
    category: "ai-marketing",
    pricing: "From $49/seat/mo (Creator)",
    pros: [
      "Best brand-voice enforcement in the category",
      "Campaign templates and shared workspaces",
      "Publishes straight to WordPress",
    ],
    cons: [
      "No free plan — trial, then pay",
      "Output still needs a strong editor",
      "$69/seat Pro stings for solo users",
    ],
    bestFor: "Teams producing high volumes of on-brand copy",
    url: "https://www.jasper.ai",
    verdict:
      "Jasper earns its fee on volume: brand voice that actually holds across hundreds of pieces, templates for every format, team workflows. Solo bloggers should stick with a $20 chat assistant; content teams will feel the difference.",
    faqs: [
      {
        q: "How much is Jasper?",
        a: "Creator is $49 a seat a month ($39 annual); Pro is $69 ($59 annual).",
      },
      {
        q: "Is there a free plan?",
        a: "No — trial only, then paid.",
      },
      {
        q: "Do I still need an editor?",
        a: "Yes — Jasper is consistent, not brilliant. Keep a human on anything public.",
      },
    ],
  },
  {
    name: "Copy.ai",
    slug: "copy-ai",
    tagline: "AI workflows for sales and marketing teams.",
    category: "ai-marketing",
    pricing: "From $24/mo",
    pros: [
      "Generous seat allowance on entry plans",
      "2,000+ integrations",
      "Fast for ads, emails, and social captions",
    ],
    cons: [
      "Long-form output needs heavy editing",
      "Pricing has changed repeatedly — verify current tiers",
      "Text only, no images",
    ],
    bestFor: "Sales and marketing teams automating repetitive writing",
    url: "https://www.copy.ai",
    verdict:
      "Copy.ai is the workflow play: less about beautiful prose, more about automating the repetitive writing inside sales and marketing processes. Verify current pricing before committing — it has moved several times this year.",
    faqs: [
      {
        q: "How much is Copy.ai?",
        a: "Paid plans start around $24 to $29 a month; pricing has changed often, so verify.",
      },
      {
        q: "Is the free plan still around?",
        a: "It has shrunk significantly — check the current offering before counting on it.",
      },
      {
        q: "What is Copy.ai best at?",
        a: "Short-form: ads, emails, social captions, and sales workflows.",
      },
    ],
  },
  {
    name: "HubSpot",
    slug: "hubspot",
    tagline: "Free CRM with Breeze AI across marketing and sales.",
    category: "ai-marketing",
    pricing: "Free CRM; Marketing Hub Starter from $15/seat/mo",
    pros: [
      "Genuinely free CRM to start",
      "Breeze AI agents across content, social, and service",
      "All-in-one: CRM, email, landing pages",
    ],
    cons: [
      "Costs scale steeply with contacts and seats",
      "Professional tiers jump to around $890 a month",
    ],
    bestFor: "Businesses that want CRM plus marketing in one system",
    url: "https://www.hubspot.com",
    verdict:
      "HubSpot's free CRM remains the best on-ramp in the business, and Breeze AI now touches content, prospecting, and service. Go in eyes open: the bill grows with your contacts, and Professional tiers are a real jump.",
    faqs: [
      {
        q: "Is HubSpot really free?",
        a: "The CRM is free. Marketing automation needs Marketing Hub — Starter from $15 a seat a month.",
      },
      {
        q: "What is Breeze?",
        a: "HubSpot's AI layer: agents for content, prospecting, social, and customer service.",
      },
      {
        q: "When does HubSpot get expensive?",
        a: "As contacts and seats grow — Professional tiers run around $890 a month.",
      },
    ],
  },
  {
    name: "Mailchimp",
    slug: "mailchimp",
    tagline: "The safe all-rounder for small-business email.",
    category: "ai-marketing",
    pricing: "Free; Essentials from $13/mo",
    pros: [
      "Everyone knows it; easy to hire for",
      "AI subject lines and send-time optimization",
      "Free tier to start",
    ],
    cons: [
      "Pricing climbs with list size",
      "Less automation depth than ActiveCampaign",
    ],
    bestFor: "Email-first businesses that want the safe choice",
    url: "https://mailchimp.com",
    verdict:
      "Mailchimp is the default small-business email tool for a reason: it is easy, the AI touches (subject lines, send-time) genuinely help, and the free tier gets you started. Price it at your 2,000-contact size before committing.",
    faqs: [
      {
        q: "Is Mailchimp free?",
        a: "Yes, up to 500 contacts with limits; Essentials starts at $13 a month.",
      },
      {
        q: "Does Mailchimp have AI?",
        a: "Yes — AI subject lines, send-time optimization, and segmentation help.",
      },
      {
        q: "Mailchimp vs Constant Contact?",
        a: "Mailchimp is the all-rounder; Constant Contact is simpler for true beginners.",
      },
    ],
  },
  {
    name: "Constant Contact",
    slug: "constant-contact",
    tagline: "Simple email marketing for small business and events.",
    category: "ai-marketing",
    pricing: "From $12/mo",
    pros: [
      "Easiest learning curve in email marketing",
      "Strong event marketing features",
      "Good phone support for non-technical owners",
    ],
    cons: [
      "Fewer advanced automations than competitors",
      "Templates feel dated next to newer tools",
    ],
    bestFor: "Non-technical owners who want email done simply",
    url: "https://www.constantcontact.com",
    verdict:
      "Constant Contact is the simplest serious email tool: if Mailchimp feels like too much software, start here. Power users will outgrow it; everyone else will appreciate the phone support.",
    faqs: [
      {
        q: "How much is Constant Contact?",
        a: "Lite starts at $12 a month; pricing scales with contacts.",
      },
      {
        q: "Is it good for events?",
        a: "Yes — event marketing is one of its standout strengths.",
      },
      {
        q: "Who should skip it?",
        a: "Marketers who need deep automation — look at ActiveCampaign or HubSpot instead.",
      },
    ],
  },
];
