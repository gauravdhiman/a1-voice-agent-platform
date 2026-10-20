/**
 * Data for the "Small Business AI Toolbox" directory at /ai-tools.
 *
 * Curated AI tools for small businesses, organized by category. Pricing was
 * researched in October 2026 and is summarized as "from" figures. Vendors
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

export interface DecisionShortcut {
  /** "Our pick" | "Best value" | "Best free option" */
  label: string;
  tool: string;
  reason: string;
}

export interface ToolCategory {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  /** Intro paragraphs shown at the top of the category page. */
  intro: string[];
  faqs: ToolFaq[];
  /** Decision shortcut cards rendered on the category page. */
  decisionShortcuts?: DecisionShortcut[];
  /** "How to choose" questions for buyers. */
  howToChoose?: string[];
  /** Honest expectations: what the category will and will not do. */
  expectations?: { will: string[]; wont: string[] };
}

export const TOOL_CATEGORIES: ToolCategory[] = [
  {
    slug: "ai-receptionists",
    name: "AI Receptionists",
    tagline: "AI that answers your business phone",
    description: "AI receptionists that answer every call, take messages, and book appointments for small businesses: compared on price, minutes, and human backup.",
    intro: [
      "An AI receptionist is a voice assistant that answers your business phone when you cannot: after hours, when you are on another call, or when you are on a job with your hands full. It talks with callers in a natural voice, answers routine questions from your business information, books appointments, takes messages, and captures leads, then sends you a summary of every call. Your customers dial the same number they always have; from their side, someone simply always picks up.",
      "For a small or medium business, this is the cheapest way to stop losing calls to voicemail. Research consistently shows most callers who reach voicemail never call back, and a missed after-hours call in trades or services is often a job your competitor books. One note on honesty: 24x7 AI is our own product, and it is reviewed in this category alongside its competitors with the same structure and the same candor about limits. Compare the facts, not the logos.",
    ],
    decisionShortcuts: [
      {
        label: "Our pick",
        tool: "24x7 AI",
        reason: "Our own AI front desk: concierge setup done with you, your number plus a website voice button, live in 48 hours. (We build it, so check our claims against the others.)",
      },
      {
        label: "Best value",
        tool: "Rosie",
        reason: "$49 a month for 250 minutes with a sub-30-minute setup is the cheapest credible 24/7 coverage from an established AI-only vendor.",
      },
    ],
    howToChoose: [
      "How do you want to be billed: per minute, per call, per caller, or per agent? Count your real monthly calls and their average length, then price each vendor's model against your numbers, because the cheapest headline is rarely the cheapest invoice.",
      "Do you need the AI to book into your actual calendar, or is message-taking enough? Calendar booking is gated behind higher tiers at Rosie and Dialzara, so decide this before you compare prices.",
      "Will any of your calls need a human voice: angry callers, sensitive intake, complex situations? Only Smith.ai and Abby Connect offer real people as backup; every other tool here is AI-only.",
      "Who sets it up? If you want done-for-you, 24x7 AI and Abby Connect hold your hand; if you want self-serve in 15 minutes, Dialzara and Rosie are faster to start.",
      "Do you handle health, financial, or legal information on calls? Then compliance is not optional: verify HIPAA, BAA, or SOC 2 claims in writing with the vendor before routing calls, because several vendors here do not publish them.",
    ],
    expectations: {
      will: [
        "Answer every call 24/7, including nights, weekends, and holidays, so no caller ever reaches voicemail again",
        "Handle the routine reliably: hours, prices, directions, booking, rescheduling, and message-taking with instant summaries to you",
        "Capture after-hours and overflow leads with names, numbers, and reasons, so Monday morning starts with opportunities instead of a voicemail pile",
        "Filter spam and telemarketers before they reach you, and log every call with a transcript you can scan in seconds",
      ],
      wont: [
        "Replace human judgment on sensitive, emotional, or legally complex calls: AI-only tools will take a message, and only Smith.ai and Abby Connect can put a real person on the line",
        "Know your business on day one without training: every tool needs your services, prices, hours, and rules, and the first weeks need you reviewing transcripts to catch wrong answers",
        "Eliminate your phone bill surprises by itself: minutes, calls, callers, and credits all meter differently, so you still have to size the plan to your real volume",
      ],
    },
    faqs: [
      {
        q: "Will my customers know they are talking to an AI?",
        a: "Some will, most will not care as long as the call goes well. Modern voices sound natural, and callers mainly notice when the AI cannot help them. That is why the first weeks matter: review transcripts, fix wrong answers, and set clear rules for when the AI should take a message instead of guessing.",
      },
      {
        q: "Do I have to change my business phone number?",
        a: "No. Every tool here works by call forwarding: you keep your number, customers dial what they always dialed, and you control when the AI answers (all calls, overflow only, or after hours).",
      },
      {
        q: "How many minutes or calls do I actually need?",
        a: "Count last month's missed and after-hours calls and multiply by 3 minutes, the typical service call length. A solo operator often lands at 60 to 250 minutes; a busy shop at 500 to 1,000. Then check what overage costs, because the plan that fits your average month can still sting in your busiest one.",
      },
      {
        q: "Can these tools really book appointments, or do they just take messages?",
        a: "Most can book into Google Calendar, Outlook, or scheduling tools, but several gate real calendar booking behind higher tiers (Rosie's $49 plan and Dialzara's $29 plan do not include it). If booking matters, confirm it is in the tier you are actually buying.",
      },
      {
        q: "What happens when the AI cannot answer a question?",
        a: "Good ones say so honestly, take a detailed message, and alert you immediately. Bad ones guess. During your trial, deliberately call with a question outside its training and listen to what it does: that tells you more than any demo.",
      },
      {
        q: "Are calls recorded, and is that legal?",
        a: "Yes, all of these tools record and transcribe calls. Whether you must tell the caller depends on your state's recording-consent laws: some states need one party's consent, others need all parties'. The disclosure is your responsibility, and most tools offer a recording notice you can switch on.",
      },
      {
        q: "AI-only or human backup: which do I need?",
        a: "If your calls are routine (booking, hours, quotes), AI-only is fine and much cheaper. If callers are ever upset, grieving, or sharing sensitive legal or medical details, a human voice matters, and only Smith.ai and Abby Connect offer one. Match the tool to your hardest call, not your easiest.",
      },
      {
        q: "How long does setup take?",
        a: "Self-serve tools (Dialzara, Rosie, Goodcall) take 15 to 60 minutes: you answer questions about your business and the AI reads your website. Concierge tools (24x7 AI, Abby Connect, Smith.ai Pro) take longer but do the work with you, typically live within 48 hours to a week.",
      },
    ],
  },
  {
    slug: "ai-chatbots",
    name: "AI Chatbots",
    tagline: "AI chat for your website",
    description: "AI chatbots that answer website visitors, capture leads, and deflect support tickets, compared for small business budgets and setup effort.",
    intro: [
      "AI chatbots are the assistants that talk to your customers when you cannot: the chat bubble on your website, the auto-replies in your Instagram DMs, the bot that answers what time you close at midnight. Modern chatbots are powered by real AI, so they understand plain language and answer from your own website, documents, and policies, not from a rigid script you have to program.",
      "For a small or medium business, this category matters for one reason: it is the cheapest way to never miss a customer question again. A good chatbot answers routine questions around the clock, captures leads while you sleep, and hands the tricky conversations to a human with the full story attached. A bad one frustrates customers and costs you sales, so the choice matters more than the price tag suggests.",
    ],
    decisionShortcuts: [
      {
        label: "Our pick",
        tool: "Tidio",
        reason: "the best all-rounder for small businesses, with an AI agent, live chat, and ticketing in one inbox, a free plan that actually works, and billing per conversation instead of per seat.",
      },
      {
        label: "Best value",
        tool: "ManyChat",
        reason: "the cheapest way to automate conversations at $14 a month, ideal if your customers talk to you on Instagram, Messenger, or WhatsApp rather than your website.",
      },
    ],
    howToChoose: [
      "Where do your customers already talk to you: your website, Instagram, WhatsApp, or email? A website chat tool and a social DM tool are different products; pick the one that covers where your customers are.",
      "Do you want the bot to just answer questions, or also capture leads, book appointments, and hand off to a human? The more it does, the more you pay, so decide what actually earns money for you.",
      "How do you want to be billed: per conversation (Tidio), per contact (ManyChat), per message credit (Chatbase), or per result (Intercom)? Pick the meter that matches how your business grows.",
      "Who answers when the bot gets stuck? A smooth handoff to a human with the full transcript is the difference between a chatbot that helps and one that infuriates.",
      "Is the vendor stable? One tool in this category, Drift, is being shut down in 2026, which is a reminder to check that the company you pick is still investing in the product.",
    ],
    expectations: {
      will: [
        "Answer your most common questions instantly, 24/7, in your customers' language, using your own website and documents as the source of truth.",
        "Capture leads for you: a good chatbot asks for name, email, and what they need, then routes the hot ones to you with the conversation attached.",
        "Take a real share of routine support off your plate. Vendors report their AI resolving a majority of routine questions; your mileage depends on the quality of the content you feed it.",
        "Work on the channels your customers already use, whether that is your website (Tidio, Chatbase), social DMs (ManyChat), or email and phone (Intercom Fin).",
      ],
      wont: [
        "Know things you never taught it. A chatbot is only as smart as your help content; a thin website means a confused bot.",
        "Handle complaints, refunds, or sensitive conversations well. You still need a human handoff for anything where judgment matters.",
        "Be free at scale. Every vendor meters usage (conversations, contacts, credits, or outcomes), and the bill rises as your traffic grows, so price the growth, not just the entry plan.",
      ],
    },
    faqs: [
      {
        q: "Will customers know they are talking to a bot?",
        a: "Usually yes, and that is fine. Most tools can introduce the bot by name, and Intercom even adds visible AI labelling. What customers hate is not a bot, it is a bot that cannot hand them to a human when it fails.",
      },
      {
        q: "How long does it take to set one up?",
        a: "Hours to an afternoon for Tidio, Chatbase, or ManyChat if you use their templates and your content already exists. Intercom Fin takes longer because it is only as good as your help center, so budget days and content work there.",
      },
      {
        q: "What happens when the bot cannot answer?",
        a: "On every tool here it hands the conversation to a human with the full transcript attached, so the customer does not repeat themselves. Test this flow before you go live; it is the single most important thing to get right.",
      },
      {
        q: "Can one bot cover my website, Instagram, and WhatsApp?",
        a: "Not perfectly. Tidio covers website chat best plus social channels in one inbox; ManyChat owns social DMs but has no website widget; Chatbase embeds anywhere but is bot-first. Most small businesses end up with one website tool and, if social matters, ManyChat beside it.",
      },
      {
        q: "What does it cost when my traffic doubles?",
        a: "It depends on the meter: Tidio charges per conversation, ManyChat per active contact, Chatbase per message credit, Intercom per outcome. Read the pricing catches section of each review here before you commit, and check the usage dashboard monthly in your first quarter.",
      },
      {
        q: "Is my customer data safe with these tools?",
        a: "Tidio, Chatbase, Intercom, and ManyChat all document GDPR alignment, encryption, and privacy controls on their security pages (Intercom's is the strongest, with SOC 2 Type II, HIPAA, and ISO certifications verified from its own site). Chatbase states it never trains models on your data. None of them handles legal responsibility for you: you still need a privacy policy and, in Europe, proper consent for tracking.",
      },
      {
        q: "Do I need a developer?",
        a: "No, for the core setup. All five are no-code for standard use. You need a developer only for custom integrations, which Chatbase, Intercom, and Tidio support through APIs on their higher plans.",
      },
      {
        q: "Can the bot book appointments?",
        a: "Yes, on most: Tidio connects to calendars via integrations, ManyChat flows can route to booking links, and Intercom Fin can follow booking procedures. Confirm your specific booking tool is supported before you buy.",
      },
    ],
  },
  {
    slug: "ai-scheduling",
    name: "AI Scheduling",
    tagline: "AI that manages your calendar",
    description: "AI scheduling tools for bookings, focus time, and calendar defense: from simple booking links to AI that plans your whole day.",
    intro: [
      "AI scheduling tools do two different jobs. The first is booking: letting clients, leads, and colleagues book time with you through a link, without the endless 'what time works for you' thread. The second is planning: taking your tasks, deadlines, habits, and focus time and arranging them intelligently across your week, then rearranging them when reality changes.",
      "For a small or medium business, both jobs matter because time is the one resource you cannot buy more of. A missed booking is missed revenue. An unmanaged week is a slow leak of hours into meetings that could have been planned around. The tools in this category either hand you a smarter booking link (Calendly, Cal.com, SavvyCal) or an AI that actively manages your calendar (Reclaim.ai, Motion), and a few do a bit of both.",
    ],
    decisionShortcuts: [
      {
        label: "Our pick",
        tool: "Calendly",
        reason: "the booking link everyone already knows how to use, with a real free tier, integrations with everything, and pricing that stays sane for solos.",
      },
      {
        label: "Best value",
        tool: "Reclaim.ai",
        reason: "free forever to start, then $10 a seat a month for focus-time defense, habit scheduling, task auto-scheduling, and booking links in one, the most automation per dollar here.",
      },
      {
        label: "Best free option",
        tool: "Cal.com",
        reason: "the free plan gives one user unlimited event types, unlimited calendars, payments, and 100+ integrations at $0, plus open-source code you can self-host.",
      },
    ],
    howToChoose: [
      "Is your main job letting other people book you, or planning your own day? Booking points to Calendly, Cal.com, or SavvyCal; day-planning points to Reclaim.ai or Motion.",
      "How many people need seats? Per-seat pricing is gentle for a solo and painful for a team of ten, so multiply before you fall in love.",
      "Which calendar and tools must it sync with? Google Calendar users get the best of everything; Outlook-only shops should test Reclaim carefully, and CRM or payment needs change which plan you actually need.",
      "Do you need branded links, payments, or automation on day one? Those features sit on different tiers in every tool, so check the plan that has your must-haves, not the headline price.",
      "How much do you care about data control? Cal.com can be self-hosted, Calendly and Reclaim publish SOC 2 credentials, and SavvyCal publishes none, so match the tool to your comfort level.",
    ],
    expectations: {
      will: [
        "End the scheduling back-and-forth: booking links and polls replace the 'what time works for you' thread for good.",
        "Cut no-shows: automatic reminders on paid plans meaningfully reduce forgotten appointments.",
        "Protect real work time, once tuned: Reclaim and Motion will defend focus blocks and reschedule tasks around meetings after roughly a week of adjustment.",
        "Keep availability honest: calendar sync means nobody can book over your existing commitments.",
      ],
      wont: [
        "Run your follow-up for you: a booked meeting still needs you to show up prepared and follow through.",
        "Read your mind on day one: the AI planners need about a week of tuning before the automation matches how you actually work.",
        "Replace a CRM or project manager by themselves (Motion comes closest by bunding light project management, the rest do not try).",
      ],
    },
    faqs: [
      {
        q: "Will a scheduling tool replace my assistant?",
        a: "For the mechanics of booking, mostly yes: links, reminders, and routing handle what an assistant used to do by email. For judgment calls, VIP handling, and complex multi-party coordination, no. Most small businesses end up with the tool handling 80 percent and a human handling the rest.",
      },
      {
        q: "Google Calendar or Outlook: does it matter?",
        a: "Somewhat. Every tool here supports both, but reviewers consistently say features mature fastest on Google Calendar (Reclaim most notably). If you live in Outlook, test your shortlist on the free tier or trial before committing.",
      },
      {
        q: "Do my clients need an account to book with me?",
        a: "No. On every booking tool here, your clients just click a link and pick a time. No account, no app, no cost to them. Only the people hosting meetings need seats.",
      },
      {
        q: "How do these handle time zones?",
        a: "Automatically. Bookers see your availability in their own local time zone, so a client in New York and a consultant in Phoenix never have to do the math.",
      },
      {
        q: "Can I charge for appointments?",
        a: "Yes on most paid plans: Calendly (Standard and up) and SavvyCal (Premium) connect to Stripe or PayPal so clients pay when they book. Cal.com includes Stripe and PayPal payments even on its free plan.",
      },
      {
        q: "What is the difference between booking tools and AI planners?",
        a: "Booking tools (Calendly, Cal.com, SavvyCal) let other people schedule time with you. AI planners (Reclaim.ai, Motion) schedule your own work: tasks, habits, and focus time arranged around your meetings. Some businesses need one, some need both.",
      },
      {
        q: "Is my calendar data safe with these tools?",
        a: "Calendly and Reclaim.ai publish SOC 2 Type II certifications and maintain trust centers; Cal.com's Organizations plan lists SOC 2 Type II, HIPAA, and ISO 27001, and it can be self-hosted for full data control. SavvyCal publishes no compliance certifications. For regulated use, verify current certificates with the vendor before buying.",
      },
    ],
  },
  {
    slug: "ai-review-management",
    name: "AI Review Management",
    tagline: "More 5-star reviews on autopilot",
    description: "Review management software that automatically requests reviews, drafts responses, and protects your Google rating.",
    intro: [
      "Review management software automates the single most valuable marketing task a local business has: asking happy customers for reviews, and doing it every single time. Instead of relying on whoever remembers to ask, the software sends the request by text or email after each job or visit, routes happy customers to Google, catches unhappy ones with private feedback first, and helps you reply to everything quickly.",
      "Why it matters: the vast majority of customers now check reviews before choosing a local business, and most only trust recent ones. A business with 200 reviews and a 4.8 rating wins the call over a competitor with 12 reviews, even when the work is identical. These tools turn reviews from something you hope happens into a system that runs itself.",
    ],
    decisionShortcuts: [
      {
        label: "Our pick",
        tool: "NiceJob",
        reason: "The simplest honest path from zero reviews to reviews on autopilot: $75 a month, no contract, requests fire when the job ends.",
      },
      {
        label: "Best value",
        tool: "Podium",
        reason: "Not cheap, but one invoice replaces a review tool, a texting tool, and a payment link tool if you will actually use the whole stack.",
      },
      {
        label: "Best free option",
        tool: "None of these four has a free plan",
        reason: "On a zero budget, text customers Google's own free review link after each job and reply from your Google Business Profile manually.",
      },
    ],
    howToChoose: [
      "Do you need reviews only, or reviews plus texting, webchat, and payments? Reviews-only tools cost $75 to $125 a month; bundled platforms run $400 and up.",
      "How many locations do you have? Per-location pricing multiplies fast, and only the enterprise tools have real multi-location dashboards.",
      "Can it pull customers automatically from the software you already run, like your scheduler or point of sale? Manual uploads die within a month.",
      "Who replies to reviews, and how fast? If nobody owns it, pick a tool with AI-drafted or automatic replies.",
      "Are you signing an annual contract? The expensive platforms are annual with real cancellation friction, so get the cancellation terms in writing first.",
    ],
    expectations: {
      will: [
        "Send a review request after every job or visit automatically, so asking stops depending on memory",
        "Route happy customers to Google and unhappy ones to private feedback first, protecting your public rating",
        "Make replying fast with AI-drafted or automatic responses, keeping your response rate high",
        "Put your best reviews on your website and social media to help close the next customer",
      ],
      wont: [
        "Make unhappy customers happy: the software amplifies your real reputation, it does not fix a 2-star business",
        "Stop fake or unfair reviews from appearing: it can alert you faster, but removal still goes through Google's process",
        "Replace the actual ask entirely: the best results still come when your team mentions the review warmly and the software handles the follow-through",
      ],
    },
    faqs: [
      {
        q: "How much should a small business pay for review management?",
        a: "Reviews-only tools run $75 to $125 a month with no contract (NiceJob, Broadly's Reputation AI). Bundled platforms with messaging and payments run $400 to $800 a month all-in on annual contracts (Podium, Broadly's full platform). Multi-location platforms run about $300 to $450 per location per month (Birdeye). Start with reviews-only unless you will genuinely use the bundle.",
      },
      {
        q: "Will this get me more Google reviews, or just organize the ones I have?",
        a: "More reviews, if you set up the automation. The entire value is the automatic ask after each job or visit, plus follow-up reminders to non-responders. Businesses that connect their scheduler and let the requests fire consistently typically see review volume multiply within a few months.",
      },
      {
        q: "Can I just ask customers myself instead of paying for software?",
        a: "You can, and on a zero budget you should: text Google's free review link after each job. Software earns its keep through consistency (every customer, every time), follow-up reminders, unhappy-customer routing, and reply assistance. Most businesses that try the manual route stop asking within weeks.",
      },
      {
        q: "Do these tools work with my scheduling or booking software?",
        a: "Usually yes. NiceJob connects natively to Jobber, Housecall Pro, and ServiceTitan; Broadly covers Jobber, Housecall Pro, QuickBooks, and several vertical tools; Birdeye has one of the deepest integration lists including Salesforce, HubSpot, and healthcare systems; Podium connects through Zapier. Confirm your specific software during the demo, not after you pay.",
      },
      {
        q: "What about bad reviews? Can the software remove them?",
        a: "No software can remove reviews; only Google (or the platform) can, through their dispute process. What these tools do is better: route unhappy customers to private feedback before they post publicly, alert you instantly when a bad review lands, and help you reply fast and professionally, which is what prospective customers actually judge you on.",
      },
      {
        q: "Are there contracts? Can I cancel?",
        a: "It depends on the tier. NiceJob bills monthly with no contract. Broadly's entry tier is monthly; its larger bundles and Podium and Birdeye are typically annual contracts, and customer reviews report real friction canceling Podium and a 90-day notice window at Birdeye. Read the cancellation clause before signing anything annual.",
      },
      {
        q: "I have three locations. Which tool fits?",
        a: "At three locations, Birdeye starts to earn its keep: per-location dashboards, competitor benchmarking, and 200+ review site coverage are built for exactly this. Podium also handles multi-location well if messaging is your priority. Reviews-only tools get awkward past two or three locations because they lack roll-up reporting.",
      },
    ],
  },
  {
    slug: "ai-marketing",
    name: "AI Marketing Tools",
    tagline: "AI for content, email, and campaigns",
    description: "AI marketing tools for content creation, email, and CRM: what actually saves time for a small business in 2026.",
    intro: [
      "AI marketing tools are software that uses artificial intelligence to help you create content, send better emails, and run campaigns without a marketing team. That covers a wide range: AI writing assistants that draft your blog posts and ads, email platforms with AI that writes subject lines and builds automations, and all-in-one systems that combine your customer data with AI-powered marketing.",
      "For a small or medium business, the payoff is leverage. One person with the right tools can now produce the content output of a small team: newsletters written and scheduled, ad variations tested, follow-up emails automated, and every customer interaction recorded in one place. The category rewards starting simple: pick the tool that solves your most painful marketing job first, prove the value, and expand from there rather than buying the biggest platform on day one.",
    ],
    decisionShortcuts: [
      {
        label: "Our pick",
        tool: "HubSpot",
        reason: "The only tool here with a genuinely free plan that includes a real CRM, so you can start marketing properly at zero cost and grow into paid tiers deliberately.",
      },
      {
        label: "Best value",
        tool: "Copy.ai",
        reason: "The $29 Chat plan gets five people unlimited AI writing across three model families, the cheapest serious AI writing deal in the category.",
      },
      {
        label: "Best free option",
        tool: "HubSpot free plan",
        reason: "Free forever with 2,000 branded email sends a month and a working CRM; nothing else free comes close.",
      },
    ],
    howToChoose: [
      "What is the one marketing job eating your week? If it is writing, start with an AI writer. If it is email, start with an email platform. Buy for the pain, not the feature list.",
      "Do you need a CRM too, or just marketing? If customer tracking matters, HubSpot's free CRM changes the math. If you only send newsletters, a dedicated email tool is simpler and cheaper.",
      "How big is your list, really? Email tools price by contacts, and costs climb fast past a few thousand. Check what your list will cost at its size in a year, not just today.",
      "Will you actually use automation, or just send broadcasts? An honest answer saves money: simple senders do fine on entry tiers, while automation fans should compare mid and top tiers directly.",
      "Who will run it? If nobody on your team wants to learn software, prioritize ease of use and human support over feature depth.",
    ],
    expectations: {
      will: [
        "Draft your marketing copy dramatically faster: first drafts of emails, ads, posts, and articles in minutes instead of hours",
        "Automate the repetitive follow-up: welcome series, abandoned carts, and reminders that run while you sleep",
        "Keep every customer interaction in one place, so you stop losing leads to spreadsheets and memory",
        "Test and improve: subject-line testing, send-time optimization, and reporting that shows what actually worked",
      ],
      wont: [
        "Replace your judgment about your customers: AI drafts need your knowledge of your audience, and automation needs your strategy",
        "Work without clean inputs: messy contact lists and vague briefs produce messy, generic output no matter how good the tool",
        "Stay cheap forever on email platforms: as your list grows, so does the bill, so budget for success",
      ],
    },
    faqs: [
      {
        q: "Do I need an AI marketing tool, or is a regular email tool enough?",
        a: "If you send a monthly newsletter and nothing else, a simple email tool is enough. AI earns its keep when you produce content regularly: weekly emails, ads, blog posts, or social content. The writing assistance and automation compound with volume.",
      },
      {
        q: "Will AI-written content hurt my Google rankings or sound robotic?",
        a: "Google cares about helpful, original content, not how the first draft was made. The risk is publishing unedited AI output, which reads generic. Edit every draft for accuracy, specifics, and your voice, and it performs like human-written content because a human finished it.",
      },
      {
        q: "What is the cheapest way to get started?",
        a: "HubSpot's free plan: a real CRM plus 2,000 branded email sends a month at zero cost. For AI writing specifically, Copy.ai's $29 Chat plan is the cheapest serious option. Start free, pay when the value is proven.",
      },
      {
        q: "How do these tools use my customer data?",
        a: "Your contacts and content live in each vendor's systems. Reputable vendors in this category publish SOC 2 and GDPR compliance and state they do not train models on your data; verify this on each vendor's trust or privacy pages before importing sensitive lists, and always keep your own exports.",
      },
      {
        q: "Can I switch tools later if I pick wrong?",
        a: "Yes for writing tools, more painful for email platforms. Exporting contacts is easy everywhere; rebuilding automation workflows, templates, and integrations is the real cost of switching. That is why starting with a free tier and proving value first matters.",
      },
      {
        q: "Do I need the expensive tiers?",
        a: "Usually not at first. Most small and medium businesses do their best work on entry and mid tiers for a year or more. The expensive tiers pay off when you have real volume: thousands of contacts, daily content output, or a sales team that needs lead scoring and attribution.",
      },
      {
        q: "Will these tools work with what I already use?",
        a: "Almost certainly. Email platforms in this category offer hundreds of native integrations, and HubSpot lists over 1,500. If your specific tool is not listed, Zapier bridges the gap for most common workflows.",
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
    tagline: "Your AI front desk: answers on your number, books on your calendar.",
    category: "ai-receptionists",
    pricing: "From $49/mo (250 call minutes); free plan available",
    featured: true,
    pros: [
      "Concierge setup done with you: the assistant is built around your services, prices, and hours, and you test and approve it before it goes live, so there is no DIY configuration gamble",
      "Answers on your existing business number plus a voice button on your website, so website visitors can talk to your front desk without leaving the page",
      "Books appointments into your real calendar (Google Calendar, Outlook, Cal.com) with confirmations and reminders that cut no-shows",
      "Live in 48 hours from setup to approved and answering, one of the fastest launches in this category",
      "Transparent credit pricing with a genuine free tier: 100 credits (about 10 minutes) to try before anything is paid",
      "Annual plans run 10 months for the price of 12, a clean two-month discount with no fine print",
      "No setup fee, no contracts, cancel anytime",
    ],
    cons: [
      "Built for small and medium businesses: it is not positioned for enterprise contact centers with thousands of seats",
      "A newer brand than Abby or Smith.ai, so it has a shorter public track record and fewer third-party reviews to check",
      "Usage is credit-based (10 credits a minute), which adds one small layer of math versus flat per-minute plans",
      "Deep or unusual integrations are scoped during setup rather than self-serve in a dashboard, so technical buyers trade DIY speed for done-for-you help",
    ],
    bestFor: "Small and medium businesses that want a done-for-you AI front desk that answers, books, and captures leads",
    url: "https://247ai.live",
    verdict:
      "24x7 AI is our own AI front desk, and we built it for the owner who wants coverage without becoming a phone-system administrator. Concierge setup, your number, your calendar, live in 48 hours. Compare it against the others on this page and judge it on the facts.",
    verdictBox:
      "Full disclosure: we build 24x7 AI, so take this review as us making our case, then check it against the others. What you get: an AI front desk that answers on your existing business number and through a voice button on your website, answers questions from your business info, books appointments into your real calendar, and captures after-hours leads. Plans run from $49 a month (2,500 credits, about 250 minutes) to $299, with a free tier to try it and a 10-for-12 annual discount. Setup is done with you as a concierge pilot, you test and approve before it goes live, and it is typically answering in 48 hours. The honest limits: it is built for small and medium businesses, not enterprise contact centers, and it is a newer brand than Abby or Smith.ai.",
    quickFacts: {
      price: "Free (100 credits); Starter $49/mo (2,500 credits, ~250 min); Pro $149; Scale $299",
      freeTier: "Free plan: 100 credits (~10 minutes), no card to start",
      setup: "Concierge setup with you; you approve before it goes live; live in 48 hours",
    },
    whatIsIt: [
      "24x7 AI is an AI phone assistant built for small and medium businesses. It answers every call on your business number around the clock, and it also sits on your website as a voice button visitors can talk to directly. It answers routine questions from your business information, books appointments, takes orders, and captures callback requests, all without press-1 menus or hold music.",
      "The difference from the DIY tools here is the setup model. This is a concierge pilot: you tell us how you work in a short brief, we build your front desk with your services, prices, hours, calendar, and instructions, and you test it and approve it before it ever answers a customer. You are not configuring software; you are approving a new team member.",
    ],
    businessScenarios: [
      {
        title: "Stop losing the after-hours emergency",
        description:
          "It is 9pm and a pipe burst. The caller reaches your AI front desk, which captures the name, number, and address, flags it urgent, and notifies you in seconds. The job is yours because you answered when nobody else did.",
      },
      {
        title: "Book jobs while you are on the job",
        description:
          "You are mid-appointment and cannot pick up. The assistant checks your real availability, books the caller into an open slot, and sends confirmations to both of you. You finish your current job to find the next one already scheduled.",
      },
      {
        title: "Turn website visitors into callers",
        description:
          "A visitor is browsing your site at midnight wondering about prices. They tap the voice button and ask. The assistant answers from your pricing and books them, no phone call needed, no form to abandon.",
      },
      {
        title: "Capture every lead with its context",
        description:
          "Every call is logged with the caller's name, number, and outcome, and that context flows to wherever your team works: your calendar, your inbox, a spreadsheet, or your CRM. Monday morning you see the weekend's opportunities, not a voicemail pile.",
      },
      {
        title: "Answer the repeats without lifting a finger",
        description:
          "Hours, prices, directions, order status: the assistant handles the questions your team answers fifty times a week, and only the calls that need a human reach one.",
      },
    ],
    howItWorks: [
      "Tell us how you work. A short brief covers your services, prices, hours, and how you want calls handled. It takes about 30 seconds to start.",
      "We build your front desk with you. Your business number, your calendar or scheduling system, and where call records should go (spreadsheet, CRM, dispatch system) are connected during setup, and custom integrations can be scoped around the tools you already run.",
      "You test it and approve it. Call it yourself, throw it hard questions, listen to how it sounds. Nothing goes live until you say it sounds like your front desk.",
      "It goes live, typically within 48 hours. From then on, every call is answered at night, on weekends, and during busy hours, and every booking and lead lands where your team already works.",
    ],
    pricingExplained: [
      "24x7 AI sells credits, where 10 credits buy about one minute of talk time. Four tiers: Free at $0 for 100 credits (about 10 minutes, enough to try it properly), Starter at $49 a month for 2,500 credits (about 250 minutes), Pro at $149, and Scale at $299. Pay yearly and you get 12 months for the price of 10. Need more than the plans cover? Credit packs run from $5 for 200 credits to $44 for 2,000.",
      "The concierge setup and pilot are included: no setup fee, no onboarding surcharge, no contracts. You pay for the plan and the credits it carries.",
    ],
    pricingCatches: [
      "Credits are the unit, not minutes, so there is one small conversion to learn: 10 credits per minute by default. At 250 minutes the Starter math is simple; at odd volumes, check the credit packs.",
      "The free tier's 100 credits is a genuine trial, about 10 minutes, not a plan you can run a business on. It is for testing, not for coverage.",
      "Premium integrations sit on the Scale tier and dedicated-instance deals run through the contact page rather than a public Enterprise card, so very large or unusual setups are a conversation, not a checkout.",
      "Because setup is concierge, you trade the instant self-serve signup of tools like Dialzara for a guided pilot. Most owners prefer that; DIY tinkerers may find it slower.",
    ],
    whoShouldGet: [
      "Small and medium business owners who want coverage without learning phone-system software",
      "Trades, dental, restaurants, and local services losing after-hours and overflow calls",
      "Anyone who likes the idea of approving a finished assistant instead of configuring one",
    ],
    whoShouldSkip: [
      "Enterprises needing contact-center scale, dedicated compliance teams, or published SOC 2 reports on day one",
      "DIY builders who want a self-serve API and dashboard from minute one with no human in the loop",
      "Businesses that need live human receptionists as backup: 24x7 AI is AI-only",
    ],
    comparison: [
      {
        tool: "24x7 AI (our product)",
        price: "$49/mo (~250 min)",
        difference: "Concierge setup, live in 48 hours, website voice button included; SMB-focused, newer brand",
      },
      {
        tool: "Rosie",
        price: "$49/mo (250 min)",
        difference: "Same entry price and minutes, but self-serve setup and no website voice widget",
      },
      {
        tool: "Goodcall",
        price: "$79/mo per agent (100 callers)",
        difference: "Unlimited minutes and per-caller billing, but billed per agent and no concierge setup",
      },
      {
        tool: "Smith.ai",
        price: "Free/25 calls; AI from $150/mo",
        difference: "Human backup available, but per-call pricing runs 3x the cost at volume",
      },
    ],
    goingDeeper: {
      integrations: [
        "During concierge setup we connect your business calendar (Google Calendar, Microsoft Outlook, Cal.com, and more), your email for confirmations and follow-ups, and your records destination: Google Sheets, HubSpot, a dispatch system, or another workflow. Bookings, reschedules, and reminders land where your team already works.",
        "If your team runs on a tool we have not listed, we scope a custom integration around it during setup rather than handing you a plugin catalog. The website voice button is included, not an add-on.",
      ],
      api: "24x7 AI does not publish a public self-serve developer API. Custom integrations and data flows are scoped and built with you during setup instead.",
      privacy: [
        "Every call is logged with the caller's name, number, and outcome, and recordings and transcripts are available to you. Your call data goes to the destinations you choose during setup; it is not sold or shared.",
        "We do not publish SOC 2, HIPAA, or other compliance certifications today. If you handle health, financial, or otherwise regulated calls, talk to us during the pilot about your requirements before going live, and handle recording-consent disclosure per your state's laws.",
      ],
      advancedWorkflowTitle: "After-hours capture with next-morning triage",
      advancedWorkflow:
        "Run the assistant in full-capture mode after hours: it answers every call, books what it can into tomorrow's real availability, captures the rest with name, number, and reason, and flags anything urgent for instant notification. In the morning, your team opens one triage view: booked jobs already on the calendar, captured leads with their context, and urgent callbacks at the top. Nothing to transcribe, nothing to sort. Most owners find the first month pays for the year in recovered after-hours jobs alone.",
    },
    faqs: [
      {
        q: "Wait, is this your product?",
        a: "Yes. We build 24x7 AI, which is why this page carries the disclosure and the featured badge. We have tried to review it the way we reviewed the others: same structure, same honesty about limits. Compare the facts and decide for yourself.",
      },
      {
        q: "How does the free plan work?",
        a: "100 credits, about 10 minutes of talk time, at no cost. It is enough to test the assistant on real calls and decide whether the voice and the answers fit your business. When you are ready for coverage, Starter is $49 a month.",
      },
      {
        q: "What does concierge setup actually mean?",
        a: "You give us a short brief on how you work, we build your front desk around it (number, calendar, instructions, integrations), and you test and approve it before it goes live. Most businesses are answering within 48 hours. No coding, no configuration screens you have to learn.",
      },
      {
        q: "Do I keep my business number?",
        a: "Yes. 24x7 AI answers on the number your customers already call. There is also a voice button for your website so visitors can talk to your front desk without calling.",
      },
      {
        q: "Can it book appointments?",
        a: "Yes, into your real calendar (Google Calendar, Outlook, Cal.com, and more), with confirmations and reminders that cut no-shows. It checks actual availability, so there is no double-booking.",
      },
      {
        q: "How do credits work?",
        a: "10 credits buy about one minute of talk time. Starter's 2,500 credits is about 250 minutes. Need more? Credit packs run from $5 for 200 credits to $44 for 2,000. Annual billing gives you 12 months for the price of 10.",
      },
      {
        q: "Is there a contract or a setup fee?",
        a: "No setup fee, no contracts, cancel anytime. The concierge pilot is included in the plan price.",
      },
      {
        q: "Is 24x7 AI HIPAA or SOC 2 certified?",
        a: "Not currently published. If you handle regulated calls, raise your requirements during the pilot before going live so we can tell you plainly whether we fit.",
      },
    ],
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
    tagline: "AI phone agent that bills per unique caller, not per minute.",
    category: "ai-receptionists",
    pricing: "From $79/mo per agent (100 unique callers)",
    pros: [
      "Unlimited minutes on every plan: a 20-minute estimate call costs the same as a 2-minute booking, so long calls never surprise you",
      "Per-unique-caller billing is predictable if your caller base is steady: repeat callers cost nothing extra within the month",
      "Setup is genuinely fast: most owners launch in under an hour with a template agent",
      "Multilingual from the start, so Spanish-speaking customers are covered without an add-on",
      "Handles unlimited simultaneous calls, so there is no busy signal even in a marketing spike",
      "14-day free trial with no credit card asked up front",
    ],
    cons: [
      "Billed per agent, not per business: if you want separate agents for sales and service, each one is its own subscription",
      "Pricing counts unique phone numbers, so a marketing push or a batch of spam callers can push you into overage at $0.50 per extra caller",
      "The $79 Starter plan allows only one customizable logic flow and 7 days of call history, so real-world setups usually need the $129 plan",
      "Inbound only: no outbound calling, no two-way texting follow-through from the agent itself",
      "No published developer API, so custom integrations have to run through Zapier",
      "Support is mostly email-only on lower plans, and reviewers cite slow responses when something breaks",
    ],
    bestFor: "Local businesses with steady repeat caller volumes and long calls (estimates, intake, consultations)",
    url: "https://goodcall.com",
    verdict:
      "Goodcall is the predictable-cost pick for businesses with long calls: unlimited minutes and per-caller billing mean a chatty customer never inflates your invoice. The per-agent pricing and single logic flow on Starter keep it best for one-line, one-agent setups.",
    verdictBox:
      "Goodcall is the AI receptionist for businesses whose calls run long: $79 a month gets you unlimited minutes, and you pay per unique caller, not per minute, so a 20-minute estimate costs the same as a quick booking. The catch is the pricing model cuts both ways: it is billed per agent, the Starter plan allows only one custom conversation flow, and a marketing blast can push you past your caller allowance. If your callers call back often and talk for a while, this is one of the most predictable bills in the category.",
    quickFacts: {
      price: "From $79/mo per agent (100 unique callers); $129 for 250; $249-299 for 500",
      freeTier: "14-day free trial, no free plan",
      setup: "Under an hour, template agents included, no tech skills needed",
    },
    whatIsIt: [
      "Goodcall is an AI phone agent for your business line. Instead of ringing through to voicemail when you are busy, the call is answered by a conversational AI that takes messages, captures lead details, answers routine questions, and books appointments.",
      "The distinctive bit is the pricing: you pay by the number of unique callers each month, not by minutes or calls. If the same customer calls five times, they count once. Call length does not affect your bill at all, which is unusual in this category and very friendly to businesses with long, detailed conversations.",
    ],
    businessScenarios: [
      {
        title: "Take the long estimate call without watching the clock",
        description:
          "A homeowner calls with a complicated project and talks for 25 minutes. Goodcall handles the whole conversation and logs the details. On a per-minute plan that call would eat a tenth of your monthly allowance; here it costs you nothing extra.",
      },
      {
        title: "Survive the Monday morning pile-on",
        description:
          "Three callers ring at once. Goodcall answers all three at the same time, so nobody gets a busy signal and nobody waits on hold. Every caller leaves with a booked slot or a captured message.",
      },
      {
        title: "Let repeat customers call freely",
        description:
          "Your regulars call every week with small questions. Because billing is per unique caller per month, their second, third, and fourth calls cost you nothing extra.",
      },
      {
        title: "Capture leads while the crew is on site",
        description:
          "Your team is on a job and nobody can answer. Goodcall takes each call, qualifies the lead with the questions you set, and sends you a summary so you can follow up with the hot ones first.",
      },
      {
        title: "Stop answering the same questions yourself",
        description:
          "Hours, prices, service area: the agent answers the repeats from your business info, and only the real jobs get through to you.",
      },
    ],
    howItWorks: [
      "Sign up and pick a template agent for your industry, or build one from scratch. You describe your business, services, hours, and the questions you want asked on every call.",
      "Goodcall gives you a number and you forward your business line to it. You control when the agent answers: all calls, overflow only, or after hours.",
      "Connect your calendar and your CRM or scheduling tools (Google Calendar, Outlook, Housecall Pro, and more, plus Zapier for the rest). The agent can then check real availability and log every call automatically.",
      "Callers talk to the agent in a natural voice conversation. You get a summary of every call by text or email, with transcripts and recordings in the dashboard.",
    ],
    pricingExplained: [
      "Goodcall charges per agent and per unique caller, with unlimited minutes. Starter is $79 a month for 100 unique callers, Growth is $129 for 250, and the top published tier is around $249 to $299 for 500 callers. Annual billing knocks roughly 15% off. A unique caller is one phone number in one month; if they call five times, they still count once, and call length never matters.",
      "For a business with a steady base of callers who ring more than once a month, this is one of the most predictable bills in the category. For a business whose callers are mostly one-and-done strangers, it behaves like per-call billing with extra steps.",
    ],
    pricingCatches: [
      "Extra unique callers beyond your allowance cost $0.50 each, and published reports note it can be higher in some tiers. A successful marketing push can inflate your bill in a good month.",
      "The $79 Starter plan includes only one customizable logic flow and 7 days of call history. If you need different conversation scripts for different needs, that is the $129 Growth plan.",
      "Every agent is a separate subscription. If you want one agent for the office line and another for the service line, that is two bills.",
      "There is no per-minute overage risk, but there is also no outbound calling and no published developer API: if you need those, look elsewhere.",
    ],
    whoShouldGet: [
      "Businesses with long calls: estimates, consultations, intake, or detailed scheduling conversations",
      "Shops with a steady base of repeat callers where per-caller billing shines",
      "Owners who want one agent for one line with simple, predictable coverage and no minute math",
    ],
    whoShouldSkip: [
      "Businesses that need multiple agents for multiple lines or departments (each agent is a separate bill)",
      "Teams whose call volume comes mostly from one-time callers responding to ads, where per-caller billing offers little advantage",
      "Anyone who needs outbound calling, a developer API, or a human backup for tricky calls",
    ],
    comparison: [
      {
        tool: "Goodcall",
        price: "$79/mo per agent (100 callers)",
        difference: "Unlimited minutes; per-caller billing rewards repeat callers and long calls; per-agent pricing",
      },
      {
        tool: "Rosie",
        price: "$49/mo (250 min)",
        difference: "Cheaper entry with metered minutes; long calls get expensive, but you pay per business, not per agent",
      },
      {
        tool: "Dialzara",
        price: "$29/mo (60 min)",
        difference: "Cheaper entry, but metered per minute, so it punishes exactly the long calls Goodcall handles free",
      },
      {
        tool: "24x7 AI (our product)",
        price: "From $49/mo",
        difference: "Our own AI front desk with concierge setup; compare it honestly in our full review",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native connections include Google Calendar, Microsoft Outlook, and Apple Calendar for booking, plus CRM and field-service tools like Housecall Pro, Workiz, Square, and Calendly. Goodcall states it connects in clicks to 100+ CRMs and helpdesks without heavy coding.",
        "Everything else runs through Zapier, where Goodcall has an official app with flow-completion triggers: push call data to Google Sheets, create contacts in HubSpot or Salesforce, ping Slack, or log tickets in Zendesk. Goodcall also has a Customer Lookup trigger that can pull a caller's record from your CRM mid-call.",
      ],
      privacy: [
        "Goodcall claims HIPAA compliance on its own site, which is why it markets to law firms and clinics. If you handle protected health information, get the BAA in writing before routing patient calls through it.",
        "Third-party reviews note that Goodcall lacks SOC 2, ISO 27001, audit trails, and custom role-based access, which makes it a weak fit for regulated enterprises. For a local shop it is adequate; for healthcare, finance, or insurance, verify controls before you commit.",
        "Every call is recorded and transcribed, and recordings live in your dashboard. As with all of these tools, the recording-consent disclosure is your responsibility under your state's laws.",
      ],
      advancedWorkflowTitle: "CRM auto-logging with hot-lead alerts",
      advancedWorkflow:
        "Connect Goodcall's flow-completion trigger in Zapier to your CRM: every answered call creates or updates the contact with the call summary, no manual entry. Add a filter step that fires only when the summary mentions booking intent or a quote request, and route that to an instant Slack alert or SMS to your phone. Routine calls log themselves; hot leads interrupt you. You stop reviewing every transcript and start responding to the ones that pay.",
    },
    faqs: [
      {
        q: "How is per-unique-caller billing different from per-minute?",
        a: "You pay for how many different phone numbers interact with your agent in a month, not how long they talk. 100 callers on Starter can talk for as long as they want. A caller who rings five times in a month counts once. It is great for repeat callers and long conversations, and less advantageous if your calls are all short and one-time.",
      },
      {
        q: "What counts as a unique caller, and what happens over my limit?",
        a: "Any unique phone number that interacts with your agent in the billing month. Going over costs $0.50 per extra caller on published plans. Watch this after a marketing push or if you get a wave of spam callers.",
      },
      {
        q: "Can Goodcall book appointments on my calendar?",
        a: "Yes, it connects to Google Calendar, Outlook, Apple Calendar, and scheduling tools like Calendly and Housecall Pro to check real availability and book without double-booking. Auto-reminders are included to cut no-shows.",
      },
      {
        q: "Do I keep my existing business number?",
        a: "Yes. Goodcall provides a number and you forward your business line to it. Callers dial the number they have always dialed, and you decide when the agent picks up.",
      },
      {
        q: "Does Goodcall make outbound calls?",
        a: "No. Goodcall is inbound only. If you need appointment reminders, reactivation, or lead follow-up calls made for you, look at Dialzara's outbound product or a tool built for outbound.",
      },
      {
        q: "Is there an API for developers?",
        a: "Goodcall does not publish a developer API. The practical route for custom workflows is Zapier, which exposes Goodcall triggers and actions to code and to other apps.",
      },
      {
        q: "What languages does it support?",
        a: "Multilingual support is included on all plans, covering English and Spanish plus additional languages, so diverse customer bases are covered without an add-on.",
      },
      {
        q: "Is there a contract or setup fee?",
        a: "No long-term contracts are required, and there is a 14-day free trial to test on real calls. Annual billing saves roughly 15% if you commit.",
      },
    ],
  },
  {
    name: "Smith.ai",
    slug: "smith-ai",
    tagline: "AI receptionist with real human receptionists on standby.",
    category: "ai-receptionists",
    pricing: "Free for 25 calls/mo; AI plans from $150/mo",
    pros: [
      "The only AI receptionist in this price range with an actual human safety net: live receptionists can take over calls the AI should not handle alone",
      "Free tier is genuinely usable: 25 AI-handled calls a month at no cost, the cheapest way to test AI answering on a real line",
      "One plan covers both AI and human answering, so you never buy two products or juggle two vendors",
      "Lead qualification, intake, routing, and AI scheduling are included on every AI plan, not gated behind add-ons",
      "Strong review track record: buyers consistently rate it near 5 stars across dozens of reviews",
      "Extensive integrations: 200+ including HubSpot, Salesforce, GoHighLevel, Calendly, and major PBX and contact center systems",
    ],
    cons: [
      "Per-call pricing gets expensive at volume: $150 for 75 calls works out to about $2 per call, and overage runs higher, so busy months sting",
      "A 10-minute call and a 30-second call cost the same, which punishes businesses with many short calls",
      "The free tier's extra calls cost $3 each, the highest per-call rate in the category",
      "Paid add-ons stack up: appointment booking, text follow-up, and call recording can each add per-call fees on top of the plan",
      "Human receptionist plans are a different price universe ($300/mo for 30 calls), so the AI-to-human upgrade is a jump, not a slide",
      "Cancellation requires 30 days' notice, so it is not quite cancel-anytime",
    ],
    bestFor: "Businesses where every call matters and a human voice must be available: law, medical-adjacent, high-ticket services",
    url: "https://smith.ai",
    verdict:
      "Smith.ai is the premium hybrid: AI handles the routine, real people handle the rest, all under one roof. You pay for that safety net in per-call pricing that runs hot at volume, but for high-value calls it is easy to justify.",
    verdictBox:
      "Smith.ai is the only mainstream AI receptionist with live human receptionists on standby: the AI handles routine calls and a real person takes over when the call needs judgment. AI plans start free for 25 calls a month and $150 for 75 calls, with human-answered plans from $300. The catch is per-call billing: a 30-second wrong number costs the same as a full intake, and overage runs higher than the in-plan rate. If one converted call is worth a thousand dollars, this is the easiest premium in the category to justify.",
    quickFacts: {
      price: "Free: 25 calls; AI Pro from $150/mo (75 calls); human plans from $300/mo (30 calls)",
      freeTier: "Free AI tier: 25 calls/month, then $3 per extra call",
      setup: "About 15 minutes including a simulated test call; dedicated onboarding on Pro",
    },
    whatIsIt: [
      "Smith.ai is a virtual receptionist service that answers your business calls 24/7. It comes in two flavors: an AI Receptionist that handles calls automatically, and live human receptionists who staff your phones around the clock. Many businesses use both, with the AI handling the routine and people handling the sensitive.",
      "What sets it apart is the human layer. Every other tool in this category is AI-only, which means an angry caller, a grieving family member, or a complicated legal intake gets an AI or nothing. Smith.ai can put a trained person on the line for those calls, which is why law firms, financial advisors, and high-ticket services keep choosing it despite the higher price.",
    ],
    businessScenarios: [
      {
        title: "Never let a sensitive call meet a robot alone",
        description:
          "A caller is upset about a billing dispute and getting heated. The AI recognizes the situation and hands off to a live receptionist who de-escalates, takes the details, and books a callback. You find out about a resolved situation, not a lost customer.",
      },
      {
        title: "Run legal intake without a paralegal on phones",
        description:
          "A potential client calls at 9pm about a case. The AI (or a human receptionist, your choice) runs your intake questions, captures the facts, and logs them to your case system. The lead is qualified before your morning coffee.",
      },
      {
        title: "Test AI answering without spending a dollar",
        description:
          "The free tier handles 25 calls a month. Put it on your line, let it take real calls for a few weeks, and see whether your callers accept an AI voice before you pay anything.",
      },
      {
        title: "Keep the front desk during the hiring gap",
        description:
          "Your receptionist quit and the replacement starts in six weeks. Smith.ai covers every call in the meantime, AI for the routine and humans for the tricky, with no recruiting and no training.",
      },
      {
        title: "Qualify every lead the same way, every time",
        description:
          "Budget, timeline, need: the same questions asked on every call, the answers logged to your CRM automatically. No more leads falling through because the person answering forgot to ask.",
      },
    ],
    howItWorks: [
      "Choose your mix: AI-only, human-only, or AI with human backup. Smith.ai says the AI Receptionist launches in about 15 minutes, including a simulated test call before it goes live.",
      "You train it on your business: services, intake questions, scheduling rules, and how calls should be routed. On Pro and up, a dedicated onboarding team helps build it out.",
      "Forward your business number. The AI answers instantly, 24/7, qualifying callers, booking appointments, and routing. When a call needs a human, a live receptionist takes it with the full context of what the AI already collected.",
      "Every call is recorded, transcribed, and summarized, and the data flows to your CRM or practice management system through 200+ integrations.",
    ],
    pricingExplained: [
      "Smith.ai bills per call, not per minute. The AI Receptionist has three tiers: Free at $0 for 25 calls a month, Pro from $150 for 75 to 300 calls (about $2.00 per call inside the plan), and Enterprise from $500 for 300 to 1,000+ calls. Extra calls beyond your allowance cost more per call than the in-plan rate. Live human receptionist plans are separate and much pricier: Starter $300 for 30 calls, Basic $810 for 90, Pro $2,100 for 300.",
      "Do the math on your real call volume, not the headline. At 200 calls a month, the AI Pro plan with overage runs roughly $385 a month, which is still a fraction of one hire, but it is the most expensive pure-AI option in this category.",
    ],
    pricingCatches: [
      "Per-call billing treats a 30-second wrong number and a 10-minute intake identically. If your line gets lots of short calls, you pay full price for each.",
      "Overage calls cost more than in-plan calls, and free-tier overage is $3 a call, the steepest in the category. Busy months need the next tier up, not overage.",
      "Add-ons are per call, not per month: appointment booking, SMS follow-up, and call recording fees can apply to every call in the month, so read the add-on list before you sign.",
      "AI plans are month-to-month but cancellation needs 30 days' notice, so mark your calendar if you are testing.",
    ],
    whoShouldGet: [
      "Law firms, financial services, and high-ticket businesses where one call can be worth thousands",
      "Anyone who wants AI efficiency with a human voice available for emotional or legally sensitive calls",
      "Businesses that want to test AI answering free before committing",
    ],
    whoShouldSkip: [
      "High-volume businesses with hundreds of short calls, where per-call billing is punishing",
      "Budget buyers who only need simple message-taking: Rosie or Dialzara cost a fraction",
      "Teams that need outbound calling or who want per-minute fairness for short calls",
    ],
    comparison: [
      {
        tool: "Smith.ai",
        price: "Free/25 calls; AI from $150/mo (75 calls)",
        difference: "Only one with live human backup; per-call pricing; free tier is the cheapest test in the category",
      },
      {
        tool: "Abby Connect",
        price: "$164/mo (50 Abby Minutes)",
        difference: "Also mixes human and AI, but bills per minute with AI minutes counting half; deeper CRM bench",
      },
      {
        tool: "Rosie",
        price: "$49/mo (250 min)",
        difference: "AI-only and far cheaper, but no human fallback when a call gets hard",
      },
      {
        tool: "24x7 AI (our product)",
        price: "From $49/mo",
        difference: "Our own AI front desk with concierge setup; compare it honestly in our full review",
      },
    ],
    goingDeeper: {
      integrations: [
        "One of the deepest benches in the category: 200+ integrations including HubSpot, Salesforce, and GoHighLevel for CRM and sales, Cisco, Avaya, Genesys, and RingCentral for contact center and PBX, plus Cal.com, Zapier, and Google Cloud for scheduling and automation. Region-based hosting in the US or EU is offered.",
        "Law-practice tools are a specialty: Clio, Lawmatics, PracticePanther, and similar tools connect directly, which is why so many firms land here.",
      ],
      privacy: [
        "Smith.ai's AI Receptionist pricing pages do not publish HIPAA, BAA, SOC 2, or other compliance terms. If you handle health, financial, or otherwise regulated calls, get compliance commitments in writing before routing calls through it.",
        "Calls are recorded, transcribed, and summarized, and that data flows to your connected systems. Confirm data retention and deletion terms for your jurisdiction, and handle recording-consent disclosures per your state's laws.",
      ],
      advancedWorkflowTitle: "Tiered intake with human escalation",
      advancedWorkflow:
        "Set the AI to run your standard intake on every call: qualifying questions first, answers logged to your CRM via a native integration. Configure escalation rules so calls flagged as urgent, upset, or legally sensitive route to a live Smith.ai receptionist with the AI's notes attached. Routine calls cost you the AI rate and never touch a human; the calls that decide your revenue get a person. Review the handoff transcripts weekly and tighten the AI's questions, and over a quarter your escalation rate should fall while your capture rate holds.",
    },
    faqs: [
      {
        q: "What is the difference between Smith.ai's AI and live receptionist plans?",
        a: "They are two products. The AI Receptionist (free to $500+/mo) is automated answering billed per call. The live Virtual Receptionist ($300 to $2,100/mo) is real people answering 24/7, also billed per call. You can use either or mix them: AI for the routine, humans for the sensitive.",
      },
      {
        q: "Is the free plan really free?",
        a: "Yes: 25 AI-handled calls a month at no cost, with 24/7 answering, recordings, transcription, and summaries. Calls beyond 25 cost $3 each, so it is a genuine trial on your real line, not a demo.",
      },
      {
        q: "How much does Smith.ai cost at 200 calls a month?",
        a: "Roughly $385 a month on the AI Pro plan with overage, or about $1,965 on the live Basic plan with overage, per published 2026 pricing. Per-call billing rewards low volume and punishes high volume, so model your real numbers.",
      },
      {
        q: "Can the AI transfer a call to a human?",
        a: "Yes, that is the signature feature. The AI can escalate to a live Smith.ai receptionist mid-call with the conversation context attached, so the caller never repeats themselves.",
      },
      {
        q: "Does Smith.ai integrate with my CRM?",
        a: "Almost certainly: 200+ integrations including HubSpot, Salesforce, GoHighLevel, and legal tools like Clio and Lawmatics, plus Zapier for the rest.",
      },
      {
        q: "Is Smith.ai HIPAA compliant?",
        a: "Smith.ai does not publish HIPAA, BAA, or SOC 2 terms on its AI Receptionist pricing pages. Healthcare buyers should get compliance terms in writing before sending patient calls through it.",
      },
      {
        q: "Is there a contract?",
        a: "Plans are month-to-month, but cancellation requires 30 days' notice. Live plans carry a 30-day money-back guarantee (overages excluded).",
      },
    ],
  },
  {
    name: "Abby Connect",
    slug: "abby-connect",
    tagline: "Human and AI receptionists under one subscription.",
    category: "ai-receptionists",
    pricing: "$164/mo (50 Abby Minutes; AI minutes count half)",
    pros: [
      "One plan, three ways to use it: human-only, AI-only, or any mix, and you can change the mix anytime without buying a new product",
      "Every receptionist is US-based and works in Abby's Las Vegas office, none from home, with a small dedicated team assigned to your business",
      "AI minutes count as half an Abby Minute, so routing routine calls to the AI makes your plan go up to twice as far",
      "Booking, intake, Spanish answering, call summaries, and transcripts are included, not charged per call",
      "20+ years in business serving 6,200+ businesses, one of the longest track records in this category",
      "Genuine free trial on every plan (14 days or 500 Abby Minutes) with no setup fee",
    ],
    cons: [
      "Abby Minute pricing math is confusing at first: you have to track that human minutes consume your allowance twice as fast as AI minutes",
      "More expensive than AI-only tools: $164 for 50 Abby Minutes is the priciest human-minute entry plan here",
      "Plans above 500 Abby Minutes are Enterprise quotes only, so high-volume pricing is not transparent",
      "Human coverage depends on plan rules you set; if you mis-set the AI/human split, you either overspend on human minutes or under-serve callers",
      "Not a fit if you want pure AI automation with no humans in the loop at all: the product is built around the blend",
    ],
    bestFor: "Practices and service firms that want a real person on some calls and AI efficiency on the rest, from one vendor",
    url: "https://abby.com",
    verdict:
      "Abby Connect is the flexible hybrid: one subscription you can run as humans, as AI, or as a blend, with a dedicated US-based team either way. The Abby Minute math takes a week to learn, but no other vendor lets you change the mix this freely.",
    verdictBox:
      "Abby Connect is the most flexible plan in this category: one subscription that you can use for human receptionists, the AI Receptionist, or any mix, and you can change the split whenever you like. Plans run $164 for 50 Abby Minutes up to $1,380 for 500, and because an AI minute costs half an Abby Minute, letting the AI take routine calls stretches your plan up to twice as far. The trade-off is price and complexity: this costs more than AI-only tools, and the minute math needs a little attention in your first month.",
    quickFacts: {
      price: "$164/mo (50 Abby Minutes) to $1,380/mo (500); AI minutes billed at half rate",
      freeTier: "Free trial on every plan: 14 days or 500 Abby Minutes, no setup fee",
      setup: "Guided onboarding with a Client Success Manager; dedicated team assigned",
    },
    whatIsIt: [
      "Abby Connect (now just Abby) has answered calls for small businesses for more than 20 years with US-based receptionists. In 2026 it added an AI Receptionist built in-house, and the clever part is the packaging: both live on the same plan.",
      "Your allowance is measured in Abby Minutes. A minute with a human receptionist uses one Abby Minute. A minute with the AI uses half of one, so your plan goes twice as far when the AI handles a call. You decide per rule, per time of day, or per call type which one picks up, and you can change your mind anytime without switching products. Under the hood the AI runs modern speech and voice models trained on Abby's two decades of real receptionist calls.",
    ],
    businessScenarios: [
      {
        title: "Let the AI take the night shift",
        description:
          "During business hours your dedicated human team answers, because your clients expect a person. After 6pm and on weekends, the AI answers, books, and captures leads at half the minute cost. Callers always reach a professional voice, and your plan stretches.",
      },
      {
        title: "Start with AI, grow into humans",
        description:
          "You launch with the AI answering everything because it is cheap and instant. As call volume and call value grow, you shift the important call types to your human team on the same plan. No migration, no new vendor, no new number.",
      },
      {
        title: "Handle the overflow without hiring",
        description:
          "Your front desk answers first. When they are busy, calls overflow to Abby instead of voicemail: a human or the AI picks up, books the appointment, and the summary lands in your AbbyGO app.",
      },
      {
        title: "Give Spanish-speaking callers a real answer",
        description:
          "Bilingual English and Spanish answering is included for both human and AI receptionists, so a Spanish-speaking caller gets the same intake and booking experience, not a language line surcharge.",
      },
      {
        title: "See every call in one place",
        description:
          "Summaries, transcripts, and sentiment for every call, human or AI, in the AbbyGO app and portal. You review the day in minutes and adjust your instructions whenever you see something off.",
      },
    ],
    howItWorks: [
      "Pick a plan by Abby Minutes and decide your starting mix: human, AI, or blended rules (for example, AI after hours, humans during the day). Onboarding is guided by a Client Success Manager.",
      "Abby assigns a small dedicated team of US-based receptionists who learn your business, and the AI is trained on your services, FAQs, and instructions. You get a free trial (14 days or 500 Abby Minutes) to test on real calls.",
      "Forward your number. Calls route by your rules: humans, AI, or AI first with human backup. Booking, intake, and Spanish answering are included on every plan.",
      "After every call you get summaries and transcripts in the AbbyGO app, and call data syncs to your CRM through 1,000+ integrations including Clio, Lawmatics, HubSpot, Salesforce, and Calendly.",
    ],
    pricingExplained: [
      "Abby sells Abby Minutes in four published tiers: Starter $164 a month for 50, Essential $329 for 100, Professional $599 for 200, and Growth $1,380 for 500. Enterprise plans above 500 minutes are quoted. The key mechanic: a human minute consumes one Abby Minute, an AI minute consumes half, so 50 Abby Minutes is 50 human minutes or 100 AI minutes or any blend. All plans are month-to-month, no setup fee, free trial included, and 24/7 coverage has no after-hours or weekend upcharge.",
      "Translated to plain dollars, human answering works out to roughly $2.76 to $3.29 per minute, and AI answering to roughly half that. That is premium versus AI-only tools, and that premium is the humans.",
    ],
    pricingCatches: [
      "The math is the catch: watch your human/AI split in month one, because leaning too hard on human minutes burns your allowance twice as fast.",
      "Overage is billed at your plan's per-minute rate, and plans above 500 Abby Minutes require an Enterprise quote, so very high volume pricing is not published.",
      "Professional ($599) is the first tier that includes Calendly scheduling for one event type; Growth includes three. Check which booking features your tier carries before you promise them to callers.",
      "HIPAA compliance is available, but confirm it is enabled on your plan and get the terms in writing if you handle health information.",
    ],
    whoShouldGet: [
      "Law firms, medical-adjacent practices, and professional services that want humans on sensitive calls and AI on routine ones",
      "Businesses unsure whether they want AI or human answering, who want to start with one and shift without switching vendors",
      "Owners who value a dedicated US-based team that learns their business over time",
    ],
    whoShouldSkip: [
      "Pure budget buyers: AI-only tools like Rosie and Dialzara cost a third to a fifth as much",
      "Very high-volume callers who need published pricing above 500 minutes without a sales conversation",
      "Anyone who wants AI-only automation and no human involvement at all",
    ],
    comparison: [
      {
        tool: "Abby Connect",
        price: "$164/mo (50 Abby Minutes)",
        difference: "Human plus AI on one plan; AI minutes at half rate; US-based dedicated team; priciest minute here",
      },
      {
        tool: "Smith.ai",
        price: "Free/25 calls; AI from $150/mo",
        difference: "Also hybrid, but bills per call instead of per minute; AI free tier is a cheaper way to test",
      },
      {
        tool: "Goodcall",
        price: "$79/mo per agent (100 callers)",
        difference: "AI-only, unlimited minutes, far cheaper; no human backup for calls that need judgment",
      },
      {
        tool: "24x7 AI (our product)",
        price: "From $49/mo",
        difference: "Our own AI front desk with concierge setup; compare it honestly in our full review",
      },
    ],
    goingDeeper: {
      integrations: [
        "Abby publishes 1,000+ integrations, including Clio, Lawmatics, HubSpot, Salesforce, and Calendly, with call summaries and transcripts syncing to your portal and connected CRM. Scheduling runs through Calendly with one event type on Professional and up to three on Growth.",
        "Abby does not publish a public developer API. The practical integration route is its built-in integration catalog and the AbbyGO app and portal, which carry summaries, transcripts, sentiment, and usage.",
      ],
      privacy: [
        "Abby states that HIPAA compliance is available on its plans. If you handle protected health information, confirm HIPAA is active on your tier and get the BAA in writing before routing patient calls.",
        "All receptionists work in Abby's Las Vegas office, none from home, which is a genuine data-handling difference from work-from-home answering services: calls happen in a controlled office environment.",
        "Every call is summarized and transcribed in the AbbyGO app. As with all answering services, recording-consent disclosure to callers is your responsibility under your state's laws.",
      ],
      advancedWorkflowTitle: "Split-shift routing that halves your minute burn",
      advancedWorkflow:
        "Route by the clock and by call type: business hours and VIP callers go to your dedicated human team, after-hours and routine FAQ calls go to the AI at half the minute cost. Then review your AbbyGO usage weekly and move any call type the AI handles perfectly from the human column to the AI column. Most businesses find within a month that 60 to 70 percent of calls never needed a human, and their effective cost per answered call drops by a third without callers noticing a change.",
    },
    faqs: [
      {
        q: "What is an Abby Minute?",
        a: "Abby's billing unit. One minute of talk with a human receptionist uses one Abby Minute; one minute with the AI Receptionist uses half of one. So a 50-minute plan covers 50 human minutes, 100 AI minutes, or any mix. It is how one plan can cover both services.",
      },
      {
        q: "Can I change my human and AI mix later?",
        a: "Yes, anytime, on the same plan. Start AI-only, shift your VIP callers to humans next month, go back for the holidays. That flexibility is the main reason to choose Abby over buying an AI tool and a human service separately.",
      },
      {
        q: "Are the receptionists really US-based?",
        a: "Yes. Abby states that 100 percent of its receptionists work in its Las Vegas office, none from home, and you get a small dedicated team plus a Client Success Manager rather than a random call-center pool.",
      },
      {
        q: "Is Spanish answering included?",
        a: "Yes, bilingual English and Spanish answering is included for both human and AI receptionists on every plan, with no per-call surcharge.",
      },
      {
        q: "How does the free trial work?",
        a: "Every plan includes a free trial of 14 days or 500 Abby Minutes, whichever comes first, before you pay. There is no setup fee.",
      },
      {
        q: "Can Abby book appointments?",
        a: "Yes, booking is included rather than billed per call. Calendly scheduling is included with one event type on Professional ($599) and up to three on Growth ($1,380).",
      },
      {
        q: "What does Abby cost compared to AI-only tools?",
        a: "More, deliberately: roughly $2.76 to $3.29 per human minute and about half that per AI minute, versus $29 to $79 a month flat for AI-only tools. You are paying for real people, a dedicated team, and 20 years of track record.",
      },
    ],
  },
  {
    name: "Dialzara",
    slug: "dialzara",
    tagline: "The cheapest dedicated AI answering service, with SMS and outbound extras.",
    category: "ai-receptionists",
    pricing: "From $29/mo (60 minutes)",
    pros: [
      "Cheapest dedicated AI answering in the category: $29 a month for a 24/7 inbound agent",
      "50+ voice options, the most voice customization of any tool reviewed here, so the agent can sound like your brand",
      "SMS agent comes free with any voice plan: two-way texting that books appointments and qualifies leads alongside the voice calls",
      "Warm call transfer, calendar sync, after-hours rules, and Spanish start at the $99 Pro plan, which is still cheap for what it bundles",
      "A developer API is available on the top Business Elite plan, and the platform also sells outbound voice agents for follow-ups and reactivation",
      "No credit card required for the 7-day trial, and setup takes about 15 minutes",
    ],
    cons: [
      "The $29 plan is bare-bones on purpose: 60 minutes, message-taking and blind transfer only, no warm transfer, no calendar sync, no Spanish",
      "Per-minute billing with the second-highest overage rates in the category ($0.48 a minute on Lite), so busy months can blow past the cheap headline",
      "Minutes do not roll over, so a quiet month is money left on the table",
      "CRM and tool connections mostly run through Zapier; native integrations are thinner than Goodcall's or Smith.ai's",
      "SMS and website chatbot are separate products with separate usage pricing ($19/mo plus per-message for SMS, $39/mo for the chatbot)",
      "Some reviewers note unanswered negative reviews, so check recent Trustpilot feedback before a long commitment",
    ],
    bestFor: "Solo operators and tiny shops that need the cheapest real 24/7 coverage and will grow into the $99 plan",
    url: "https://dialzara.com",
    verdict:
      "Dialzara is the budget play that keeps surprising you upward: $29 gets you in the door, the $99 Pro plan is genuinely competitive with real calendar sync and warm transfer, and the free-bundled SMS agent is a real differentiator. Just budget for the metered minutes.",
    verdictBox:
      "Dialzara is the cheapest dedicated AI answering service in this category at $29 a month, with 50+ voice options and an SMS agent bundled free with every voice plan. The $29 plan is deliberately limited (60 minutes, no calendar sync, no warm transfer), but the $99 Pro plan is a genuine sweet spot: 220 minutes, warm transfer, calendar sync, and after-hours rules. The watch-out is per-minute billing with steep overage: $0.48 a minute on the Lite plan means a busy month can cost more than the plan itself.",
    quickFacts: {
      price: "$29/mo (60 min) / $99 (220) / $199 (500) / $349 (1,000); overage $0.48 to $0.35/min",
      freeTier: "7-day free trial, no credit card required; no free plan",
      setup: "About 15 minutes, no coding; custom prompt engineering on the Plus plan",
    },
    whatIsIt: [
      "Dialzara is an AI receptionist service that answers your inbound calls 24/7, takes messages, routes and transfers calls, books appointments, and captures leads, all in a natural voice you pick from more than 50 options. It also sells AI SMS agents that text with your customers and outbound voice agents that make follow-up and reactivation calls for you.",
      "It is the longest-running vendor in this roundup that sells AI answering this cheaply, and it positions itself as the established budget option: everything works, the basics are cheap, and the advanced features unlock as you climb the tiers.",
    ],
    businessScenarios: [
      {
        title: "Get 24/7 coverage on a startup budget",
        description:
          "You are a solo practitioner and $79 a month feels steep. For $29, Dialzara answers every call, takes detailed messages, and emails you the summary. Your phone is finally covered for the price of a pizza dinner.",
      },
      {
        title: "Warm-transfer the hot ones, message-take the rest",
        description:
          "On the $99 Pro plan, Dialzara answers, figures out the call is a ready-to-book customer, and warm-transfers them to you live with context, while routine price shoppers get their questions answered and a follow-up text. You only interrupt your day for revenue.",
      },
      {
        title: "Follow up by text when the call ends",
        description:
          "The SMS agent is free with your voice plan. A caller asks about availability at 10pm, the voice agent handles it, and the SMS agent follows up the next morning with a booking link. Two channels, one plan.",
      },
      {
        title: "Reactivate old leads without lifting a finger",
        description:
          "Dialzara's outbound voice agents (a separate product from $750 a month) can call your old lead list, offer a tune-up special, and book the takers straight to your calendar. Expensive, but it exists under the same roof.",
      },
      {
        title: "Sound the way you want to sound",
        description:
          "With 50+ voice options, you audition voices until one matches your brand: warm for a spa, crisp for a law office, upbeat for a home-services shop.",
      },
    ],
    howItWorks: [
      "Sign up and start the 7-day trial without a credit card. Pick a voice from 50+ options and configure your greeting, scripts, and call-routing rules; setup typically takes about 15 minutes.",
      "You get a dedicated number and forward your business line to it, or port your number in. Set when the agent answers: 24/7, after hours, or overflow when you are busy.",
      "Train it on your business info, FAQs, and services. On Business Pro ($99) and up, connect Google Calendar or Outlook so the agent books into real availability, and set warm-transfer rules for urgent calls.",
      "The agent answers, records, transcribes, and summarizes every call, and the data lands in your dashboard or your email. Add the free-bundled SMS agent for two-way texting, or Zapier connections to push calls into your other tools.",
    ],
    pricingExplained: [
      "Dialzara sells minutes in four published tiers: Business Lite $29 a month for 60 minutes, Business Pro $99 for 220, Business Plus $199 for 500, and Business Elite $349 for 1,000. Overage drops as you climb: $0.48 a minute on Lite down to $0.35 on Elite. There are no setup fees and no long-term contracts. Companion products are separate: the AI SMS agent is free with any voice plan ($19 a month plus 5 cents a message standalone), the website chatbot is $39 a month standalone, and outbound voice agents start at $750 a month for 1,500 contacts.",
      "The pricing has not moved in about a year, which suggests stability, but it also means the entry plan's 60 minutes is thin: at 3 minutes a call, that is about 20 calls a month.",
    ],
    pricingCatches: [
      "The $29 Lite plan covers 60 minutes and only does message-taking and blind transfer. Warm transfer, calendar sync, after-hours rules, and Spanish all start at the $99 Pro plan, so the real price for a working receptionist is $99, not $29.",
      "Overage at $0.48 a minute on Lite is the second-highest in this roundup. If you regularly exceed your minutes, the next tier up is always cheaper than paying overage.",
      "Minutes do not roll over. A quiet month wastes your allowance, so size the plan to your busiest month, not your average.",
      "The API is only listed on the $349 Business Elite plan, and priority support with an SLA is Elite-only too. Technical buyers on lower tiers should plan on Zapier.",
    ],
    whoShouldGet: [
      "Solo operators and micro-businesses that want the cheapest dedicated AI answering available",
      "Shops that also want two-way SMS with customers without paying for a separate texting tool",
      "Businesses that might later want outbound calling or an API, and like having it under one roof",
    ],
    whoShouldSkip: [
      "Businesses with long calls, where per-minute billing at $0.35 to $0.48 a minute is brutal: Goodcall's unlimited minutes is the antidote",
      "Anyone who needs deep native CRM integrations out of the box rather than via Zapier",
      "Buyers who want published human backup for calls that go sideways: Dialzara is AI-only",
    ],
    comparison: [
      {
        tool: "Dialzara",
        price: "$29/mo (60 min)",
        difference: "Cheapest entry, metered per minute, free SMS agent bundled; long calls cost extra",
      },
      {
        tool: "Goodcall",
        price: "$79/mo per agent (100 callers)",
        difference: "More expensive but unlimited minutes: punishes exactly the long calls Dialzara charges extra for",
      },
      {
        tool: "Rosie",
        price: "$49/mo (250 min)",
        difference: "250 minutes for $49 beats Dialzara's 60 for $29; less feature depth, no SMS agent",
      },
      {
        tool: "24x7 AI (our product)",
        price: "From $49/mo",
        difference: "Our own AI front desk with concierge setup; compare it honestly in our full review",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native scheduling connections include Google Calendar, Microsoft Outlook, and popular booking tools (Calendly, Acuity, Setmore) starting on the Business Pro plan. SMS runs through Dialzara's own agent with built-in 10DLC registration.",
        "Everything else runs through Zapier, where Dialzara has an official app: push new calls to Google Sheets, create HubSpot tickets, build Jobber requests, or update Pipedrive activities. The outbound voice and SMS products also have their own API-style access points.",
      ],
      api: "Dialzara lists API access on the Business Elite plan ($349 a month). Lower tiers should use Zapier or webhooks for custom integrations.",
      privacy: [
        "Dialzara's own security pages claim SOC 2 Type II, HIPAA, GDPR, FINRA, and PCI-DSS compliance, with TLS 1.3 and SRTP in transit, AES-256 at rest, a no-public-model-training policy, and BAA availability for healthcare. If you rely on these claims for regulated calls, verify the SOC 2 report and BAA directly with Dialzara before going live.",
        "Every call is recorded, transcribed, and summarized. Audit logs are claimed to be tamper-proof and real-time. Recording-consent disclosure remains your responsibility under your state's laws.",
      ],
      advancedWorkflowTitle: "Voice plus SMS capture loop",
      advancedWorkflow:
        "Use the voice agent and the free-bundled SMS agent as a pair: the voice agent answers and qualifies, and the SMS agent follows up every qualified lead by text within minutes with a booking link and a short reminder sequence. Connect Dialzara's Zapier trigger to your CRM so every call and text lands on the contact record automatically. Businesses that answer by voice and follow up by text convert far more after-hours leads than voice alone, and here both channels come in one subscription.",
    },
    faqs: [
      {
        q: "What do I actually get for $29 a month?",
        a: "60 talk minutes, 24/7 answering, call recordings, transcripts and summaries, message-taking, and blind transfer. What you do not get: warm transfer, calendar sync, after-hours routing rules, or Spanish. For those you need the $99 Pro plan.",
      },
      {
        q: "How much do extra minutes cost?",
        a: "$0.48 a minute on Lite, $0.45 on Pro, $0.40 on Plus, and $0.35 on Elite. Minutes do not roll over. If you are regularly going over, step up a tier instead of paying overage.",
      },
      {
        q: "Is the SMS agent really free?",
        a: "Yes, with any voice plan: a two-way AI text agent that books and qualifies. Bought standalone it is $19 a month plus 5 cents per message.",
      },
      {
        q: "Can Dialzara book appointments on my calendar?",
        a: "Yes, starting on Business Pro ($99): it syncs with Google Calendar, Outlook, and booking tools to check real availability and book without double-booking.",
      },
      {
        q: "Does Dialzara make outbound calls?",
        a: "Yes, as a separate product: outbound voice agents from $750 a month for 1,500 contacts, for follow-ups, reminders, and lead reactivation. It is priced like a campaign tool, not like the inbound plans.",
      },
      {
        q: "Is there an API?",
        a: "API access is listed on the Business Elite plan ($349 a month). On lower tiers, Zapier is the integration route.",
      },
      {
        q: "Is Dialzara HIPAA compliant?",
        a: "Dialzara's own security pages claim HIPAA compliance with BAA availability, alongside SOC 2 Type II, GDPR, FINRA, and PCI-DSS. Verify the SOC 2 report and BAA directly with Dialzara before routing regulated calls through it.",
      },
      {
        q: "Is there a contract or a setup fee?",
        a: "No setup fees and no long-term contracts. The trial is 7 days with no credit card required.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI chatbots
  // ------------------------------------------------------------------
  {
    name: "Tidio",
    slug: "tidio",
    tagline: "AI chatbot, live chat, and ticketing in one inbox for small businesses.",
    category: "ai-chatbots",
    pricing: "Free plan; paid from $29/mo",
    pros: [
      "Genuinely usable free plan: 50 conversations a month and up to 10 seats, which covers a small site",
      "Billed per conversation, not per seat, so adding your team does not raise the bill",
      "Lyro AI agent answers from your own content (website, docs, help center) and hands off to a human cleanly",
      "Strong ecommerce coverage: deep Shopify and WooCommerce integrations plus order lookups",
      "7-day free trial with no credit card; the account drops back to free if you do not upgrade",
    ],
    cons: [
      "The AI agent (Lyro) is metered and billed separately from the plan, which makes real costs harder to predict",
      "Free plan includes only 50 one-time Lyro conversations, so the AI runs out fast on the free tier",
      "Removing Tidio branding costs extra ($20 a month) on self-serve plans",
      "No verified HIPAA documentation, so healthcare businesses should look elsewhere",
      "Growth pricing climbs in volume steps, so a busy account can cost more than the Plus starting price",
    ],
    bestFor: "Small businesses and ecommerce stores that want an AI chatbot plus live chat in one tool",
    url: "https://www.tidio.com",
    verdict:
      "Tidio is the best all-rounder in this category for small businesses: a real free plan, billing per conversation instead of per seat, and an AI agent that works alongside live chat. Watch the separate Lyro billing so it does not surprise you.",
    verdictBox:
      "Tidio is the most complete small-business chat tool here: live chat, an AI agent called Lyro, ticketing, and automations in one inbox, with a free plan that is actually usable. It bills per conversation, not per seat, so your whole team can share it cheaply. The catch is that the AI agent is metered and billed separately from the plan, which makes real monthly costs harder to predict than the headline price suggests.",
    quickFacts: {
      price: "Free plan; paid from $29/mo (100 conversations)",
      freeTier: "Free forever: 50 conversations a month, up to 10 seats, 50 one-time AI conversations",
      setup: "Install a snippet or Shopify app in minutes; train Lyro on your site and docs",
    },
    whatIsIt: [
      "Tidio is a customer-service chat platform for your website. It puts a chat widget on your site where visitors can talk to an AI agent called Lyro, to you or your team live, or both. Everything lands in one shared inbox: website chats, email, Facebook Messenger, Instagram DMs, and WhatsApp.",
      "You teach Lyro about your business by pointing it at your website, help center, and FAQs. It then answers routine questions on its own (shipping times, return policy, pricing) and hands the tricky conversations to a human. For small businesses, it is effectively a 24/7 front desk for your website without hiring anyone.",
    ],
    businessScenarios: [
      {
        title: "Answer the midnight shipping question",
        description:
          "A shopper is on your site at 1am wondering if an order arrives before Friday. Lyro checks your policy and answers instantly, and the shopper completes the purchase. Without it, they bounce and you read the question next morning too late.",
      },
      {
        title: "Capture the lead that would have left",
        description:
          "A visitor is about to close the tab. A targeted chat message asks what they are looking for, Lyro qualifies them with two or three questions, and their contact details land in your inbox. Your website starts collecting leads while you sleep.",
      },
      {
        title: "Cut the repeat questions for your team",
        description:
          "Your support inbox is full of the same five questions: where is my order, what is your refund policy, do you ship to my city. Lyro answers those from your own content, and your team only handles the exceptions.",
      },
      {
        title: "Recover abandoned carts",
        description:
          "Tidio's Shopify integration lets the bot see cart activity and send a reminder or a discount code. For ecommerce, this turns chat into a small sales tool, not just support.",
      },
      {
        title: "One inbox instead of five tabs",
        description:
          "Website chat, email, Instagram, Messenger, and WhatsApp all show up in one place. Two team members can cover every channel from one screen instead of switching apps all day.",
      },
    ],
    howItWorks: [
      "Add Tidio to your website. Paste a small snippet into your site's code, or install the Shopify or WordPress plugin with one click. The chat widget goes live immediately.",
      "Teach Lyro about your business. Point it at your website pages, help center, and FAQs. It reads your content and starts answering from it. Add custom instructions for tone and for questions it should hand to a human.",
      "Set up your inbox and rules. Connect email, Instagram, Messenger, and WhatsApp so every channel flows into one dashboard. Build simple automations (Flows) like greeting new visitors or asking for an email after hours.",
      "Let it run and review. Lyro resolves conversations on its own and hands off when it is unsure. You review the chat history, fix any wrong answers by updating the source content, and watch your resolution rate improve.",
    ],
    pricingExplained: [
      "Tidio bills by billable conversation, not by seat, and all self-serve plans include up to 10 seats. The free plan covers 50 billable conversations a month. Starter is $29 a month ($24.17 billed annually) for 100 conversations. Growth starts at $59 a month ($49.17 billed annually) for 250 conversations and climbs in steps as volume grows. Plus starts at $300 a month plus usage, and Premium is quote-only with pay-per-resolution billing for large AI deployments.",
      "The AI agent Lyro is metered and billed separately from the plan: from $39 a month ($32.50 billed annually) for 50 Lyro conversations. Annual billing on plans gives roughly two months free. Every paid plan starts with a 7-day free trial that needs no credit card, and the account drops back to the free plan if you do not upgrade.",
    ],
    pricingCatches: [
      "The plan price covers human conversations only. Lyro AI conversations are a separate meter with a separate bill, which is the biggest budgeting gotcha.",
      "Lyro counts a whole conversation once, not per message, but a conversation that Lyro starts and a human finishes can count on both meters.",
      "Growth is priced in volume steps, so a busy Growth account can end up costing more than Plus's $300 starting fee; check the slider on their pricing page.",
      "Removing the Powered by Tidio branding is a $20-a-month add-on on self-serve plans.",
      "The free plan's 50 Lyro conversations are one-time, not monthly, so the AI tap runs dry quickly on free.",
    ],
    whoShouldGet: [
      "Small businesses and ecommerce stores wanting AI chat plus live chat in one inbox",
      "Teams that want predictable billing per conversation rather than per seat",
      "Shopify and WooCommerce stores that can use the order-lookup integrations",
    ],
    whoShouldSkip: [
      "Businesses whose conversations live mostly on Instagram and WhatsApp (a social-first tool like ManyChat fits better)",
      "Healthcare or regulated businesses that need verified HIPAA documentation",
      "Anyone wanting simple flat-rate pricing with AI included, since Lyro is billed separately",
    ],
    comparison: [
      {
        tool: "Tidio",
        price: "Free plan; from $29/mo + separate AI meter",
        difference: "Live chat, AI agent, and ticketing in one inbox; billed per conversation, not per seat",
      },
      {
        tool: "Chatbase",
        price: "$40/mo (700 message credits)",
        difference: "Bot-only, no live chat or ticketing; bills per message credit instead of per conversation",
      },
      {
        tool: "Intercom (Fin)",
        price: "From $29/seat/mo + $0.99 per outcome",
        difference: "Stronger AI resolution and enterprise depth, but seats plus per-outcome billing adds up fast",
      },
      {
        tool: "Drift",
        price: "Sunset announced (see review)",
        difference: "The B2B conversational marketing pioneer is being retired; Tidio is the stable pick now",
      },
    ],
    goingDeeper: {
      integrations: [
        "Direct integrations listed by Tidio: Facebook Messenger, Instagram, WhatsApp, Zendesk, HubSpot, Salesforce, Zoho CRM, Shopify, WooCommerce, WordPress, Klaviyo, Mailchimp, ActiveCampaign, Google Analytics (GA4), MailerLite, Brevo, Judge.me, Pipedrive, plus Slack on Plus and Premium. Everything else runs through Zapier.",
        "The ecommerce integrations are the deepest: Lyro can look up order status and customer details from Shopify and WooCommerce, so it answers where is my order questions without a human.",
      ],
      api: "Tidio publishes a developer API with API-key authentication, plus webhooks and a widget SDK for customizing the chat widget. Full OpenAPI access is listed on Plus and Premium, so deep custom builds are aimed at larger accounts.",
      privacy: [
        "Tidio's security documentation reports a completed SOC 2 Type II examination, AES-256 encryption at rest and TLS 1.2+ in transit, two-factor authentication, and annual external penetration tests.",
        "It also documents GDPR and CCPA privacy controls, EU data hosting, DPA and standard contractual clauses, and Data Privacy Framework participation.",
        "What is not verified: we found no official HIPAA compliance documentation from Tidio, so do not use it for protected health information without direct written confirmation.",
      ],
      advancedWorkflowTitle: "After-hours lead machine with CRM sync",
      advancedWorkflow:
        "Build a Flow that greets after-hours visitors, has Lyro qualify them (what do you need, budget range), and captures their email. Connect Tidio to HubSpot or Salesforce via Zapier so qualified chats create contacts automatically, and set Slack alerts only for chats Lyro marked hot. You wake up to a sorted lead list instead of a pile of raw chat transcripts.",
    },
    faqs: [
      {
        q: "Is Tidio really free?",
        a: "Yes, the free plan is free forever: 50 billable conversations a month, up to 10 seats, live chat, and ticketing. The catch is that the AI agent gets only 50 one-time conversations on free, so you will pay once you want real AI volume.",
      },
      {
        q: "How much does the Lyro AI agent cost?",
        a: "Lyro is billed separately from your plan: from $39 a month ($32.50 billed annually) for 50 AI conversations, then per-conversation from there. This is the number most buyers miss on the pricing page.",
      },
      {
        q: "Does Tidio charge per agent?",
        a: "No. Tidio charges by billable conversation, and Free, Starter, and Growth all include up to 10 seats. Plus plans allow a custom seat count.",
      },
      {
        q: "What happens when Lyro cannot answer?",
        a: "It hands the conversation to a human in your shared inbox, with the full transcript attached. You can also route failed AI conversations into tickets in Salesforce or Zendesk.",
      },
      {
        q: "Which channels does Tidio cover?",
        a: "Website chat, email, Facebook Messenger, Instagram DMs, and WhatsApp, all in one inbox. It does not replace a phone system.",
      },
      {
        q: "Can I remove the Powered by Tidio branding?",
        a: "Yes, for $20 a month on self-serve plans ($16.67 billed annually). Custom branding is included on Plus.",
      },
      {
        q: "Is Tidio suitable for an online store?",
        a: "It is one of the stronger picks for ecommerce: the Shopify and WooCommerce integrations let the AI look up order status, and you can build cart-recovery automations without code.",
      },
    ],
  },
  {
    name: "Chatbase",
    slug: "chatbase",
    tagline: "Train an AI chatbot on your docs and embed it anywhere in an afternoon.",
    category: "ai-chatbots",
    pricing: "Free plan; paid from $40/mo",
    pros: [
      "Fastest path from your documents to a working bot: connect your website, PDFs, or help center and embed in an afternoon",
      "Free plan lets you test a real agent before paying anything",
      "Picks the AI model for each reply and supports advanced models (GPT, Claude) without you managing API keys",
      "Grown into a real platform: built-in helpdesk, voice and phone agents, and outbound campaigns on higher tiers",
      "Never trains AI models on your data, per its own privacy policy",
    ],
    cons: [
      "Message-credit billing is hard to forecast: each reply costs 1 to 5 credits depending on the model, and AI actions roughly double the spend",
      "Extra credits cost $40 per 1,000, which reviewers call steep compared with rivals",
      "Only one AI agent per plan; extra agents cost $25 a month each",
      "API access, the helpdesk, and voice only start on the $150 Standard plan",
      "Removing the Powered by Chatbase badge costs $99 a month",
    ],
    bestFor: "Teams that want a train-on-your-docs AI bot embedded on their site fast",
    url: "https://www.chatbase.co",
    verdict:
      "Chatbase is the quickest way to turn your docs into a working AI chatbot. The credit system makes costs unpredictable though, and the features that matter (API, voice, helpdesk) only start at $150 a month.",
    verdictBox:
      "Chatbase made train a chatbot on your docs and embed it a one-afternoon job: connect your site or PDFs, and the bot answers visitors in your words. The catch is the billing: every plan buys a pool of message credits, and each reply spends 1 to 5 credits depending on the AI model, so a busy month or a heavy model burns through the allowance fast. Extra credits cost $40 per 1,000, and the API, helpdesk, and voice features are locked behind the $150 plan.",
    quickFacts: {
      price: "Free plan; paid from $40/mo (700 message credits)",
      freeTier: "Free: 50 message credits a month, 1 agent (deleted after 14 days of inactivity)",
      setup: "Point it at your website or upload files; embed with a snippet, no code needed",
    },
    whatIsIt: [
      "Chatbase is an AI chatbot builder. You feed it your knowledge: your website, help docs, PDFs, or plain Q&A pairs. It builds an AI agent that answers customer questions in natural language and you embed it on your website or connect it to WhatsApp, Messenger, Instagram, or Slack.",
      "It is popular with small teams that want a smart FAQ bot without building anything custom. On higher plans it adds a built-in helpdesk, voice and phone agents, and AI actions that let the bot do things like look up an order or book a meeting, not just answer questions.",
    ],
    businessScenarios: [
      {
        title: "Turn your FAQ page into a conversation",
        description:
          "Your pricing and policy pages get read by almost nobody. Chatbase's bot answers what's included in the Pro plan or do you offer refunds instantly, in chat, instead of making visitors hunt through pages.",
      },
      {
        title: "Support in your customer's language",
        description:
          "The bot replies in the visitor's language automatically. A small business with international customers gets multilingual support without hiring for it.",
      },
      {
        title: "Take support calls with an AI voice agent",
        description:
          "On Standard and up, Chatbase adds voice and phone: the same knowledge base that powers your chat can answer inbound calls. One brain for both chat and phone.",
      },
      {
        title: "Let the bot take action, not just answer",
        description:
          "With AI actions, the bot can check an order status, schedule a Calendly meeting, or create a support ticket. It stops being a FAQ machine and starts doing small jobs.",
      },
      {
        title: "Capture leads while answering questions",
        description:
          "Ask for the visitor's email when the bot cannot resolve something, or proactively after it helps. Conversations become a lead list you can export or sync to your CRM.",
      },
    ],
    howItWorks: [
      "Create an agent and add your knowledge. Paste your website URL so Chatbase imports your pages, or upload PDFs, documents, or a help center. It shows you the character count so you know what fits your plan.",
      "Pick the AI model and behavior. Choose how the bot should answer, set the tone, add fallback replies, and decide what happens when it does not know something.",
      "Embed it or connect channels. Drop the JavaScript snippet on your site, or connect WhatsApp, Messenger, Instagram, or Slack. On Standard and up, you can also wire it to your helpdesk or turn on voice.",
      "Watch usage and tune. The dashboard shows conversations, credit usage, and unanswered questions. Add the questions it missed to your knowledge base so it gets smarter over time.",
    ],
    pricingExplained: [
      "Chatbase sells plans that include a monthly pool of message credits: Free ($0, 50 credits), Hobby ($40 a month, 700 credits), Standard ($150 a month, 4,000 credits), Pro ($500 a month, 15,000 credits), and custom Enterprise. Yearly billing is 20% cheaper. Every plan includes one AI agent; extra agents are $25 a month each. Paid plans start with a 7-day trial.",
      "Credits are the whole game. Each AI reply spends 1 to 5 credits depending on the model it uses, and turning on AI actions roughly doubles the credits per reply. So Hobby's 700 credits might mean 700 simple replies or far fewer if you use heavy models. Training data is also capped per plan: 1 MB on Free, 10 MB on Hobby, 20 MB on Standard, 40 MB on Pro.",
    ],
    pricingCatches: [
      "Extra credits cost $40 per 1,000 with auto-recharge, which reviewers flag as expensive. A traffic spike can burn through your allowance in days, so watch the usage screen.",
      "The free plan deletes your agent after 14 days of inactivity, so it is a trial, not a home for a real bot.",
      "API access, the helpdesk, voice agents, and advanced integrations (Stripe, Zendesk) only start on Standard at $150 a month. Hobby at $40 has no API.",
      "Removing the Powered by Chatbase badge is a $99-a-month add-on.",
      "Every tier includes just one agent by default. A separate bot for sales and another for support costs extra.",
    ],
    whoShouldGet: [
      "Teams that want a working bot trained on their docs with minimum effort",
      "Businesses that need chat plus voice agents from the same knowledge base",
      "Anyone who wants to test an AI bot on a free plan before committing",
    ],
    whoShouldSkip: [
      "Teams that need predictable billing (the credit model punishes heavy models and traffic spikes)",
      "Businesses that need an API or helpdesk on a budget (both start at $150 a month)",
      "Anyone who needs live human chat in the same tool (Chatbase is bot-first; pair it with a separate inbox or use the built-in helpdesk)",
    ],
    comparison: [
      {
        tool: "Chatbase",
        price: "From $40/mo (700 message credits)",
        difference: "Fastest train-on-docs setup; credit billing is the least predictable of the five",
      },
      {
        tool: "Tidio",
        price: "Free plan; from $29/mo",
        difference: "Adds live chat and ticketing in one inbox; bills per conversation, easier to forecast",
      },
      {
        tool: "Intercom (Fin)",
        price: "From $29/seat/mo + $0.99 per outcome",
        difference: "Bills per resolved outcome instead of per reply; stronger for support-heavy teams, pricier for small ones",
      },
      {
        tool: "ManyChat",
        price: "From $14/mo",
        difference: "Cheaper, but it is a flow-based social DM tool, not a train-on-docs website bot",
      },
    ],
    goingDeeper: {
      integrations: [
        "Messaging channels: WhatsApp, Messenger, Instagram, Slack. Helpdesks: Zendesk, Salesforce, Intercom, HubSpot, Zoho Desk, Freshdesk, Help Scout, Gorgias. Commerce and tools: Shopify, Stripe, WordPress, Zapier, Make.com, Calendly, Twilio, Odoo. Hobby includes basic integrations; advanced integrations (Stripe, Zendesk named as examples) start on Standard.",
        "The Zendesk integration lets the agent reply to tickets or draft replies for a human, so Chatbase can sit inside an existing support desk rather than replacing it.",
      ],
      api: "Chatbase publishes a REST API plus webhooks and a JavaScript embed API, but API access starts on the Standard plan ($150 a month). The $40 Hobby plan has no API, so builders who want programmatic control should price Standard as the real entry point.",
      privacy: [
        "Per Chatbase's own privacy policy and security page: the company states it is SOC 2 Type II compliant and GDPR compliant, encrypts data at rest and in transit, and never uses customer data to train AI models.",
        "Data is stored on AWS infrastructure in the US (us-east-1). Model providers (OpenAI, Anthropic, Google) receive conversation data to generate replies, but Chatbase says it does not opt into their data-sharing programs, so they cannot use it for training.",
        "On deletion: Chatbase says it deletes customer data, including conversation content and knowledge sources, within 30 days of a written deletion request or contract termination.",
      ],
      advancedWorkflowTitle: "Ticket-deflecting helpdesk assistant",
      advancedWorkflow:
        "Connect Chatbase to Zendesk on the Standard plan and let it draft replies for common tickets instead of auto-replying. Your team reviews each draft with one click to send. Over a month, tag which drafts were sent unchanged; those become candidates for full auto-reply. You get the safety of human review while measuring exactly how much of your ticket volume the bot could absorb.",
    },
    faqs: [
      {
        q: "What is a message credit, really?",
        a: "One credit is roughly one AI reply on the lightest model. Heavier models cost more: up to 5 credits per reply, and AI actions roughly double the spend. So a plan's credit pool is not a fixed number of conversations.",
      },
      {
        q: "What happens when I run out of credits?",
        a: "With auto-recharge on, Chatbase adds 1,000 credits for $40 and the bot keeps running. Without it, the bot stops replying until the next month or until you buy more. Watch the usage screen in your first month.",
      },
      {
        q: "Can I use my own OpenAI API key?",
        a: "Chatbase uses its own model access, so you do not need API keys. You also cannot bring your own key to change the credit math.",
      },
      {
        q: "Does Chatbase work on WhatsApp and Instagram?",
        a: "Yes, it lists WhatsApp, Messenger, Instagram, and Slack as channels, plus a website embed. Voice and phone agents start on Standard.",
      },
      {
        q: "Will my data train AI models?",
        a: "No, per Chatbase's own policy. It uses retrieval-based generation and says neither it nor its model providers use your data for training.",
      },
      {
        q: "Can it hand off to a human?",
        a: "Yes. On Standard and up, the built-in helpdesk and integrations like Zendesk let unresolved conversations land in front of a person with the full transcript.",
      },
      {
        q: "Is the free plan enough for a real business?",
        a: "No. Fifty credits a month is a test drive, and the agent is deleted after 14 days of inactivity. Treat free as a trial and budget at least Hobby for anything real.",
      },
    ],
  },
  {
    name: "Intercom (Fin)",
    slug: "intercom-fin",
    tagline: "Fin is Intercom's AI agent that resolves support questions, billed per result.",
    category: "ai-chatbots",
    pricing: "Seats from $29/seat/mo + $0.99 per outcome",
    pros: [
      "Pay per outcome, not per message: you are charged only when Fin delivers a resolution, a handoff, or a qualification, and at most once per conversation",
      "One of the most capable AI support agents: it reads your help center and docs, follows multi-step procedures, and can take actions in connected systems",
      "Works across chat, email, WhatsApp, SMS, and phone, and can run on top of other helpdesks (Zendesk, Salesforce, HubSpot) without Intercom seats",
      "14-day free trial with unlimited outcomes, generous enough to measure real resolution rates",
      "Vendor-documented compliance: SOC 2 Type II, HIPAA, ISO 27001/27018/27701, plus GDPR and CCPA",
    ],
    cons: [
      "Total cost stacks fast: per-seat plans (from $29 per seat per month) plus $0.99 per outcome plus add-ons like Copilot ($29 per teammate)",
      "The per-outcome bill is unpredictable month to month; a product launch or traffic spike can multiply it",
      "Overkill for a solo business: the power shows only when you already have a help center and support volume",
      "Sales qualifications cost $9.99 each, a steep per-lead price for small teams",
      "Setup takes real work: Fin is only as good as the help center content and procedures you give it",
    ],
    bestFor: "Teams already on Intercom, or support-heavy businesses that want top-tier AI resolution",
    url: "https://www.intercom.com",
    verdict:
      "Fin is the strongest AI support agent in this category, and the pay-per-outcome model is honest: no result, no charge. But the full Intercom bill (seats plus outcomes plus add-ons) makes it a poor fit for very small teams.",
    verdictBox:
      "Fin is Intercom's AI agent, and it is the most capable support bot in this category: it answers from your help center and policies, follows multi-step procedures like processing a refund or updating an account, and works across chat, email, WhatsApp, SMS, and phone. You pay $0.99 only when it achieves an outcome (a resolution, a procedure handoff, or a disqualification), never more than once per conversation. The catch is the total bill: Intercom seat plans start at $29 per seat per month on top, add-ons stack up, and outcome volume is hard to predict, so small teams should model the cost before committing.",
    quickFacts: {
      price: "$0.99 per outcome, on top of seat plans from $29/seat/mo",
      freeTier: "No free plan; 14-day free trial with unlimited outcomes",
      setup: "Moderate: needs a decent help center; Fin is only as good as your content",
    },
    whatIsIt: [
      "Fin is the AI agent built by Intercom, the customer-service platform. Where a classic chatbot follows scripts, Fin reads your help center articles, support docs, and policies, and then resolves customer questions end to end: answering, taking actions, and escalating to a human when it cannot confidently help.",
      "You can use Fin inside Intercom's full helpdesk (shared inbox, ticketing, messenger) or bolt it onto an existing helpdesk like Salesforce, HubSpot, or Zendesk, where it runs without Intercom seats. Either way, you are buying AI resolution, not just a chat widget.",
    ],
    businessScenarios: [
      {
        title: "Deflect the Monday morning ticket pile",
        description:
          "After a weekend, your inbox has 200 tickets and half are password resets, plan questions, and policy lookups. Fin resolves the routine half from your help center before your team logs in, and they start the day on the hard cases.",
      },
      {
        title: "Answer support email, not just chat",
        description:
          "Fin works on email as well as live chat, so the same AI that deflects website chats also clears the repetitive email backlog your team dreads.",
      },
      {
        title: "Qualify sales leads at 2am",
        description:
          "A prospect asks pricing questions on your site at night. Fin answers, checks them against your qualification criteria, and routes the good ones to sales. A qualification costs $9.99, but only when the prospect actually qualifies.",
      },
      {
        title: "Handle refunds without a human touching them",
        description:
          "You write a procedure in plain language: verify identity, check the order, process refunds under a set amount. Fin follows it step by step and hands off with a summary when it cannot complete it.",
      },
      {
        title: "Keep Fin when you change helpdesks",
        description:
          "If your team later moves to Salesforce or Zendesk, Fin can run on top of the new desk too, so the AI investment is not tied to one inbox.",
      },
    ],
    howItWorks: [
      "Connect your knowledge. Point Fin at your help center, public URLs, documents, and snippets. Fin answers only from approved content, which keeps it from inventing policy.",
      "Set guidance and procedures. Write plain-language rules for tone, what Fin may promise, and when to escalate. Then define procedures for multi-step jobs like refunds, cancellations, account changes, and lead qualification.",
      "Turn it on per channel. Enable Fin on chat, email, WhatsApp, SMS, or phone, and set how much of your volume it should attempt before handing off.",
      "Measure outcomes and improve content. The dashboard shows resolutions, handoffs, and the questions Fin could not answer. Fix the gaps in your help center and Fin's resolution rate climbs.",
    ],
    pricingExplained: [
      "Fin is billed per outcome: $0.99 for a resolution, a procedure handoff, or a disqualification, and $9.99 for a sales qualification. You are charged at most once per conversation, no matter how many messages or actions happen inside it. If the customer asks for a human immediately, or Fin cannot answer, there is no charge, and a reopened conversation refunds the outcome. On the standalone (non-Intercom) plan there is a 50-outcome monthly minimum, about $49.50 a month.",
      "On top of that, Intercom seat plans apply if you use the full platform: Essential at $29 per seat per month, Advanced at $85, Expert at $132, all billed annually (monthly billing runs higher). Add-ons stack: Copilot, the AI assistant for your human agents, is $29 per teammate per month, and proactive messaging starts at $99 a month. There is a 14-day free trial with unlimited outcomes.",
    ],
    pricingCatches: [
      "The $0.99 headline is not the bill. Add seats, Copilot, and proactive messaging, and a modest team can spend several hundred dollars a month before outcomes.",
      "Outcome volume is usage-based: a busy month, a launch, or an incident can multiply the Fin line item, which finance teams find hard to budget.",
      "Qualifications cost ten times a resolution: $9.99 each. Sales teams should model qualification volume carefully.",
      "Fin needs fuel: if your help center is thin, resolution rates are low and you pay for handoffs instead. Budget time, not just money, for content.",
      "Fin Voice (phone) is sold on a custom plan through sales for select customers, not as a self-serve add-on.",
    ],
    whoShouldGet: [
      "Teams already on Intercom that want to automate a real share of support",
      "Support-heavy businesses with a decent help center and hundreds of conversations a month",
      "Companies on Zendesk, Salesforce, or HubSpot that want Fin's AI without switching helpdesks",
    ],
    whoShouldSkip: [
      "Solo businesses and tiny teams (seats plus outcomes will cost more than the problem)",
      "Anyone who needs a fixed, predictable monthly bill",
      "Businesses with no written help content yet (write the docs first, then buy the AI)",
    ],
    comparison: [
      {
        tool: "Intercom (Fin)",
        price: "From $29/seat/mo + $0.99/outcome",
        difference: "Strongest AI resolution and enterprise compliance; the total bill is the highest of the five",
      },
      {
        tool: "Tidio",
        price: "Free plan; from $29/mo",
        difference: "Far cheaper for small teams and includes live chat; AI is metered per conversation, not per outcome",
      },
      {
        tool: "Chatbase",
        price: "From $40/mo (700 message credits)",
        difference: "Simpler train-on-docs bot at a lower entry price; bills per reply (credit), not per result",
      },
      {
        tool: "Drift",
        price: "Sunset announced (see review)",
        difference: "Was the B2B sales-chat rival to Fin; it is being retired, so do not build on it now",
      },
    ],
    goingDeeper: {
      integrations: [
        "Fin connects to external systems through Intercom's app ecosystem, its API, data connectors, and MCP (Model Context Protocol) support, so it can read and write to tools like your CRM, billing system, or order database while following a procedure.",
        "Channels are broad: Intercom Messenger (chat), email, WhatsApp, SMS, Slack, and phone via Fin Voice. On other helpdesks, Fin runs inside Salesforce, HubSpot, Zendesk, and Freshdesk.",
      ],
      api: "Yes. Intercom publishes a well-documented REST API and webhooks, and Fin can call external APIs as part of procedures (for example, checking an order or updating an account). Developer access is a first-class part of the platform, not an afterthought.",
      privacy: [
        "From Intercom's own security page: Intercom and Fin hold SOC 2 Type II and HIPAA compliance, ISO 27001, ISO 27018, ISO 27701, and ISO 42001 certifications, and Fin is also AIUC-1 certified. Documentation is self-serve in its Trust Center.",
        "Intercom states it complies with GDPR and CCPA, encrypts data in transit (TLS) and at rest (AES-256), and offers European data hosting (AWS Dublin region).",
        "Fin only answers from content you approve, and Intercom states customer data is not used to train public foundation models; LLM providers operate under zero-retention agreements per its compliance documentation.",
      ],
      advancedWorkflowTitle: "Refund procedure with guardrails",
      advancedWorkflow:
        "Write a Fin procedure: verify the customer's identity from the order email, check the purchase date against your refund window, process refunds under $100 automatically, and escalate anything above that with a summary for a human. Connect your billing system so Fin can actually issue the refund. You automate the refund queue while keeping a human on every exception, and you only pay $0.99 per completed outcome.",
    },
    faqs: [
      {
        q: "What exactly counts as a billable outcome?",
        a: "A resolution (the customer got their answer and asked for nothing more), a procedure handoff (Fin completed a workflow that ends with a human), or a disqualification in sales flows. Qualifications cost $9.99. You are charged at most once per conversation, and if the customer immediately asks for a human or Fin cannot answer, there is no charge.",
      },
      {
        q: "Do I have to use Intercom's helpdesk to use Fin?",
        a: "No. Fin is also sold standalone on top of Salesforce, HubSpot, Zendesk, and Freshdesk, with no seat costs, just the per-outcome price and a 50-outcome monthly minimum.",
      },
      {
        q: "How much will Fin actually cost my business?",
        a: "Model it: take your monthly conversation volume, estimate what share Fin resolves (the 14-day free trial with unlimited outcomes is the honest way to measure), multiply by $0.99, then add your seat plan. Three seats on Advanced plus 1,000 outcomes is about $255 plus $990, roughly $1,245 a month.",
      },
      {
        q: "What if Fin gives a wrong answer?",
        a: "Fin answers only from content you approve, and you can set confidence thresholds and escalation rules. If a resolved conversation is reopened, the outcome charge is refunded.",
      },
      {
        q: "Does Fin work on the phone?",
        a: "Yes, via Fin Voice, but it is sold on a custom plan through sales for select customers rather than self-serve. Chat, email, WhatsApp, and SMS are the standard channels.",
      },
      {
        q: "Is Fin good for a very small business?",
        a: "Usually not. If you get a few dozen chats a month and have no help center, Tidio's free plan or Chatbase's $40 plan solves the same problem for a fraction of the cost.",
      },
    ],
  },
  {
    name: "Drift",
    slug: "drift",
    tagline: "The B2B conversational marketing pioneer; being retired, do not buy.",
    category: "ai-chatbots",
    pricing: "Sunset announced; was from ~$2,500/mo",
    pros: [
      "Pioneered conversational marketing: chatbots plus live chat plus meeting booking built for B2B sales teams",
      "Playbook-based routing and lead qualification were battle-tested by thousands of B2B companies",
      "Strong Salesforce alignment for account-based marketing workflows",
    ],
    cons: [
      "The product is being shut down. Do not buy Drift for a new deployment in 2026",
      "No new features are being developed; the standalone product is in maintenance mode",
      "Even before the sunset it was expensive (from about $2,500 a month) and sold through annual contracts",
      "Data and integrations have an end date, so any remaining investment goes toward migration, not growth",
    ],
    bestFor: "Existing Drift customers planning their migration, not new buyers",
    url: "https://www.drift.com",
    verdict:
      "Drift is being retired. If you are not already a customer, skip it entirely; if you are, plan your migration now rather than waiting for the end date.",
    verdictBox:
      "Do not buy Drift. Clari + Salesloft announced the gradual sunset of Drift as a standalone product in March 2026 and named 1mind as the successor, with the product's access ending per customer contracts (Salesloft's FAQ cites January 31, 2027). No new features are being built, and pricing was enterprise-grade anyway (about $2,500 a month to start). This entry exists so you do not waste a sales call discovering all this. If you are already on Drift, use the remaining time to audit your workflows and pick a replacement; the alternatives below are where to look.",
    quickFacts: {
      price: "Was from ~$2,500/mo; product being retired",
      freeTier: "No free plan; only legacy contracts remain",
      setup: "Not applicable for new buyers; legacy setup took weeks with sales assistance",
    },
    whatIsIt: [
      "Drift was the tool that created conversational marketing: a chat widget on B2B websites that qualified visitors with chatbots (playbooks), routed good leads to sales reps, and booked meetings straight from chat.",
      "After Salesloft acquired Drift in 2024 and merged with Clari, the owners decided to fold Drift's capabilities into the broader revenue platform and retire the standalone product. Drift's customers are being steered toward 1mind under an exclusive referral agreement.",
    ],
    businessScenarios: [
      {
        title: "If you are already a Drift customer: audit your workflows",
        description:
          "List every active playbook, routing rule, and meeting-booking flow, plus what each depends on in your CRM. Migration vendors recommend running the replacement in parallel for 60 to 90 days before turning Drift off.",
      },
      {
        title: "If you are shopping: do not start here",
        description:
          "Whatever you read about Drift's playbooks applies to its replacements. Evaluate Qualified, Intercom Fin, or Tidio instead, depending on your size and stack.",
      },
      {
        title: "Export your data before access closes",
        description:
          "Salesloft says chat data stays available until your contract ends or the sunset date, then goes offline and is deleted months later. Plan a full data export before that.",
      },
    ],
    howItWorks: [
      "This section is for current customers only: audit every active chatflow, bot, routing rule, and meeting-booking setup.",
      "Map each workflow's dependencies: which CRM fields, routing rules, and integrations it touches.",
      "Evaluate replacements against that audit (Qualified for Salesforce-native B2B, Intercom Fin for support-plus-sales, Tidio for smaller budgets), not just the vendor's recommended successor.",
      "Run the replacement in parallel for 60 to 90 days on your highest-traffic flows before deactivating Drift, and export all conversation data before access closes.",
    ],
    pricingExplained: [
      "Drift never published full pricing; it was sold through sales on annual contracts. Reported starting prices were about $2,500 a month for Premium, with Advanced and Enterprise on custom quotes that commonly ran to $40,000 to $60,000+ a year. Seat fees and implementation added on top.",
      "For new buyers this is history, not a quote: no one should be signing a Drift contract in 2026.",
    ],
    pricingCatches: [
      "Annual contracts were required, so switching cost was high even before the sunset.",
      "The base license was only part of the bill: seats, implementation fees, and SDR staffing to answer chats added up.",
      "Enterprise quotes varied widely, so public figures were always approximate.",
    ],
    whoShouldGet: [
      "Existing Drift customers who need to plan a migration",
    ],
    whoShouldSkip: [
      "Everyone shopping for a chatbot in 2026: buy from a vendor with a future",
      "Small businesses: Drift was enterprise-priced and enterprise-built even before the sunset",
      "Teams that want self-serve signup (Drift was sales-led with annual contracts)",
    ],
    comparison: [
      {
        tool: "Drift",
        price: "Sunset announced; was ~$2,500/mo",
        difference: "Being retired; listed here so you do not waste time evaluating it",
      },
      {
        tool: "Qualified",
        price: "From ~$3,500/mo",
        difference: "The closest B2B-native successor for Salesforce shops, with an AI agent called Piper",
      },
      {
        tool: "Intercom (Fin)",
        price: "From $29/seat/mo + $0.99/outcome",
        difference: "AI agent for support and sales conversations, still actively developed and improving",
      },
      {
        tool: "Tidio",
        price: "Free plan; from $29/mo",
        difference: "The budget-stable pick: chat plus AI plus live chat without the enterprise contract",
      },
    ],
    goingDeeper: {
      integrations: [
        "Drift's integrations centered on Salesforce, Marketo, HubSpot, and sales calendars for routing and meeting booking. These integrations end with the product, so map which ones your replacement must keep.",
      ],
      privacy: [
        "We could not verify current compliance documentation for Drift during the sunset, so do not assume SOC 2 or GDPR status for new evaluations. Treat the product as legacy infrastructure.",
        "If you are migrating, confirm in writing how long your conversation data stays available and when it is deleted after contract end.",
      ],
      advancedWorkflowTitle: "Migration audit, not a workflow",
      advancedWorkflow:
        "Export every playbook and bot, record each routing rule and CRM dependency, and export all conversation history before access closes. Then stand up the replacement on one high-traffic page first, run it alongside Drift for 60 to 90 days, and compare booked meetings per visitor before cutting over.",
    },
    faqs: [
      {
        q: "Is Drift shutting down?",
        a: "Yes. Clari + Salesloft announced the gradual sunset of Drift as a standalone product in March 2026 and named 1mind as the successor. Salesloft's FAQ says the website chat widget, Drift Email, and custom API integrations stop on January 31, 2027 or when your contract ends, whichever comes first.",
      },
      {
        q: "Can I still buy Drift?",
        a: "You should not. There are no new features, no public pricing for new buyers, and an end date. Any vendor still selling you Drift in 2026 deserves a hard question.",
      },
      {
        q: "What should Drift customers switch to?",
        a: "It depends on your stack: Qualified if you are a Salesforce shop doing B2B sales chat, Intercom Fin if you want AI across support and sales, Tidio for smaller budgets. Do not default to the vendor's recommended successor without evaluating.",
      },
      {
        q: "What happens to my Drift data?",
        a: "Per Salesloft's sunset FAQ, data stays online until your contract ends or January 31, 2027, stays offline for a few months, and is deleted on May 1, 2027. Export everything before then.",
      },
    ],
  },
  {
    name: "ManyChat",
    slug: "manychat",
    tagline: "Automate Instagram DMs, Messenger, and WhatsApp with visual flows.",
    category: "ai-chatbots",
    pricing: "Free plan; paid from $14/mo",
    pros: [
      "The best tool here for social DMs: Instagram, Messenger, WhatsApp, TikTok, and Telegram from one dashboard",
      "Cheapest real entry in the category: $14 a month covers 250 contacts, and paid plans include a 14-day trial",
      "Visual flow builder anyone can use: comment triggers, story replies, and keyword shortcuts need no code",
      "Official Meta Business Partner using the official Instagram and Messenger APIs, so it is safe for your account",
      "Huge template library and community: most small businesses find a ready-made flow for their exact use case",
    ],
    cons: [
      "Not a website chatbot: there is no website chat widget, so pair it with a site tool if your visitors come from Google",
      "Bills by active contact, so a viral post or ad spike pushes you up a tier automatically",
      "The free plan was cut to 25 active contacts in March 2026, which is a demo, not a working tier",
      "WhatsApp and SMS carry Meta and carrier fees on top of the subscription",
      "AI replies are an add-on and flow-based thinking, not a train-on-docs agent: complex questions still need a human or a webhook",
    ],
    bestFor: "Creators and small brands that sell through Instagram DMs and WhatsApp",
    url: "https://manychat.com",
    verdict:
      "ManyChat is the pick when your customers live in Instagram DMs and WhatsApp rather than on your website. It is cheap to start and easy to build with, but remember it is a flow tool, not a website chatbot, and the bill grows with your contact list.",
    verdictBox:
      "ManyChat automates conversations where social-first businesses actually sell: Instagram DMs, Facebook Messenger, WhatsApp, TikTok, and Telegram. You build visual flows (when someone comments LINK on your post, send them the download link and ask for their email) without any code. Paid plans start at $14 a month and there is a 14-day trial. The catches: it is billed per active contact, so success raises your bill; WhatsApp adds Meta's per-conversation fees; and there is no website chat at all, so if your customers find you on Google, you need a website tool too.",
    quickFacts: {
      price: "Free plan; paid from $14/mo (250 active contacts)",
      freeTier: "Free: 25 active contacts, 2 channels, 4 automations, ManyChat branding",
      setup: "Connect your Instagram or Facebook account and pick a template; most flows take under an hour",
    },
    whatIsIt: [
      "ManyChat is a chat-automation platform for social messaging. Instead of a website widget, it lives in the DMs your customers already use: Instagram, Facebook Messenger, WhatsApp, TikTok, and Telegram, plus SMS and email on paid plans.",
      "You build automations with a drag-and-drop flow builder: a trigger (a comment keyword, a story reply, an ad click) starts a conversation that delivers a lead magnet, answers FAQs, collects an email, or hands off to you. For creators and social-first small businesses, it is the closest thing to a salesperson inside your DMs.",
    ],
    businessScenarios: [
      {
        title: "Turn comments into customers",
        description:
          "You post a Reel about your new product and say comment GUIDE for the free checklist. Everyone who comments gets the guide by DM automatically, plus a follow-up asking for their email. One post becomes a lead generator that runs itself.",
      },
      {
        title: "Answer DM questions while you sleep",
        description:
          "Price, hours, booking links, shipping: the same five questions fill your Instagram inbox daily. A flow answers them instantly and tags anyone who needs a real reply for you in the morning.",
      },
      {
        title: "Run WhatsApp broadcasts that people actually read",
        description:
          "Send a new-arrivals or restock message to opted-in WhatsApp contacts. Open rates on chat beat email by a wide margin, and replies come straight back into your inbox.",
      },
      {
        title: "Recover the followers your ads paid for",
        description:
          "Click-to-message ads drop people straight into a ManyChat flow that qualifies them and books a call or sends a product link, instead of a landing page they bounce from.",
      },
      {
        title: "Collect emails without a website",
        description:
          "Many creators and local businesses have no real website. ManyChat flows collect names, emails, and phone numbers inside the DM and sync them to your email tool, so your list lives somewhere you own.",
      },
    ],
    howItWorks: [
      "Connect your accounts. Link your Instagram, Facebook Page, or WhatsApp number through the official login. ManyChat is a Meta Business Partner, so it uses the official APIs and never asks for your password.",
      "Pick a trigger and build the flow. Start from a template: comment-to-DM, story mention replies, keyword shortcuts, or a welcome message. Drag blocks to ask questions, send links, and tag contacts.",
      "Add your follow-ups and integrations. Sync collected emails to your email platform, send new leads to Google Sheets or your CRM via Zapier, and set the message windows Meta allows (free-form replies are limited to 24 hours after the customer's last message).",
      "Watch contacts and upgrade as you grow. Your plan is billed by active contacts (people who interacted with your automation that month). When you pass your tier, overage fees apply, so check the contact count after big campaigns.",
    ],
    pricingExplained: [
      "ManyChat rebuilt its pricing in March 2026 around active contacts: Free ($0, 25 contacts), Essential ($14 a month billed annually, 250 contacts), Pro ($29 billed annually, 2,500 contacts), Business ($69 billed annually, 7,500 contacts), and Advanced ($139 billed annually, 25,000 contacts). Monthly billing costs more ($17, $39, $99, and $199). Paid plans offer a 14-day free trial.",
      "An active contact is anyone who interacts with your automation in a month, so your bill tracks your audience activity, not your message count. AI features start on Pro, and AI replies cost extra (an AI add-on at $29 a month on Pro). When you exceed your tier, per-contact overage fees apply automatically.",
    ],
    pricingCatches: [
      "The free plan shrank from 1,000 contacts to 25 in March 2026. One Reel with a keyword trigger can exhaust it in an afternoon; treat free as a test.",
      "WhatsApp conversations carry Meta's per-conversation fees on top of your subscription, and SMS carries carrier fees. Budget for both if those channels matter.",
      "Overage fees are automatic when you pass your contact tier (reported as starting around $0.10 per extra contact on Essential). A viral month raises your bill whether or not it raised your sales.",
      "AI is not included in the base price on lower tiers; the AI add-on costs $29 a month extra on Pro.",
      "Free and Essential carry ManyChat branding on messages; custom branding comes with higher tiers.",
    ],
    whoShouldGet: [
      "Creators, coaches, and ecommerce brands that sell through Instagram and WhatsApp",
      "Local businesses whose customers message them on Facebook instead of visiting a website",
      "Anyone running comment-to-DM or click-to-message ad campaigns",
    ],
    whoShouldSkip: [
      "Businesses whose traffic arrives on a website (you need Tidio or Chatbase for that widget)",
      "Teams that want a train-on-docs AI agent rather than pre-built flows",
      "Anyone uncomfortable with a bill that grows automatically with audience size",
    ],
    comparison: [
      {
        tool: "ManyChat",
        price: "Free plan; from $14/mo",
        difference: "Social DM automation (Instagram, WhatsApp, Messenger); no website chat widget at all",
      },
      {
        tool: "Tidio",
        price: "Free plan; from $29/mo",
        difference: "Website-first: live chat plus AI agent plus ticketing, with Instagram and WhatsApp as side channels",
      },
      {
        tool: "Chatbase",
        price: "From $40/mo (700 message credits)",
        difference: "Train-on-docs AI bot for your website; less about campaigns, more about answering from your content",
      },
      {
        tool: "Intercom (Fin)",
        price: "From $29/seat/mo + $0.99/outcome",
        difference: "Enterprise support platform that also covers chat and email; far pricier, built for support teams",
      },
    ],
    goingDeeper: {
      integrations: [
        "Direct integrations include Shopify, HubSpot, Klaviyo, and Google Sheets, plus Zapier for everything else (email platforms, CRMs, calendars). ManyChat also connects to ad platforms so click-to-message ads feed straight into flows.",
        "The practical pattern for small businesses: ManyChat collects the lead in the DM, Zapier or a native integration pushes them into your email tool and CRM, and broadcasts go out from ManyChat where the conversation lives.",
      ],
      api: "ManyChat publishes a developer API with API keys managed in your account settings, so you can send messages, update contact fields, and trigger flows from your own systems. Webhooks inside flows can also call external services mid-conversation, which is how technical users bolt on custom AI replies.",
      privacy: [
        "From ManyChat's own security page: it states GDPR and CCPA alignment, encrypts data in transit (TLS 1.2 with AES-256) and at rest (FIPS 140-2 compliant encryption), and runs external penetration tests at least annually.",
        "As a Meta Business Partner, ManyChat goes through Meta's Data Use Checkups and compliance audits, and connects via OAuth rather than storing your Instagram password.",
        "Your responsibilities: Meta's messaging rules (the 24-hour window for free-form messages, consent for broadcasts) are enforced by Meta, and breaking them risks your account regardless of the tool. Collect only the contact data you need and honor opt-outs (replying STOP unsubscribes).",
      ],
      advancedWorkflowTitle: "Comment-to-DM lead funnel with CRM sync",
      advancedWorkflow:
        "Post content with a keyword CTA. The flow delivers the lead magnet, asks one qualifying question (for example, are you buying for yourself or your business), tags the contact by answer, and syncs them to your CRM via Zapier with the tag attached. A week later, a follow-up flow offers a booking link only to the qualified tag. You end up with a segmented, nurtured list built entirely inside DMs.",
    },
    faqs: [
      {
        q: "Is ManyChat safe for my Instagram account?",
        a: "Yes, when used as intended. ManyChat is an official Meta Business Partner using the official Instagram and Messenger APIs with OAuth login, so it never needs your password. Account trouble almost always comes from breaking Meta's messaging rules (spammy broadcasts, ignoring the 24-hour window), not from the tool itself.",
      },
      {
        q: "What is an active contact?",
        a: "Anyone who interacts with one of your automations in a given month. Your plan includes a set number (250 on Essential, 2,500 on Pro), and going over triggers automatic per-contact overage fees.",
      },
      {
        q: "Does ManyChat work on my website?",
        a: "No. ManyChat covers Instagram, TikTok, Messenger, Telegram, WhatsApp, SMS, and email, but it has no website chat widget. If website visitors matter, run Tidio or Chatbase alongside it.",
      },
      {
        q: "What extra fees should I expect?",
        a: "WhatsApp conversations carry Meta's per-conversation fees, SMS carries carrier fees, contact overages apply above your tier, and the AI add-on costs $29 a month on Pro. The subscription is the floor, not the total.",
      },
      {
        q: "Can ManyChat answer free-form questions like ChatGPT?",
        a: "Partly. Its AI step handles simple free-text FAQ answers from a small knowledge base, but ManyChat is fundamentally a flow builder: you design the conversation paths. For a true train-on-docs agent, look at Chatbase.",
      },
      {
        q: "Is the free plan worth using?",
        a: "For testing one small automation, yes. For real business use, no: 25 active contacts and ManyChat branding make it a demo. Essential at $14 a month is the realistic starting point.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI scheduling
  // ------------------------------------------------------------------
  {
    name: "Calendly",
    slug: "calendly",
    tagline: "The standard booking link: let people book time with you without the back and forth.",
    category: "ai-scheduling",
    pricing: "Free; Standard from $10/seat/mo (billed annually)",
    pros: [
      "The default everyone recognizes: most clients have used a Calendly link before, so there is zero learning curve for your bookers",
      "Deep integration catalog: Google Calendar, Outlook, Zoom, Teams, Meet, Slack, Stripe, PayPal, Salesforce, HubSpot, plus Zapier to 700+ apps",
      "Real free plan: usable forever for one person with one meeting type",
      "Enterprise-grade security posture: SOC 2 Type II, ISO 27001, GDPR, CCPA, and PCI, with a public trust center",
      "Paid plans stay cheap for solos: $10 a seat a month is easy math for a consultant or small shop",
    ],
    cons: [
      "Per-seat pricing punishes teams: a 5-person team on Teams is $80 a month on annual billing, and you pay for every seat, filled or not",
      "The free plan is thin on purpose: one event type, one calendar connection, no payments, no integrations",
      "Booking only, nothing else: it will not plan your day, defend focus time, or schedule your tasks (that is Reclaim or Motion territory)",
      "The AI features (Notetaker, Callie) cost extra: they live on the Plus tiers, not on Standard or Teams",
      "The pricing page leads with annual rates; month-to-month is 17 to 20 percent more and that is easy to miss",
    ],
    bestFor: "Anyone who needs a booking link clients already trust, from solo consultants to sales teams",
    url: "https://calendly.com",
    verdict:
      "Calendly is the safe default for booking: a real free tier, integrations with everything, and a link your clients already know how to use. Pay per seat only when the free plan's one-event-type limit actually bites.",
    verdictBox:
      "Calendly is the booking link the whole business world already knows how to use, which is half the value. A genuinely free plan covers one person with one meeting type; Standard at $10 a seat a month (billed annually) unlocks unlimited event types, payments, and integrations. The per-seat model adds up fast for teams, and the AI notetaking features cost extra on the Plus tiers. If your main job is letting other people book time with you, start here.",
    quickFacts: {
      price: "Free; Standard $10/seat/mo annual ($12 monthly); Teams $16/seat/mo annual ($20 monthly)",
      freeTier: "Free plan forever (1 event type, 1 calendar); 14-day trial of paid plans",
      setup: "Minutes: connect your calendar, set availability, share your link",
    },
    whatIsIt: [
      "Calendly is a scheduling link you send to clients, leads, or anyone who needs time with you. They pick a slot from your real availability, the meeting lands on both calendars, and the back-and-forth emails disappear.",
      "It connects to the calendar you already use (Google or Outlook), adds video conferencing links automatically, sends reminders so people actually show up, and on paid plans can take payments, route leads to the right teammate, and sync bookings into your CRM.",
    ],
    businessScenarios: [
      {
        title: "End the 'what time works for you' email thread",
        description:
          "A prospect asks for a call. Instead of five emails negotiating a time, you send your link, they pick Thursday at 2pm, and a Zoom invite lands on both calendars. You look professional and the meeting is set in under a minute.",
      },
      {
        title: "Charge for consultations at booking",
        description:
          "A coach or consultant connects Stripe on the Standard plan and sets a 60-minute strategy session at $150. The client pays when they book, the calendar holds the slot, and no-shows drop because money already changed hands.",
      },
      {
        title: "Route inbound leads to the right rep",
        description:
          "A growing sales team uses routing forms on the Teams plan: enterprise leads go to the senior rep, everyone else round-robins across the team. Every lead gets a booked meeting with the right person, no manual triage.",
      },
      {
        title: "Cut no-shows with automatic reminders",
        description:
          "A service business turns on email and text reminders for every booking. Clients get a nudge the day before and an hour before, and the owner stops losing afternoons to people who forgot.",
      },
      {
        title: "Share team availability without the group chat",
        description:
          "A support team publishes one link that shows combined availability across the team and books whoever is free. Customers never see the internal juggling.",
      },
    ],
    howItWorks: [
      "Connect your calendar. Link Google Calendar or Outlook (paid plans support multiple calendars) and Calendly reads your real availability, including existing events, so nobody can double-book you.",
      "Create your event types. A free plan gets one (say, a 30-minute intro call). Paid plans allow unlimited: discovery calls, demos, paid consultations, each with its own length, price, questions, and reminders.",
      "Set your rules. Choose your working hours, buffers between meetings, how far ahead people can book, and minimum notice. This is what keeps your days sane.",
      "Share the link. Put it in your email signature, on your contact page, in proposals. Bookers pick a time, answer your questions, get a confirmation, and you get a calendar invite with the video link attached.",
    ],
    pricingExplained: [
      "Free ($0 forever): one user, one event type, one calendar connection, basic 1:1 scheduling. Enough to test whether booking links work for your business. Standard ($10 per seat per month billed annually, $12 monthly): unlimited event types, multiple calendars, automations, Stripe and PayPal payments, HubSpot and Mailchimp integrations. Teams ($16 per seat per month billed annually, $20 monthly): everything in Standard plus round-robin and collective scheduling, lead routing forms, Salesforce, Marketo, and Pardot integrations, managed event types.",
      "Standard Plus ($18 per seat per month) and Teams Plus ($24 per seat per month) add Calendly's AI features: Notetaker (meeting summaries) and Callie (AI scheduling assistant). Enterprise starts around $15,000 a year with a 50-seat minimum and is annual-only: SSO/SAML, SCIM, audit logs, domain control. Every paid plan is priced per seat, and only hosts (people who connect a calendar and take meetings) need seats; your bookers never pay.",
    ],
    pricingCatches: [
      "You pay for every seat, filled or not. Calendly's own billing docs say five seats with four users still bills five seats, so right-size your seat count.",
      "The free plan's single event type is the real limit. The moment you need a 15-minute intro AND a 60-minute paid session, you need Standard.",
      "Paying month-to-month costs 17% more on Standard and 20% more on Teams. The pricing page advertises the annual rates, so do the math for your actual billing choice.",
      "AI features are not included on Standard or Teams. Notetaker and Callie require the Plus tiers, which is an $8 per seat per month step up from the base plans.",
      "Enterprise has a 50-seat minimum, so for most small businesses the realistic ceiling is Teams Plus.",
    ],
    whoShouldGet: [
      "Solo consultants, coaches, and service pros who need a professional booking link clients already trust",
      "Sales and support teams that need lead routing, round-robin, and CRM sync",
      "Any business where clients keep asking 'when are you free' and you want that thread to end",
    ],
    whoShouldSkip: [
      "Anyone who wants a full-featured free plan (Cal.com's free tier is far more generous)",
      "People who need the tool to plan their own day, not just take bookings (look at Reclaim or Motion)",
      "Businesses that need client records and packages built in (Acuity-style tools serve that better)",
    ],
    comparison: [
      {
        tool: "Calendly",
        price: "Free; $10-$16/seat/mo annual",
        difference: "The safe default: widest recognition, deepest integrations, booking only",
      },
      {
        tool: "Cal.com",
        price: "Free (1 user); $12/user/mo annual",
        difference: "More generous free plan, open-source and self-hostable; smaller brand recognition",
      },
      {
        tool: "SavvyCal",
        price: "$10-$17/user/mo annual",
        difference: "Nicer booking experience (calendar overlay, ranked availability); no free plan, fewer integrations at the low tier",
      },
      {
        tool: "Reclaim.ai",
        price: "Free; $10/seat/mo annual",
        difference: "Also does booking links, plus defends your focus time and auto-schedules tasks; booking features alone are weaker than Calendly's",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native calendar and conferencing: Google Calendar, Outlook, Zoom, Microsoft Teams, Google Meet, Webex, GoTo. Connect Stripe or PayPal for paid bookings, Salesforce or HubSpot so bookings land on contact records, Slack for notifications, and Google Analytics to track booking goals.",
        "Zapier connects Calendly to 700+ more apps: add bookers to your email list, create tasks in your project tool, log bookings in a spreadsheet. Workflows and automations on paid plans handle reminders and follow-ups without third-party tools.",
      ],
      api: "Calendly publishes a developer API and webhooks with public documentation, so a technical team can build bookings into their own product or sync booking data into internal systems. Enterprise adds a Data Deletion API for privacy compliance workflows.",
      privacy: [
        "Calendly maintains SOC 2 Type II and ISO 27001 certifications, plus SOC 3 and CSA STAR, and states GDPR, CCPA, and PCI compliance on its security pages, with a public trust center for security documentation.",
        "It connects to your calendar via OAuth rather than storing your calendar password, and limits collection to what scheduling needs. Enterprise plans add SSO, SCIM provisioning, audit logs, and domain control for IT-managed accounts.",
      ],
      advancedWorkflowTitle: "Self-qualifying sales booking flow",
      advancedWorkflow:
        "On the Teams plan, build a routing form that asks company size and need, then routes enterprise leads to the senior rep's calendar and everyone else round-robin. Sync every booking to Salesforce so the rep sees the lead's answers before the call, and add a Zapier step that creates a pre-call research task in your project tool. The link qualifies, routes, and briefs, so the rep just shows up.",
    },
    faqs: [
      {
        q: "Is Calendly really free?",
        a: "Yes, the Free plan costs nothing forever. It covers one user, one event type, and one calendar connection. Most businesses outgrow it when they need more than one meeting type (like a 15-minute intro and a 60-minute paid session), which is when Standard at $10 a seat a month makes sense.",
      },
      {
        q: "Do the people who book with me need a Calendly account?",
        a: "No. Your bookers just click your link and pick a time; they need no account and pay nothing. Only hosts, the people who connect a calendar and take meetings, need a paid seat.",
      },
      {
        q: "Can I charge for appointments through Calendly?",
        a: "Yes, on Standard and up. Connect your own Stripe or PayPal account, set a price on the event type, and the client pays when they book. Calendly does not take a cut; your payment processor's normal fees apply.",
      },
      {
        q: "Will it stop people from double-booking me?",
        a: "Yes. Calendly reads your connected calendar's real availability, so it only offers genuinely free slots. You can also add buffers between meetings, daily booking limits, and minimum notice periods.",
      },
      {
        q: "Can Calendly plan my day or protect focus time?",
        a: "No, that is not what it does. Calendly takes bookings; it does not auto-schedule your tasks or defend focus blocks. If that is the job, look at Reclaim.ai or Motion instead.",
      },
      {
        q: "How does Calendly handle time zones?",
        a: "Automatically. Your booker sees your availability in their own local time zone, so neither of you has to do the math.",
      },
      {
        q: "Is my calendar data secure with Calendly?",
        a: "Calendly is SOC 2 Type II and ISO 27001 certified, states GDPR and CCPA compliance, and connects via OAuth so it never stores your calendar password. It has a public trust center with security documentation for IT reviews.",
      },
    ],
  },
  {
    name: "Cal.com",
    slug: "cal-com",
    tagline: "Open-source booking links with a genuinely generous free plan, or self-host it on your own servers.",
    category: "ai-scheduling",
    pricing: "Free for 1 user; Teams from $12/user/mo (billed annually)",
    pros: [
      "The most generous free plan in the category: one user gets unlimited event types, unlimited calendars, Stripe/PayPal payments, and 100+ integrations at $0",
      "Open source, so you can self-host it and pay zero per-seat fees (you pay for the server and the maintenance time instead)",
      "API-first by design: a documented API v2, webhooks on every plan, and OAuth clients, built for developers embedding scheduling into products",
      "Built-in video (Cal Video) plus 20+ video tool integrations, so meetings work out of the box",
      "A cal.eu hosted instance exists for users who want their data handled in Europe",
    ],
    cons: [
      "Less polished and less familiar than Calendly: non-technical users and bookers may find the experience rougher",
      "Self-hosting trades money for engineering time: servers, updates, and uptime are your problem",
      "Team features are cloud-only since 2026, so self-hosters do not get everything the hosted plans have",
      "Smaller ecosystem: fewer third-party guides, templates, and integrations than Calendly's catalog",
      "An April 2026 review reported the mobile app logging cal.eu users into cal.com instead, locking them out; the two instances do not share accounts, so pick carefully",
    ],
    bestFor: "Budget-conscious solos who want full features free, and technical teams that want an API or self-hosting",
    url: "https://cal.com",
    verdict:
      "Cal.com is the value-and-control pick: the free plan does what Calendly charges $10 a month for, and the open-source code means you can self-host or build on its API. Trade-off: less polish and brand recognition.",
    verdictBox:
      "Cal.com gives you what Calendly's $10 plan gives you, free: unlimited event types and calendars, payments, and 100+ integrations for a single user at $0. Teams is $12 per user per month billed annually and adds round-robin, routing forms, and analytics. The open-source code also lets you self-host (no per-seat fees, but you own the servers and the maintenance) and its API v2 is built for embedding scheduling into your own product. The catch is polish: it is less refined than Calendly and the brand is less familiar to your bookers.",
    quickFacts: {
      price: "Free (1 user); Teams $12/user/mo annual ($16 monthly); Organizations $28/user/mo annual",
      freeTier: "Free forever: 1 user, unlimited event types and calendars, payments, 100+ integrations",
      setup: "Minutes on hosted; self-hosting needs a developer and a server",
    },
    whatIsIt: [
      "Cal.com is a booking-link tool like Calendly, except it is open source. You get a link, people pick a time from your real availability, and the meeting lands on your calendar. The difference is philosophy: generous free tier, your data under your control, and an API built for developers.",
      "You can use Cal.com's hosted service (the easy path, like any SaaS), or download the code and run it on your own servers. For a business that cares about data ownership or wants scheduling embedded inside its own app, that option matters.",
    ],
    businessScenarios: [
      {
        title: "Run full-featured booking free as a solo",
        description:
          "A freelance consultant needs three event types (intro call, paid session, follow-up), takes payment through Stripe, and syncs to HubSpot. On Calendly that is $10 a month; on Cal.com's free plan it is $0.",
      },
      {
        title: "A small team shares the booking load",
        description:
          "A four-person agency puts Cal.com Teams ($12 per user per month annual) on a shared round-robin link. Inbound inquiries distribute evenly, and the routing form sends big-budget projects to the founder automatically.",
      },
      {
        title: "Embed booking inside your own product",
        description:
          "A SaaS founder uses Cal.com's API to put scheduling directly inside their app, so customers book onboarding calls without leaving the product. No iframe hacks, no third-party branding.",
      },
      {
        title: "Keep scheduling data on your own infrastructure",
        description:
          "A business with strict data requirements self-hosts Cal.com on its own servers. No per-seat fees, and booking data never sits on a vendor's cloud. The trade-off is that someone has to maintain it.",
      },
      {
        title: "Take payments on a booking from day one",
        description:
          "A coach connects Stripe on the free plan and charges for strategy sessions at booking. Paid bookings, usually a paid-plan feature elsewhere, cost nothing extra here.",
      },
    ],
    howItWorks: [
      "Sign up on cal.com (or deploy the open-source code to your own server). Connect Google Calendar or Outlook and Cal.com learns your real availability, including busy times it must work around.",
      "Create unlimited event types: 15-minute intros, paid hour-long sessions, group workshops, round-robin team links, each with its own questions, reminders, and payment settings.",
      "Share your link or embed it. Use the hosted link, drop the embed on your website, or call the API to build booking into your own product.",
      "Manage and automate. Set up routing forms to direct bookers, turn on email and SMS reminders, connect webhooks so bookings flow into your CRM or spreadsheets automatically.",
    ],
    pricingExplained: [
      "Free ($0 forever): 1 user, unlimited event types and calendars, email and SMS notifications, 100+ integrations, mobile apps, browser extension, Stripe and PayPal payments. Teams ($12 per user per month billed annually, $16 monthly): everything in Free plus shared team availability, round-robin scheduling, managed and collective event types, recurring events, routing forms, booking analytics. Organizations ($28 per user per month billed annually, $37 monthly): everything in Teams plus unlimited sub-teams, custom-variable routing, a company subdomain, SAML SSO, SCIM, role-based permissions, and additional APIs.",
      "Enterprise is custom-priced and annual-only, adding SLAs (99.9%, with a 99.99% option), dedicated onboarding, HRIS integrations, and priority support. Teams and Organizations both include a 14-day free trial. Annual billing saves roughly 25% versus monthly.",
    ],
    pricingCatches: [
      "The free plan is one user only. The moment a second person needs their own calendar connected, you are on Teams at $12 per user per month.",
      "Self-hosting is free the way a free puppy is free: no license cost, but you pay for servers and the engineering time to deploy, update, and secure it.",
      "Monthly billing runs noticeably higher: $16 instead of $12 on Teams, $37 instead of $28 on Organizations. The annual discount is 25%, so month-to-month is expensive.",
      "Governance features (SSO, SCIM, role permissions) need the Organizations plan at $28 per user per month, which is a real jump for a small team.",
      "The separate Cal.ai phone agent (an AI that answers calls to book appointments) is metered separately at $0.29 per minute. It is not part of the scheduling plans.",
    ],
    whoShouldGet: [
      "Solo operators and freelancers who want full booking features without paying $10 a month",
      "Technical teams that want an API, webhooks, or embedded scheduling",
      "Businesses that want to self-host scheduling on their own infrastructure",
    ],
    whoShouldSkip: [
      "Non-technical users who want the most polished, foolproof experience (Calendly is smoother)",
      "Anyone who needs planning of their own day, not just bookings (Reclaim or Motion)",
      "Teams that need hand-holding: the ecosystem of guides and consultants is smaller than Calendly's",
    ],
    comparison: [
      {
        tool: "Cal.com",
        price: "Free (1 user); $12/user/mo annual",
        difference: "Most generous free plan; open-source and self-hostable; API-first; less polish",
      },
      {
        tool: "Calendly",
        price: "Free; $10-$16/seat/mo annual",
        difference: "More familiar to bookers, deeper integration catalog; free plan much thinner",
      },
      {
        tool: "SavvyCal",
        price: "$10-$17/user/mo annual",
        difference: "Nicer invitee experience; no free plan at all; less suited to developers",
      },
      {
        tool: "Reclaim.ai",
        price: "Free; $10/seat/mo annual",
        difference: "Adds focus-time defense and task auto-scheduling on top of booking; booking alone is simpler here",
      },
    ],
    goingDeeper: {
      integrations: [
        "100+ app integrations: Zapier and Make for no-code automation, Salesforce and HubSpot for CRM sync, 20+ video tools plus built-in Cal Video. Webhooks run on every plan, including Free, so bookings can trigger anything you build.",
        "For embedding: the open-source codebase and embed options put the booking flow inside your own site or product, and Organizations unlocks additional APIs plus a company subdomain for branded team scheduling.",
      ],
      api: "Cal.com publishes a documented API v2 with OAuth scopes and rate limits, designed for embedding scheduling into your own applications. The Organizations plan unlocks additional API surface. Note: the separate Cal.com Platform product (for building scheduling into third-party products at scale) has been closed to new sign-ups since December 2025.",
      privacy: [
        "The Organizations plan lists SOC 2 Type II, HIPAA, and ISO 27001 compliance, and Enterprise adds SLA-backed uptime (99.9%, with a 99.99% option). Verify current certificates with Cal.com's team before relying on them for procurement.",
        "Self-hosting is the strongest privacy lever: booking data lives on your own servers under your own policies. On the hosted side, a cal.eu instance exists separately from cal.com for users who prefer EU-based handling; the two do not share accounts, so choose at signup.",
      ],
      advancedWorkflowTitle: "Embedded onboarding scheduler with CRM sync",
      advancedWorkflow:
        "Use the Cal.com API to embed booking directly in your product's onboarding flow: new customers pick an onboarding call without leaving your app. Route via routing forms so enterprise signups reach the founder and everyone else round-robins across the team. Fire a webhook on every booking to create the contact in HubSpot with the event type tagged, and send SMS reminders to cut no-shows. Scheduling becomes part of your product, not a side tab.",
    },
    faqs: [
      {
        q: "Is Cal.com really free?",
        a: "For one user, yes, and it is unusually generous: unlimited event types and calendars, payments via Stripe or PayPal, 100+ integrations, and the mobile apps, all at $0 forever. You only start paying when you add a second user or need team features.",
      },
      {
        q: "What does self-hosting actually involve?",
        a: "Cal.com is open source, so you can deploy it on your own server and skip per-seat fees entirely. In practice that means someone technical sets it up, applies updates, and keeps it online. For a non-technical solo, the hosted free plan is the better deal.",
      },
      {
        q: "How is it different from Calendly?",
        a: "Three things: the free plan is far more capable, the code is open source (self-host or audit it), and the API is a first-class citizen for embedding scheduling into products. Calendly wins on polish, brand familiarity, and integration depth.",
      },
      {
        q: "Can I embed it on my website?",
        a: "Yes. Beyond the standard booking link, Cal.com offers embed options for your site and a documented API v2 for building booking into your own product or workflows.",
      },
      {
        q: "Does it work with Outlook and Microsoft tools?",
        a: "Yes, Outlook calendar connections are supported. One caveat from 2026 reviews: if you use the cal.eu hosted instance, use the matching mobile app and login, because cal.com and cal.eu accounts are separate.",
      },
      {
        q: "What is the Cal.ai phone agent?",
        a: "A separate add-on: an AI voice agent that answers phone calls and books appointments into your Cal.com schedule. It is metered at $0.29 per minute from credits, on top of your scheduling plan.",
      },
      {
        q: "Is my data secure on the hosted plan?",
        a: "The Organizations plan lists SOC 2 Type II, HIPAA, and ISO 27001 compliance. If compliance is a buying criterion, ask Cal.com's team for current certificates. For maximum control, self-hosting keeps all data on your own servers.",
      },
    ],
  },
  {
    name: "Motion",
    slug: "motion",
    tagline: "An AI planner that builds your day from tasks and deadlines, then rebuilds it when reality changes.",
    category: "ai-scheduling",
    pricing: "No free plan; teams from $19/seat/mo, solos from $29/mo (billed annually)",
    pros: [
      "The auto-scheduling is genuinely good: give it tasks with deadlines and priorities, and it builds your day around fixed meetings, then reshuffles when a meeting moves",
      "All-in-one workspace: tasks, projects, calendar, docs, notes, and an AI meeting notetaker in one subscription can replace several tools",
      "Two-way sync with Google Calendar and Outlook, so your real calendar stays the source of truth",
      "Smart capture: create tasks by forwarding emails, from Zoom or Meet transcripts, or by voice via Siri",
      "Backward planning from deadlines is rare in task tools and genuinely useful for client work with hard due dates",
    ],
    cons: [
      "The most expensive solo price in this category: $29 a month billed annually ($49 monthly), versus a $19 team per-seat rate that reviews keep misquoting as the personal price",
      "No free plan, only a 7-day trial, and multiple 2026 reviews report it requires a card and auto-converts unless canceled",
      "The aggressive AI can feel controlling: it sometimes schedules work at times you would not have chosen, which creates friction if you like manual control",
      "AI credits are metered: 7,500 per seat per month on Pro AI, 15,000 on Business AI, with overage charges per 100 credits on top",
      "Overkill if your problem is just booking meetings: there is no invitee booking-link experience comparable to Calendly or Cal.com",
    ],
    bestFor: "Deadline-driven owners and small teams whose week falls apart the moment a meeting moves",
    url: "https://usemotion.com",
    verdict:
      "Motion is the autopilot for task-heavy weeks: it plans your day and replans it when things shift. It is also the priciest solo option here with no free tier, so it has to earn its keep by replacing other subscriptions.",
    verdictBox:
      "Motion is the only tool here that plans your work, not just your meetings: feed it tasks with deadlines and priorities and it sequences them around your fixed meetings, then automatically rebuilds the plan when a meeting moves or a task runs long. Team pricing is Pro AI $19 per seat per month billed annually ($27 monthly) and Business AI $29 per seat per month ($45 monthly); solo users pay more ($29/$39 per month annually). There is no free plan, only a 7-day trial, and AI features draw from metered credit pools. If your week is task-heavy and deadline-driven, it can replace several subscriptions; if you just need booking links, it is the wrong tool.",
    quickFacts: {
      price: "Teams: Pro AI $19/seat/mo, Business AI $29/seat/mo annual; solo: $29 and $39/mo annual",
      freeTier: "No free plan; 7-day trial only (reviewers report card required, auto-converts)",
      setup: "Under an hour: connect calendar, add tasks with deadlines; two-way Google/Outlook sync",
    },
    whatIsIt: [
      "Motion is an AI daily planner. Instead of you dragging tasks onto a calendar every morning, you tell Motion what needs doing, when it is due, and how long it takes, and its AI builds your day: tasks slotted around your fixed meetings in priority order.",
      "When reality intrudes (a meeting gets added, a task runs long, a deadline moves), Motion reshuffles automatically. Around that core it has grown into an all-in-one workspace: projects, docs and notes, an AI chat that searches everything, and a meeting notetaker that turns action items into tasks.",
    ],
    businessScenarios: [
      {
        title: "Stop losing Monday mornings to planning",
        description:
          "An agency owner has 14 client deliverables with different deadlines. Instead of spending an hour mapping the week, Motion sequences the work around fixed meetings automatically. When a client call gets moved to Wednesday, the whole plan rebuilds itself.",
      },
      {
        title: "Never miss a deadline hidden in email",
        description:
          "A contractor forwards client emails to Motion, which creates tasks with the deadlines from the message. The proposal due Thursday gets scheduled into Tuesday's open blocks without anyone opening a task manager.",
      },
      {
        title: "Turn meetings into assigned work automatically",
        description:
          "The AI notetaker joins Zoom calls, captures action items, and creates them as tasks linked to the right project. The post-meeting admin step of 'who was supposed to do what' disappears.",
      },
      {
        title: "See team capacity before committing",
        description:
          "On the Business AI plan, a five-person shop checks predicted completion dates against real team capacity. When one person is overloaded, work gets rebalanced before the deadline slips instead of after.",
      },
      {
        title: "Keep one system instead of four subscriptions",
        description:
          "A solo consultant cancels a separate task app, notes app, and meeting transcription tool, because Motion bundles projects, docs, notes, and the notetaker. The $29 a month starts to look reasonable against three $10 subscriptions.",
      },
    ],
    howItWorks: [
      "Connect your calendar. Motion does a two-way sync with Google Calendar or Outlook, importing your existing meetings as fixed events it plans around (it does not move your meetings, it schedules tasks into the gaps).",
      "Add your work. Create tasks in plain language with a deadline, estimated duration, and priority, or forward emails to Motion to create tasks from them. For projects, describe the goal and Motion generates the task list, assignees, and dependencies for your review.",
      "Let it plan. Motion's AI sequences tasks around your fixed meetings by priority and deadline, building each day's schedule. Set work hours and preferences so it knows when you are available.",
      "Watch it adapt. Add a 2pm meeting and Motion finds the next available slot for your 3pm task block automatically. Complete tasks, and the plan recalculates. Use AI Chat to ask about anything across your tasks, docs, and meeting notes.",
    ],
    pricingExplained: [
      "Two plans, priced per seat. Pro AI: $19 per seat per month billed annually on the Teams rate ($27 per seat monthly); solo individuals pay $29 per month billed annually ($49 month-to-month). It includes AI chat, projects and tasks, AI calendar and meetings, docs and notes, the AI task planner, unlimited storage, and 7,500 AI credits per seat per month. Business AI: $29 per seat per month billed annually ($45 monthly); solo $39 per month annually ($69 monthly). It adds capacity planning, dashboards and reports, timeline and Gantt views, time tracking, and permission controls, with 15,000 AI credits per seat per month.",
      "AI features draw from the monthly credit pool; extra credits cost 25 cents per 100 on Pro AI and 19 cents per 100 on Business AI. Basic auto-scheduling uses no credits. Paying annually saves about 33% versus monthly. There is no free plan; the 7-day trial is the only way to test it.",
    ],
    pricingCatches: [
      "The headline $19 is the team per-seat rate, not the solo price. A single user pays $29 a month on annual billing ($49 monthly), which many reviews flag as the most expensive solo price in the category.",
      "The 7-day trial is short, and multiple 2026 reviewers report it requires a payment card and converts to a paid subscription unless canceled before renewal. Set a calendar reminder.",
      "AI credits are a second meter on top of the seat price. Heavy use of AI chat, project generation, and the notetaker can push you into overage charges.",
      "Per-seat pricing means a 5-person team on Business AI is $145 a month on annual billing before any credit overage. Model the real team cost, not the per-seat number.",
      "Annual billing saves 33% but commits you upfront ($228 per Pro AI seat per year on the team rate). Be sure the workflow fits before committing.",
    ],
    whoShouldGet: [
      "Deadline-driven freelancers and owners juggling many tasks across clients",
      "Small teams that want capacity planning and automatic replanning when the week shifts",
      "People already paying for separate task, notes, and transcription tools that Motion could replace",
    ],
    whoShouldSkip: [
      "Anyone whose main need is a booking link for clients (Calendly or Cal.com do that better and cheaper)",
      "People who want full manual control of their schedule and will fight an algorithm",
      "Budget-conscious solos: Reclaim.ai's free tier does auto-scheduling of tasks at $0",
    ],
    comparison: [
      {
        tool: "Motion",
        price: "Teams $19-$29/seat/mo; solo $29-$39/mo annual",
        difference: "Full auto-planner plus projects, docs, notetaker; priciest solo option, no free tier",
      },
      {
        tool: "Reclaim.ai",
        price: "Free; $10-$15/seat/mo annual",
        difference: "Defends focus time and auto-schedules tasks on your existing calendar; free tier; no projects or docs",
      },
      {
        tool: "Calendly",
        price: "Free; $10-$16/seat/mo annual",
        difference: "Booking links only, no day planning at all; far cheaper for pure scheduling",
      },
      {
        tool: "Cal.com",
        price: "Free (1 user); $12/user/mo annual",
        difference: "Booking links with a generous free plan; no task planning or auto-scheduling",
      },
    ],
    goingDeeper: {
      integrations: [
        "Two-way calendar sync with Google Calendar and Outlook keeps Motion and your real calendar in lockstep. Native connections include Todoist, Asana, Slack, and Google Tasks, with iOS, Android, and desktop apps. Email forwarding turns messages into tasks, Siri voice commands create them hands-free, and Zoom/Google Meet transcripts feed action items into projects.",
        "Zapier connects Motion to thousands of more apps for triggers and actions (for example, creating Motion projects from completed inspections or form submissions).",
      ],
      api: "Motion does not publish a general-purpose developer API on its public pages. The practical routes for automation are its Zapier integration and its native app connections. Third parties have built MCP-server bridges on top of Motion, but those are not official Motion products.",
      privacy: [
        "Motion's data processing addendum references third-party SSAE 18 SOC 2 audits, with a summary report available on confidential written request rather than published openly. The DPA covers GDPR-aligned data rights including access, deletion, and portability.",
        "Practical note: email forwarding and transcript ingestion mean your task content flows through Motion's servers by design. If your work involves sensitive client data, review the DPA and confirm the current audit status with their team before committing.",
      ],
      advancedWorkflowTitle: "Deadline-driven client pipeline on autopilot",
      advancedWorkflow:
        "Forward client emails to Motion so every request becomes a task with its deadline attached. Set priorities by client tier and let Motion backward-plan from due dates, slotting work into open blocks around your meetings. Turn on the meeting notetaker so action items from client calls land as project tasks automatically. On Business AI, watch the capacity dashboard weekly: when predicted completion dates slip past deadlines, rebalance before the client notices. Your mornings go from planning to doing.",
    },
    faqs: [
      {
        q: "Will Motion move my meetings around?",
        a: "No. Your meetings are fixed events; Motion schedules your tasks into the gaps around them and reshuffles the tasks (not the meetings) when things change.",
      },
      {
        q: "What are AI credits and will I run out?",
        a: "AI features like AI chat, project generation, and the notetaker draw from a monthly pool: 7,500 credits per seat on Pro AI, 15,000 on Business AI. Basic auto-scheduling uses none. Heavy AI use can trigger overage charges (25 cents per 100 credits on Pro AI), so watch usage in your first month.",
      },
      {
        q: "Why is the solo price higher than the team price?",
        a: "Motion prices individuals and teams separately. A solo on Pro AI pays $29 a month billed annually ($49 month-to-month), while each team seat is $19 a month billed annually. Many reviews misquote $19 as the personal price; budget for the real one.",
      },
      {
        q: "Is there a free plan?",
        a: "No. Motion offers only a 7-day trial, and multiple 2026 reviewers report it requires a payment card and auto-converts to a paid subscription unless canceled. If you need a free auto-scheduler, Reclaim.ai's Lite tier is free forever.",
      },
      {
        q: "Can clients book meetings with me through Motion?",
        a: "Motion has an AI calendar and meeting features, but it is not a booking-link tool like Calendly. If clients booking time with you is the core need, pair Motion with a dedicated booking tool or choose one of those instead.",
      },
      {
        q: "What happens when my week explodes?",
        a: "That is the whole point of the product: add an unexpected meeting and Motion automatically finds the next available slot for displaced tasks. You do not replan; the plan rebuilds itself.",
      },
      {
        q: "Does it replace tools like Asana or Todoist?",
        a: "For many small teams, yes: Motion bundles tasks, projects, docs, notes, and time tracking. It two-way syncs with Google Calendar and Outlook, and integrates with Todoist and Asana if you want to keep them alongside.",
      },
    ],
  },
  {
    name: "Reclaim.ai",
    slug: "reclaim-ai",
    tagline: "An AI layer on your calendar that defends focus time and auto-schedules tasks, habits, and breaks.",
    category: "ai-scheduling",
    pricing: "Free Lite forever; Starter from $10/seat/mo (billed annually)",
    pros: [
      "Free-forever Lite tier: the only auto-scheduler in this category you can run indefinitely at $0, with no card required",
      "Defends focus time automatically: habits, focus blocks, and buffers get scheduled and stay scheduled as meetings land",
      "Best task integrations of the auto-schedulers: Asana, ClickUp, Todoist, Jira, and Google Tasks flow onto your calendar",
      "No migration: it sits on top of the Google Calendar or Outlook calendar you already use",
      "Serious about security: SOC 2 Type II certified, EU-US Data Privacy Framework certified, public trust center with security documentation",
    ],
    cons: [
      "Starter limits are real: up to 10 seats, an 8-week scheduling range, 3 scheduling links, and 3 Smart Meetings",
      "Smart Meetings with 3 or more attendees consume Attendance Units, a quiet extra cost (a 3-pack of extra units costs $8 a month on Starter, billed annually)",
      "Reviewers report the Outlook experience is less mature than Google Calendar, so Microsoft shops should verify coverage first",
      "Expect roughly a week of tuning before the automation matches how you actually work; week one can feel aggressive",
      "Team-level payoff needs broad adoption; one lone enthusiast on Reclaim gets personal value, not org-wide change",
    ],
    bestFor: "Individuals and small teams drowning in meetings who want their calendar to defend real work time",
    url: "https://reclaim.ai",
    verdict:
      "Reclaim.ai is the best value in auto-scheduling: free forever to start, then $10 a seat a month for focus-time defense, habit scheduling, and tasks pulled straight from your project tools. Google Calendar users get the best of it.",
    verdictBox:
      "Reclaim.ai sits on top of the calendar you already use and quietly defends your time: it schedules habits, focus blocks, tasks, and buffers automatically, then reshuffles them as meetings land. The Lite plan is free forever (1 scheduling link, 1 habit, 1-week range) with no card needed. Starter is $10 per seat per month billed annually and Business is $15, adding team analytics, webhooks, and unlimited links and Smart Meetings. Expect a week of tuning, and watch the Attendance Units meter for group Smart Meetings. For meeting-heavy small businesses, it is the most automation for the least money.",
    quickFacts: {
      price: "Lite $0 forever; Starter $10/seat/mo annual ($12 monthly); Business $15/seat/mo annual; Enterprise $22/seat/mo",
      freeTier: "Lite forever: 1 user, 1 scheduling link, 1 habit, 1-week range, no card required",
      setup: "Minutes: connect Google or Outlook calendar, set habits and focus blocks; about a week of tuning",
    },
    whatIsIt: [
      "Reclaim.ai is an AI layer that sits on top of your existing calendar (Google Calendar or Outlook) and manages the space around your meetings. It automatically finds time for habits, focus blocks, tasks, and breaks, and keeps defending that time when new meetings get booked.",
      "It also gives you scheduling links for letting others book you, auto-syncs your Slack status to what you are doing, and pulls tasks from the tools you already use (Asana, ClickUp, Todoist, Jira, Google Tasks) and puts them on your calendar. It does not replace your calendar; it makes your calendar do its job.",
    ],
    businessScenarios: [
      {
        title: "Stop meeting sprawl from eating your deep work",
        description:
          "An owner whose weeks fill up with back-to-back calls sets a daily 2-hour focus block. Reclaim places it in the best available slot daily and reshuffles it when a client books over it, instead of the focus time just evaporating.",
      },
      {
        title: "Habits happen without willpower",
        description:
          "A founder wants weekly reviews, a dentist wants daily prep time, a manager wants 1:1 prep. Set each habit once with a frequency and duration; Reclaim finds slots every week and keeps finding them as the calendar changes.",
      },
      {
        title: "Tasks from your project tool land on the calendar",
        description:
          "A small agency connects Asana to Reclaim: tasks with due dates become calendar blocks sized to their estimates. Instead of a to-do list you ignore, the work is actually scheduled into real time.",
      },
      {
        title: "Booking links that respect your protected time",
        description:
          "A consultant shares a Reclaim scheduling link. Clients see availability that already accounts for focus blocks and buffers, so external bookings never trample the internal commitments you made to yourself.",
      },
      {
        title: "Team-wide focus policy without a meeting about it",
        description:
          "On the Business plan, a team sets shared focus-time and no-meeting policies. Reclaim enforces them across everyone's calendars and the analytics show whether meeting load is actually coming down.",
      },
    ],
    howItWorks: [
      "Connect your calendar. Reclaim plugs into Google Calendar or Outlook and reads your existing events; nothing moves, it just starts managing the open space. (Reviewers note Google support is the most mature.)",
      "Set what to protect. Create habits (recurring commitments), focus-time targets, buffer rules between meetings, and your work hours. Tell Reclaim which are sacred and which can flex.",
      "Connect your tasks. Link Asana, ClickUp, Todoist, Jira, or Google Tasks, and Reclaim places tasks on your calendar by due date and priority, sized to your estimates.",
      "Let it run and tune. As meetings land, Reclaim reshuffles habits, tasks, and buffers automatically and updates your Slack status to match. Mark what it gets wrong in week one; the automation gets noticeably better as you tune priorities.",
    ],
    pricingExplained: [
      "Lite ($0 forever, 1 user): 1 connected calendar, 1-week scheduling range, 1 scheduling link, 1 habit, Google Tasks only, unlimited tasks and buffer time. Genuinely usable for testing whether automated time defense works for you. Starter ($10 per seat per month billed annually, $12 monthly, up to 10 seats): unlimited habits, 3 scheduling links, 3 Smart Meetings, 3 connected calendars, 8-week scheduling range, all task integrations. Business ($15 per seat per month billed annually, $18 monthly, up to 100 seats): unlimited scheduling links and Smart Meetings, 12-week range, delegated access, webhooks, team and people analytics, admin controls, priority support. Enterprise ($22 per seat per month, annual contracts, 100+ seats): SSO, SCIM provisioning, domain capture, dedicated support.",
      "Discounts exist: 50% off for students and educators, 20% for nonprofits and startups, and 20% off for 6 months if you switch from Clockwise. Independent reviewers reckon typical savings land around 30 to 60 minutes of calendar admin per week for meeting-heavy users, which pays for Starter quickly.",
    ],
    pricingCatches: [
      "Smart Meetings with 3 or more attendees consume Attendance Units. Two-person Smart Meetings are free; group ones meter, and an extra 3-pack of units costs $8 a month on Starter (billed annually). Meeting-heavy teams should model this.",
      "Seat caps are tier walls: Starter stops at 10 seats, Business at 100. Growing past a cap means a plan jump, not a gradual bill increase.",
      "The Lite plan's 1-week scheduling range and single scheduling link are deliberately minimal; it is a real product for light use, not a full trial.",
      "Outlook support exists but reviewers consistently describe Google Calendar as the more mature experience. Microsoft-only shops should test carefully before rolling out.",
      "Monthly billing adds $2 to $3 per seat per month over annual on Starter and Business, so the annual discount matters at team scale.",
    ],
    whoShouldGet: [
      "Meeting-heavy individuals on Google Calendar who keep losing focus time",
      "Small teams that want tasks from Asana, Todoist, or Jira to actually get scheduled",
      "Anyone who wants to try automated calendar defense free before paying",
    ],
    whoShouldSkip: [
      "Businesses whose core need is client booking links with payments and CRM sync (Calendly or Cal.com go deeper there)",
      "Teams wanting projects, docs, and notes bundled in (Motion covers more ground, at a higher price)",
      "Outlook-only shops unwilling to test whether the Google-first feature set covers their workflow",
    ],
    comparison: [
      {
        tool: "Reclaim.ai",
        price: "Free; $10-$15/seat/mo annual",
        difference: "Focus-time defense and task auto-scheduling on your existing calendar; booking is secondary",
      },
      {
        tool: "Motion",
        price: "Teams $19-$29/seat/mo; solo $29-$39/mo annual",
        difference: "Fuller all-in-one (projects, docs, notetaker) and more aggressive planning; no free tier, much pricier solo",
      },
      {
        tool: "Calendly",
        price: "Free; $10-$16/seat/mo annual",
        difference: "Booking links only, no defense or task scheduling; better for pure client booking",
      },
      {
        tool: "Cal.com",
        price: "Free (1 user); $12/user/mo annual",
        difference: "Generous free booking plan and API; does not plan your day or defend time",
      },
    ],
    goingDeeper: {
      integrations: [
        "Task sources: Asana, ClickUp, Todoist, Jira, and Google Tasks sync tasks onto your calendar (the Lite plan is Google Tasks only). Slack integration auto-updates your status from your calendar or Zoom meetings, and a Google Workspace add-on lets you insert scheduling links from Gmail.",
        "Webhooks arrive on the Business plan, and services like Zapier and Make connect Reclaim to thousands of other apps for custom automations (create a Reclaim task from a form submission, for example).",
      ],
      privacy: [
        "Reclaim states on its own security pages that it is SOC 2 Type II certified, and runs a public trust center (trust.reclaim.ai) where security documentation, including the audit report, can be requested. It is certified under the EU-US Data Privacy Framework and publishes GDPR help documentation.",
        "Its stated data principles are simple: your data is yours, you can delete it whenever you want, data is protected at rest and in transit, and Reclaim asks only for the minimum permissions each integration needs (its security page lists the exact Google API scopes it uses, feature by feature).",
      ],
      advancedWorkflowTitle: "Self-running week with status sync and task intake",
      advancedWorkflow:
        "Connect Asana (or Todoist) so tasks with due dates auto-schedule into focus blocks, then set habits for your weekly review and daily prep so they are defended like meetings. Turn on Slack status sync so the team can see when you are in deep work without asking. On Business, add a webhook that logs every Smart Meeting scheduled to a spreadsheet, giving you a running record of meeting load the analytics dashboard can be checked against. The week plans and defends itself; you just review it on Monday.",
    },
    faqs: [
      {
        q: "Is the free plan really free forever?",
        a: "Yes. Lite costs $0 with no time limit and no card required: 1 user, 1-week scheduling range, 1 scheduling link, 1 habit, Google Tasks integration, and unlimited tasks and buffer time. It is a real light-use plan, not a trial.",
      },
      {
        q: "Does Reclaim replace my calendar?",
        a: "No. It layers on top of Google Calendar or Outlook. Your events stay where they are; Reclaim manages the open space by placing habits, tasks, focus time, and buffers into it.",
      },
      {
        q: "Will it move my meetings?",
        a: "No. Meetings are fixed. What Reclaim moves is the flexible stuff (habits, tasks, focus blocks) around your meetings as the calendar changes.",
      },
      {
        q: "Does it work with Outlook?",
        a: "Yes, Outlook and Microsoft 365 are supported. Independent reviewers note that some capabilities still feel most mature on Google Calendar, so Outlook shops should run the free tier first and verify the features they need.",
      },
      {
        q: "What are Attendance Units?",
        a: "Smart Meetings (Reclaim's auto-scheduled recurring meetings) with 3 or more attendees consume Attendance Units; 2-person Smart Meetings do not. Extra unit packs cost money (a Starter 3-pack is $8 a month billed annually), so group-meeting-heavy teams should budget for them.",
      },
      {
        q: "Can clients book me through Reclaim?",
        a: "Yes, scheduling links are included (1 on Lite, 3 on Starter, unlimited on Business). They respect your defended time, so bookings never land on top of your focus blocks. For heavy client-booking needs like payments and lead routing, Calendly or Cal.com go further.",
      },
      {
        q: "Is my calendar data safe?",
        a: "Reclaim is SOC 2 Type II certified, certified under the EU-US Data Privacy Framework, and publishes a trust center with security documentation. Its stated principles: your data is yours, deletable anytime, and integrations ask for minimum permissions only.",
      },
    ],
  },
  {
    name: "SavvyCal",
    slug: "savvycal",
    tagline: "Booking links designed around the invitee: calendar overlay and ranked availability.",
    category: "ai-scheduling",
    pricing: "Basic from $10/user/mo (billed annually); Premium $17/user/mo",
    pros: [
      "Best invitee experience in the category: the calendar overlay lets bookers compare their own calendar against yours, and ranked availability lets you steer them toward your preferred times",
      "Simple, honest pricing: two plans, unlimited scheduling links, calendars, and events on both",
      "Team scheduling (collective and round-robin) is included on the cheaper Basic plan, not gated behind a team tier",
      "30-day money-back guarantee means the lack of a free plan stings less",
      "Meeting polls and calendar overlay features are genuinely useful additions most competitors do not have",
    ],
    cons: [
      "No permanent free plan: 'kick the tires for free' is a setup period, not a free tier",
      "Heavy feature gating: reminders and workflows, CRM integrations, Zapier, API and webhooks, custom domains, branding removal, Stripe paid bookings, and delegated access all need Premium at $20 a month",
      "At $10 a user, Basic delivers fewer integrations than Calendly Standard at the same price (Stripe, HubSpot, Zapier are all paid-plan features in Calendly Standard)",
      "Smaller company with a smaller ecosystem: fewer third-party guides, fewer native integrations",
      "No auto-scheduling of tasks or focus-time defense; it is purely a booking tool",
    ],
    bestFor: "Consultants and small teams who care how the booking experience feels for the client",
    url: "https://savvycal.com",
    verdict:
      "SavvyCal is the boutique booking link: the calendar overlay and ranked availability make booking feel effortless for your clients. Budget for Premium if you need automation, branding removal, or payments.",
    verdictBox:
      "SavvyCal's bet is that the booking experience itself matters: its calendar overlay lets invitees compare their own schedule against yours, and ranked availability quietly steers them toward times you prefer, which is ideal for consultants and agencies where the link is a first impression. Basic is $10 per user per month billed annually ($12 monthly) with unlimited links and team scheduling included. The catch is Premium: reminders, CRM integrations, Zapier, the API, custom domains, branding removal, and Stripe paid bookings all sit behind the $17 per user per month annual rate ($20 monthly). There is no free plan, just a try-before-you-buy setup and a 30-day money-back guarantee.",
    quickFacts: {
      price: "Basic $10/user/mo annual ($12 monthly); Premium $17/user/mo annual ($20 monthly)",
      freeTier: "No permanent free plan; try-before-you-buy setup plus 30-day money-back guarantee",
      setup: "Minutes: connect calendars, set availability, share your link",
    },
    whatIsIt: [
      "SavvyCal is a booking-link tool like Calendly, built around one idea: make choosing a time effortless for the person on the other end. Its signature feature is the calendar overlay, which lets your booker see their own calendar events next to your availability when picking a slot.",
      "On your side, ranked availability lets you mark which times you prefer, so bookers gravitate toward your ideal slots without you saying a word. Add time-blocking and time-defense features, team scheduling, and meeting polls, and you get a thoughtfully designed, smaller-scale alternative to the big booking platforms.",
    ],
    businessScenarios: [
      {
        title: "Make booking feel like a favor, not a chore",
        description:
          "A consultant selling high-consideration engagements sends a SavvyCal link instead of a Calendly link. The prospect overlays their own calendar, picks a slot without double-booking themselves, and the interaction feels considered. Small detail, real impression.",
      },
      {
        title: "Steer clients to your best hours",
        description:
          "An agency owner ranks Tuesday and Thursday mornings as preferred. Prospects see those slots first and book them most, protecting the deep-work afternoons without any awkward negotiation.",
      },
      {
        title: "Share the load across a small team",
        description:
          "A three-person support team puts a round-robin link on their contact page. Incoming calls distribute evenly, and the collective link shows combined availability for meetings that need the whole team.",
      },
      {
        title: "Let an assistant book on your behalf",
        description:
          "On Premium, delegated access lets an executive assistant manage the owner's scheduling links and bookings. The owner never touches settings; the assistant runs the calendar.",
      },
      {
        title: "Charge for sessions at booking",
        description:
          "A coach on Premium connects Stripe and takes payment when clients book. Paid bookings arrive pre-paid, and the calendar holds the slot automatically.",
      },
    ],
    howItWorks: [
      "Connect your calendars and conferencing. Link Google Calendar or Outlook (unlimited calendars on both plans) and your video tool, so SavvyCal knows your real availability and can attach meeting links.",
      "Create your scheduling links. Unlimited on both plans: 1:1 calls, team round-robin, collective meetings, and meeting polls for finding a time with a group.",
      "Rank your availability. Mark preferred times so bookers see your ideal slots first, and set time-blocking rules to protect focus hours. This is the feature competitors do not have.",
      "Share the link. Bookers can overlay their own calendar on yours while choosing, pick a time in their own time zone, and get confirmations and (on Premium) automated reminders.",
    ],
    pricingExplained: [
      "Basic ($10 per user per month billed annually, $12 monthly): unlimited scheduling links, calendars, and events; calendar overlay; meeting polls; ranked availability; time-blocking; collective and round-robin team scheduling; reminders and workflows. Premium ($17 per user per month billed annually, $20 monthly): everything in Basic plus CRM integrations, Zapier, API access and webhooks, custom domains, branding removal, delegated access, paid bookings via Stripe, and deeper branding controls.",
      "Annual billing works out to about 2 months free versus monthly. There is no permanent free tier, but SavvyCal advertises a try-before-you-buy setup period and a 30-day money-back guarantee on paid plans, which is the practical way to evaluate it.",
    ],
    pricingCatches: [
      "The Basic-to-Premium gap is the whole story: workflows, CRM integrations, Zapier, the API, custom domains, branding removal, delegated access, and Stripe payments are all Premium-only. That is a lot of functionality behind an $8-per-user-per-month step up.",
      "No free plan means you cannot keep a light-use link alive at $0 the way you can on Calendly or Cal.com. The money-back guarantee is the safety net instead.",
      "Branding removal needs Premium. If a clean, white-labeled link matters to your firm, Basic is the wrong plan no matter how cheap it looks.",
      "Compared feature-for-feature at $10 to $12 a user, Calendly Standard includes Stripe, PayPal, HubSpot, and Zapier at the entry price; SavvyCal puts most of that on Premium.",
    ],
    whoShouldGet: [
      "Consultants, coaches, and agencies where the booking interaction is part of the brand experience",
      "Small teams that want simple round-robin scheduling without a per-seat enterprise plan",
      "Anyone who loves the calendar overlay and ranked availability concept after trying it",
    ],
    whoShouldSkip: [
      "Anyone who needs a free plan (Cal.com's free tier does the core job at $0)",
      "Buyers who need CRM, automation, or API access at the entry price (Calendly Standard $10 beats SavvyCal Basic on integrations)",
      "People who need their schedule planned, not just booked (Reclaim.ai or Motion)",
    ],
    comparison: [
      {
        tool: "SavvyCal",
        price: "$10-$17/user/mo annual",
        difference: "Best invitee booking experience (overlay, ranked availability); no free plan; integrations gated to Premium",
      },
      {
        tool: "Calendly",
        price: "Free; $10-$16/seat/mo annual",
        difference: "More familiar to bookers, deeper integrations at entry price; blander booking experience",
      },
      {
        tool: "Cal.com",
        price: "Free (1 user); $12/user/mo annual",
        difference: "Generous free plan and open source; no overlay or ranked availability",
      },
      {
        tool: "Reclaim.ai",
        price: "Free; $10/seat/mo annual",
        difference: "Booking links plus focus-time defense and task scheduling; booking experience less refined",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native conferencing and calendar connections cover Zoom, Microsoft Teams, Google Calendar, and Outlook. Paid bookings run through Stripe on Premium, and CRM integrations (also Premium) sync bookers into your contact records.",
        "Zapier access is Premium-only, so Basic users are limited to the native integrations. Meeting polls work for group time-finding without needing everyone on the same tool.",
      ],
      api: "API access and webhooks are available on the Premium plan only; Basic has no API access. If programmatic access to your booking data matters, Premium is required.",
      privacy: [
        "SavvyCal does not publish SOC 2, ISO 27001, or GDPR compliance details on its public pages as of this research. If you need a data processing agreement or compliance documentation for procurement, ask their team directly before buying.",
        "Like its competitors it connects to calendars via OAuth, so it does not store your calendar password. For regulated use cases, the lack of published certifications makes Calendly or Reclaim the safer documented choice.",
      ],
      advancedWorkflowTitle: "Preference-steered booking with assistant delegation",
      advancedWorkflow:
        "Rank your availability so Tuesday and Thursday mornings fill first and Friday afternoons stay empty. Put the round-robin link on your contact page so the team shares inbound calls evenly. On Premium, give your assistant delegated access to manage links and bookings, connect Stripe for paid sessions, and push every booking into your CRM. Clients get the smoothest booking experience in the category, and your ideal week fills itself first.",
    },
    faqs: [
      {
        q: "Is there a free plan?",
        a: "No. SavvyCal has no permanent free tier. It offers a try-before-you-buy setup period and a 30-day money-back guarantee on paid plans, which is how you evaluate it risk-free. If you need a real free plan, look at Cal.com or Calendly's free tier.",
      },
      {
        q: "What is the calendar overlay?",
        a: "SavvyCal's signature feature: when your booker opens your link, they can overlay their own calendar next to your availability. They see at a glance which of your open slots also work for them, which cuts double-booking mistakes and makes picking a time faster.",
      },
      {
        q: "What is ranked availability?",
        a: "You rank your available times by preference, and SavvyCal presents your preferred slots more prominently to bookers. It quietly steers people toward the times you want without you having to say 'mornings only.'",
      },
      {
        q: "What is the real difference between Basic and Premium?",
        a: "Basic ($10 per user per month annual) covers the booking experience: unlimited links, overlay, ranked availability, polls, and team scheduling. Premium ($17 annual) adds the business plumbing: reminders and workflows, CRM integrations, Zapier, API and webhooks, custom domains, branding removal, delegated access, and Stripe paid bookings.",
      },
      {
        q: "Can I remove SavvyCal branding from my links?",
        a: "Only on Premium. Branding removal and custom domains are Premium features, so factor the $17 per user per month annual rate into your budget if a white-labeled link matters.",
      },
      {
        q: "Can I take payments through SavvyCal?",
        a: "Yes, on Premium via Stripe: clients pay when they book. Payment processing is not available on Basic.",
      },
      {
        q: "How does it handle time zones?",
        a: "Automatically. Bookers see your availability in their own local time zone, and the overlay works across zones too.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI review management
  // ------------------------------------------------------------------
  {
    name: "NiceJob",
    slug: "nicejob",
    tagline: "Automated review requests built for home-service businesses.",
    category: "ai-review-management",
    pricing: "From $75/mo, no contract",
    pros: [
      "Published pricing with no contract and no sales call: $75 a month for Reviews, $125 a month for Pro, plus a 14-day free trial",
      "Built around the job, not a generic contact list: it connects to Jobber, Housecall Pro, ServiceTitan, and similar tools, then fires the review request when the work is marked complete",
      "Smart routing steers happy customers to Google and unhappy ones to private feedback first, so you can fix problems before they become public one-star reviews",
      "Automatic AI replies to Google reviews on the Pro plan, so your response rate stays high without anyone spending evenings on it",
      "Social proof built in: reviews publish to your website and Facebook automatically, and staff leaderboards show which techs earn the most reviews",
      "Strong user love: 4.8 out of 5 from over 420 G2 reviews (checked Oct 2026)",
    ],
    cons: [
      "The $75 plan covers reviews only; referrals, repeat-booking reminders, and NPS surveys all need the $125 Pro plan",
      "Designed for job-based service businesses, so retail or walk-in businesses may find the workflow awkward",
      "No published pricing for multi-location or franchise accounts: those go through a sales quote",
      "You can reply to Google reviews directly from NiceJob, but Facebook reviews require logging into Facebook itself",
      "Some customers report confusion about which review site their review actually lands on",
    ],
    bestFor: "Single-location service businesses that want reviews collected automatically after every job",
    url: "https://nicejob.com",
    verdict:
      "NiceJob is the simplest honest entry point for review management: $75 a month, no contract, and automation that fires when the job ends. It does one job well, which is exactly what most small shops need.",
    verdictBox:
      "NiceJob is the simplest honest entry point in this category: $75 a month with no contract, and review requests that fire automatically when a job is marked complete. It routes happy customers to Google, catches unhappy ones with private feedback first, and can auto-reply to Google reviews on the Pro plan. It does one job and does it well, which is exactly what most single-location service businesses need.",
    quickFacts: {
      price: "From $75/mo (Reviews); Pro at $125/mo adds referrals, repeat booking, NPS",
      freeTier: "14-day free trial, no card required; no free plan",
      setup: "Connects to your job software in an afternoon; no tech skills needed",
    },
    whatIsIt: [
      "NiceJob is software that asks your customers for reviews automatically. When a job finishes, it sends the customer a text or email asking for a review, follows up if they do not reply, and makes leaving a Google review as easy as a couple of taps.",
      "It also watches your reviews, helps you reply to them with AI-drafted responses, and puts your best reviews on your website and social media to win more business. You stop relying on whoever remembers to ask, and reviews start arriving on their own.",
    ],
    businessScenarios: [
      {
        title: "The ask happens even when the tech forgets",
        description:
          "Your tech finishes a water-heater install and drives to the next job without asking for a review, which is how it always goes. NiceJob sees the completed job in your scheduling software and texts the homeowner a review request that evening. You get the review anyway.",
      },
      {
        title: "Catch the unhappy customer before Google does",
        description:
          "NiceJob asks the customer for a private rating first. Happy customers get sent to Google; an unhappy one gives you feedback privately instead, and you get the chance to fix it before it becomes a public one-star review.",
      },
      {
        title: "Reply to every review without a Sunday-night session",
        description:
          "On the Pro plan, NiceJob's AI drafts and can automatically post replies to your Google reviews every day. You stay responsive and Google-friendly while spending zero evenings writing thank-you notes.",
      },
      {
        title: "See which techs earn reviews",
        description:
          "Staff leaderboards show how many reviews each team member generates, which turns review collection into a friendly competition instead of another chore you have to nag about.",
      },
      {
        title: "Turn old customers into repeat jobs",
        description:
          "On the Pro plan, NiceJob checks in with past customers when they are due for their next service, by text or email, and prompts happy customers to refer friends. Your review tool quietly becomes a rebooking engine too.",
      },
    ],
    howItWorks: [
      "Connect NiceJob to the software you already run: your job scheduler (Jobber, Housecall Pro, ServiceTitan, and many more), or simply upload your customer list. When a job is marked complete, that is the trigger.",
      "NiceJob sends the review request by text or email, timed how you like it, and follows up automatically if the customer does not respond. The customer rates their experience; happy ones land on Google or Facebook, unhappy ones give you private feedback.",
      "New reviews appear in your NiceJob dashboard, where you can reply directly to Google reviews, use AI-drafted replies, or switch on automatic replies on the Pro plan.",
      "Put your reviews to work: NiceJob publishes them to your website with widgets and can share them to your Facebook page, so the reviews you collect also help you close the next customer.",
    ],
    pricingExplained: [
      "Two plans, billed monthly, no contract: Reviews at $75 a month covers automated review requests and reminders by text and email, smart review routing, review monitoring, social sharing, website widgets, AI-assisted replies, and integrations. Pro at $125 a month adds referral campaigns, repeat-booking reminders, competitor insights, NPS surveys, and automatic AI replies.",
      "A 14-day free trial is available with no card, and billing starts the day the trial ends. NiceJob also sells a done-for-you website product separately (Sites, from $99 a month plus a setup fee): that is an add-on, not part of either review plan.",
    ],
    pricingCatches: [
      "The features most businesses want beyond basic review collection (referrals, rebooking reminders, automatic replies) all sit on the $125 Pro plan, so budget for Pro, not $75, if those matter to you.",
      "NiceJob does not publish pricing for multi-location or franchise accounts; those are quoted through sales.",
      "Automatic AI review replies only work on the Pro plan and only for Google reviews. For Facebook and other sites, you reply on those platforms themselves.",
      "Some pricing directories show the plan price varying with your customer count, so confirm your exact quote before paying.",
    ],
    whoShouldGet: [
      "Home-service businesses where a finished job is the natural moment to ask for a review",
      "Owners who want a set-and-forget tool with published pricing and no annual contract",
      "Teams that like light motivation mechanics, like staff leaderboards, to keep reviews flowing",
    ],
    whoShouldSkip: [
      "Retail or walk-in businesses with no job-completion trigger to hook the automation to",
      "Businesses that need messaging, listings, payments, or surveys bundled in (NiceJob is reviews-focused)",
      "Multi-location brands that want centralized roll-up reporting out of the box",
    ],
    comparison: [
      {
        tool: "NiceJob",
        price: "$75/mo (Reviews)",
        difference: "Cheapest published price here; reviews-only focus; no contract",
      },
      {
        tool: "Broadly",
        price: "$79/mo (Reputation AI)",
        difference: "Slightly more, but adds webchat and payments at higher bundles; fuller packages climb fast",
      },
      {
        tool: "Birdeye",
        price: "~$299+/mo per location",
        difference: "Monitors 200+ review sites with real multi-location muscle; far more tool and cost than a single shop needs",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native connections to the tools service businesses already run: Jobber, Housecall Pro, ServiceTitan, JobTread, and dozens of other field-service, CRM, and scheduling apps, so review requests fire automatically when a job is marked complete.",
        "Website widgets that publish your reviews on your site, social sharing to Facebook, and a Zapier app that connects NiceJob to thousands of other apps for custom workflows like logging every new review into a spreadsheet.",
      ],
      privacy: [
        "NiceJob does not publish security certifications such as SOC 2 or ISO 27001 on its public pages. If your business needs them for compliance, ask NiceJob directly before signing.",
        "Review requests go out by SMS and email, which makes consent your responsibility. Only text customers who have agreed to receive texts from your business, and keep records of that consent.",
        "Your reviews and customer lists live in your NiceJob account; export or delete your data before canceling if you want a clean exit.",
      ],
      advancedWorkflowTitle: "Review-sorted weekly scorecard",
      advancedWorkflow:
        "Use NiceJob's Zapier app to log every new Google review into a Google Sheet with the star rating, date, and technician. Add a weekly digest email to yourself with the count of reviews by rating band. In ten minutes a week you can see whether reviews are climbing and which techs are driving them, without opening the dashboard.",
    },
    faqs: [
      {
        q: "Do my techs have to change how they work?",
        a: "No. The review request is triggered by the completed job in your scheduling software, so techs do not need to remember anything or use a new app. If you do not use scheduling software, you can upload customer lists or add customers manually.",
      },
      {
        q: "Will customers be annoyed by the follow-up reminders?",
        a: "NiceJob sends reminders only to customers who have not responded, and you control the timing and the number of follow-ups. In practice, most customers who ignore the first text respond to a polite second one, and that is where much of the review volume comes from.",
      },
      {
        q: "What happens with a bad review?",
        a: "NiceJob asks for a private rating first, so most unhappy customers give you feedback privately instead of posting publicly. If a bad review does land on Google, you can reply directly from NiceJob's dashboard, with AI-drafted help.",
      },
      {
        q: "Can NiceJob reply to reviews for me automatically?",
        a: "Only on the $125 Pro plan, and only for Google reviews: automatic replies post every day around 6pm Eastern. On the $75 plan you get AI-drafted suggestions that you approve yourself, and for Facebook and other sites you reply on those sites.",
      },
      {
        q: "Is there really no contract?",
        a: "Correct. Both plans bill monthly and you can cancel anytime. The 14-day free trial requires no card, and billing starts only when the trial ends.",
      },
      {
        q: "Does NiceJob work for businesses with more than one location?",
        a: "The standard plans are priced per business account rather than per location, but there is no centralized multi-location dashboard like the enterprise tools have. If you run several locations and want roll-up reporting, get a quote from NiceJob sales or look at Birdeye.",
      },
      {
        q: "Will it help my Google ranking?",
        a: "More reviews and a higher response rate are signals Google rewards in local search, and NiceJob automates both. It will not fix other ranking factors like your listing accuracy or website, but review volume and freshness are among the easiest wins a local business can get.",
      },
    ],
  },
  {
    name: "Broadly",
    slug: "broadly",
    tagline: "Reviews plus webchat and payments in one local-business app.",
    category: "ai-review-management",
    pricing: "From $79/mo (Reputation AI)",
    pros: [
      "Affordable entry: $79 a month for Reputation AI Standard, $89 with AI-generated review responses, which keeps reviews in reach of small budgets",
      "More than a review tool: the larger bundles add website webchat, two-way texting, mobile payments and invoicing, so one app can replace several subscriptions",
      "Industry-specific workflows for automotive, construction, home services, and medical, with prebuilt automations that shave setup time in those verticals",
      "Review funnel pages route happy customers to Google and unhappy ones to private feedback, protecting your public rating",
      "A developer API is available for custom integrations, and native integrations cover Jobber, QuickBooks, Clio, Shopmonkey, PetExec, and Housecall Pro",
    ],
    cons: [
      "Pricing beyond the $79 to $89 Reputation AI tier is not transparent: the full platform bundles run $399 to $999 a month and need a sales conversation",
      "A $350 onboarding fee applies to the larger platform plans, and several customer reviews mention billing and refund friction, so read the contract before signing annual",
      "Multi-location accounts are referred into parent company Vendasta's plans, so growing chains face a platform switch, not just an upgrade",
      "Less polished than Podium: smaller team, and independent reviews rate the depth behind enterprise suites as thinner",
      "No published free trial terms; confirm what try-before-you-buy looks like with your rep",
    ],
    bestFor: "Local businesses that want reviews, website chat, and payment collection bundled in one app",
    url: "https://broadly.com",
    verdict:
      "Broadly's Reputation AI tier is a fair $79/month entry for reviews alone; the value story only works if you actually use the bundled webchat and payments at the higher tiers.",
    verdictBox:
      "Broadly starts at $79 a month for Reputation AI (Google and Facebook review management), $89 with AI-drafted responses, which makes it one of the cheaper entries here. The bigger pitch is the bundle: website webchat, two-way texting, and mobile payments in the same app. But the jump to the full platform ($399 to $999 a month plus a $350 onboarding fee) is steep, and pricing beyond the entry tier needs a sales conversation. Start with Reputation AI, and add modules only when the business justifies them.",
    quickFacts: {
      price: "From $79/mo (Reputation AI Standard); full platform $399-$999/mo",
      freeTier: "No free plan; demo through sales, trial terms not published",
      setup: "Guided onboarding; $350 onboarding fee applies to the larger bundles",
    },
    whatIsIt: [
      "Broadly is a local-business platform that starts with reviews and grows from there. At the entry level, it automatically sends review requests by text or email, watches your Google and Facebook reviews, and drafts replies with AI so responding takes two minutes instead of twenty.",
      "On the larger plans it becomes a small operating system: a webchat widget that catches website visitors, two-way texting with customers, mobile invoices they can pay from their phone, and a shared view of every customer interaction. Broadly has been owned by Vendasta since 2023.",
    ],
    businessScenarios: [
      {
        title: "Stop losing after-hours website visitors",
        description:
          "Someone lands on your site at 9pm with a question. Broadly's webchat answers instantly and captures their details, so Monday morning starts with a lead instead of a bounce you never knew about.",
      },
      {
        title: "Get paid without chasing",
        description:
          "You finish a job and text the invoice from Broadly; the customer taps and pays from their phone. The review request can follow right behind the payment, when the customer is happiest.",
      },
      {
        title: "Replies that write themselves",
        description:
          "A new Google review lands and Broadly drafts a response in your tone. You approve or tweak it in seconds instead of staring at a blank reply box for ten minutes.",
      },
      {
        title: "Fit your trade out of the box",
        description:
          "Broadly ships prebuilt workflows for industries like automotive (service write-up to review request), construction (project completion plus invoicing), and medical offices, so the automation matches how your business actually runs.",
      },
      {
        title: "One inbox for everything",
        description:
          "Texts, webchat, review replies, and customer history live in one app with a mobile version, so whoever is on duty sees the full conversation instead of hunting across four tools.",
      },
    ],
    howItWorks: [
      "Connect Broadly to your customer source: integrations with Jobber, Housecall Pro, QuickBooks, Clio, Shopmonkey, PetExec, and others pull in customers automatically, or import your list.",
      "Set up the review request flow: Broadly sends texts or emails after the job or visit, routes happy customers to Google and unhappy ones to private feedback, and follows up with non-responders.",
      "Add the webchat widget to your website (included in the larger plans) so visitors can message you instantly, and set up mobile invoicing if you want payments in the same app.",
      "Monitor everything from the dashboard and mobile app: new reviews, customer messages, invoices, and team activity, with AI-drafted replies ready for review responses.",
    ],
    pricingExplained: [
      "Reputation AI, the standalone review product, has three tiers: Standard at $79 a month for Google and Facebook review management, Pro at $89 a month adding AI-generated review responses, and Premium at call-for-pricing with more automation. This is the tier most small businesses should evaluate.",
      "Beyond that, Broadly sells full platform bundles that add webchat, payments, CRM, listings, SEO, and more: Standard at $399 a month, Pro at $699, Premium at $999, each with a $350 onboarding fee. Independent pricing roundups report legacy plans starting around $249 a month for some existing customers.",
    ],
    pricingCatches: [
      "The $399-to-$999 bundles are a different product category than the $79 review tier. Compare Reputation AI against other review tools, and the bundles against platforms like Podium, not against $75 review apps.",
      "The $350 onboarding fee on the platform bundles is real and non-trivial; factor it into the first-year cost.",
      "Multiple customer reviews mention billing and refund friction. Read the contract, especially any annual terms and the cancellation clause, before signing.",
      "Multi-location accounts get referred into Vendasta's plans rather than upgraded inside Broadly, which can mean re-platforming if you grow into several locations.",
    ],
    whoShouldGet: [
      "Trades and local services (auto, construction, home services, medical) that fit Broadly's prebuilt industry workflows",
      "Businesses that want reviews plus website chat and mobile payments from one vendor",
      "Owners comfortable buying through a sales conversation rather than self-serve checkout",
    ],
    whoShouldSkip: [
      "Anyone who wants a simple reviews-only tool at a published price with no sales process (see NiceJob)",
      "Businesses on a tight budget that will not use the webchat and payments bundle (the value is in the bundle)",
      "Multi-location brands that want to stay on one platform as they grow past a few locations",
    ],
    comparison: [
      {
        tool: "Broadly",
        price: "$79/mo (Reputation AI)",
        difference: "Cheapest bundle path: reviews plus webchat and payments; full platform climbs to $399-$999",
      },
      {
        tool: "Podium",
        price: "~$399/mo (Core)",
        difference: "More polished SMS-first inbox with text-to-pay; substantially more expensive entry point",
      },
      {
        tool: "NiceJob",
        price: "$75/mo (Reviews)",
        difference: "Simpler, reviews-only, published pricing with no contract; no webchat or payments",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native integrations with the tools local businesses run on: Jobber and Housecall Pro for field service, QuickBooks for accounting, Clio for legal, Shopmonkey for auto shops, and PetExec for pet services. The website webchat widget and mobile app (iOS and Android) come with the platform.",
        "A Zapier-style connector ecosystem exists through third-party automation platforms; Broadly's own API covers custom needs where a native integration is missing.",
      ],
      api: "Broadly offers a developer API for custom integrations. Software directories confirm it is available; ask your Broadly rep for the documentation and what access your plan includes.",
      privacy: [
        "Broadly does not publish security certifications such as SOC 2 or ISO 27001 on its public pages. If your business needs them for compliance, ask for documentation before signing.",
        "Broadly describes its medical workflow as HIPAA-aware. Confirm a signed business associate agreement (BAA) with your rep in writing before using Broadly for any patient data.",
        "Texts and emails go to your customers under your business name, so consent and unsubscribe handling are on you; Broadly provides the tooling, but the compliance responsibility stays with the business.",
      ],
      advancedWorkflowTitle: "Payment-then-review sequence",
      advancedWorkflow:
        "Send the mobile invoice the moment the job is done and let the payment notification be the trigger for the review request, while the customer is at peak satisfaction. In Broadly, sequence the two automations so the review ask goes out an hour after a paid invoice, not after the job itself. Paid customers leave reviews at a higher rate, and the timing feels like a thank-you rather than a request.",
    },
    faqs: [
      {
        q: "Is Broadly just a review tool?",
        a: "Not anymore. Reviews are one module inside a broader local-business platform that also includes webchat, texting, payments, and CRM features. If you only want reviews, the $79 Reputation AI tier keeps you in review-only territory; everything above that is the platform.",
      },
      {
        q: "What is the real cost if I want the full platform?",
        a: "Broadly's own published figures show $399, $699, and $999 a month for the platform bundles, plus a $350 onboarding fee. Independent roundups report some customers on legacy plans around $249. Get the quote in writing, including the onboarding fee and the contract term, before committing.",
      },
      {
        q: "How is Broadly different from Podium?",
        a: "Similar idea (reviews plus messaging plus payments), different polish and price. Podium is the more polished, more expensive SMS-first platform starting around $399 a month. Broadly's Reputation AI entry at $79 is far cheaper, and its full platform undercuts Podium's bundles, but independent reviews rate Broadly as less polished with a smaller team behind it.",
      },
      {
        q: "Does Broadly integrate with my scheduling or accounting software?",
        a: "It connects natively with Jobber, Housecall Pro, QuickBooks, Clio, Shopmonkey, and PetExec, among others. If your software is not on the list, ask about the API or a Zapier-style workaround before you buy.",
      },
      {
        q: "Can I try it before I buy?",
        a: "Broadly does not publish free-trial terms, so there is no self-serve trial you can start today. Ask your rep for a demo and for whatever trial or pilot terms they can offer, and get them in writing.",
      },
      {
        q: "What happens if I open a second or third location?",
        a: "Broadly refers multi-location accounts into its parent company Vendasta's plans. That can mean a platform change rather than a simple upgrade, so if you plan to expand, ask exactly what that migration looks like before you invest in Broadly.",
      },
      {
        q: "Is Broadly HIPAA compliant for my medical practice?",
        a: "Broadly describes its medical workflow as HIPAA-aware, but do not take that as a signed guarantee: confirm a business associate agreement (BAA) with your rep in writing before any patient data touches the platform.",
      },
    ],
  },
  {
    name: "Birdeye",
    slug: "birdeye",
    tagline: "The full reputation platform for businesses with multiple locations.",
    category: "ai-review-management",
    pricing: "From ~$299/mo per location (quote only)",
    pros: [
      "Deepest review coverage in this group: it monitors over 200 review sites, including vertical ones like Cars.com, Zocdoc, and TripAdvisor, not just Google and Facebook",
      "The multi-location dashboard genuinely works at scale: a regional manager can compare dozens of locations on review volume, rating, and trends from one screen",
      "Competitor benchmarking tracks rival businesses' review profiles alongside yours, which is genuinely useful for franchisees and regional marketers",
      "AI response suggestions are well rated by users and save real hours when you are replying to a hundred reviews a month",
      "Enterprise-grade security, verified on Birdeye's own security page: SOC 2 Type II, ISO 27001, HIPAA support with a BAA on request, and GDPR with a data processing agreement",
      "Strong track record: about 4.7 out of 5 from over 4,200 G2 reviews (checked Oct 2026)",
    ],
    cons: [
      "Per-location pricing multiplies fast: three locations on the mid tier is roughly $1,000 a month before any add-ons",
      "No reviews-only tier: you buy reviews, listings, messaging, and social together, whether you use all of them or not",
      "Annual contracts with a reported 90-day cancellation notice window; read the renewal clause, including a reported innovation fee on auto-renewal, before signing",
      "Steep learning curve: the platform has enough modules that most users touch a fraction of what they pay for",
      "Overkill for a single location: at one shop you are paying roughly four times what a reviews-only tool costs for overlapping core features",
    ],
    bestFor: "Multi-location businesses and franchises that want reviews, listings, and messaging managed from one place",
    url: "https://birdeye.com",
    verdict:
      "Birdeye is the heavyweight: 200+ review sites, real multi-location dashboards, and verified enterprise security. It earns its keep at three locations and up; at one location it is too much money for too much software.",
    verdictBox:
      "Birdeye is the most complete reputation platform in this group: it monitors over 200 review sites, syncs your business listings, runs messaging and social alongside reviews, and gives multi-location operators one dashboard for every site. The catch is the price: roughly $299 to $449 per location per month on annual contracts, with no published pricing and no self-serve trial. At three locations and up it earns its keep; at one location it is too much money for too much software.",
    quickFacts: {
      price: "~$299-$449/mo per location, annual contracts (reported; Birdeye publishes no prices)",
      freeTier: "No free plan; demo and custom quote through sales",
      setup: "A few hours per location with onboarding help; budget real implementation time",
    },
    whatIsIt: [
      "Birdeye is an all-in-one customer experience platform built for businesses with more than one location. It watches your reviews across 200+ sites, keeps your business listings accurate everywhere, runs two-way messaging with customers, manages social posts, and collects payments, all from one login. Over 80,000 businesses use it daily.",
      "For a single shop that is a lot of software. For a brand with ten or fifty locations, it replaces the chaos of every manager logging into Google, Facebook, and Yelp separately, and gives headquarters one dashboard showing which locations are winning on reputation and which need help.",
    ],
    businessScenarios: [
      {
        title: "See all 30 stores on one screen",
        description:
          "You run a regional chain and used to open thirty Google profiles to check reviews. Birdeye's dashboard shows every location's review volume, average rating, and response rate at once, and flags the stores sliding downward before the quarter ends.",
      },
      {
        title: "Catch the review Google never shows you",
        description:
          "A patient leaves a two-star review on Zocdoc and a driver complains on Cars.com. Google-only tools miss both. Birdeye's 200-site monitoring catches them and routes them to your inbox, so nothing festers unanswered.",
      },
      {
        title: "Benchmark against the competitor across the street",
        description:
          "Birdeye tracks your competitors' review profiles next to yours: their rating, their volume, their trend. When the rival down the road jumps from 4.1 to 4.6, you see it and can ask why, instead of finding out from lost customers.",
      },
      {
        title: "Reply to a hundred reviews without a hundred hours",
        description:
          "AI response suggestions draft replies for high review volumes across locations, and headquarters can set approval rules so local managers handle their own stores while brand standards stay intact.",
      },
      {
        title: "Keep every listing accurate from one place",
        description:
          "Holiday hours change, a phone number changes, a location moves. Birdeye's Listings AI pushes the correction across the major directories at once instead of someone editing thirty profiles by hand.",
      },
    ],
    howItWorks: [
      "Talk to Birdeye sales: there is no self-serve signup. You will share your location count and get a custom quote, then go through guided onboarding for each location, which takes a few hours per site.",
      "Connect your Google Business Profiles and other review sources, and sync your business listings so hours, phone numbers, and addresses are consistent everywhere.",
      "Set up automated review request campaigns by text, email, or QR code, with AI-assisted responses and routing rules for which teams handle which locations.",
      "Manage from the dashboards: corporate sees every location rolled up, local managers see their own stores, and competitor benchmarks and sentiment trends update continuously.",
    ],
    pricingExplained: [
      "Birdeye does not publish pricing; every number below comes from independent pricing trackers and buyer reports in 2026, so treat them as a starting point for your quote. Reported plans: Starter around $299 per location per month (Reviews AI, Listings AI, Messaging AI), Growth around $349 (adds Social AI), Dominate around $449 (adds Chatbot AI). Premium plans for four or more locations are custom-quoted.",
      "Plans are billed per location on annual contracts. There is no free plan; the path in is a demo and a sales quote. Volume discounts exist for larger location counts, but only sales can tell you what yours are.",
    ],
    pricingCatches: [
      "Per-location pricing is the big surprise: a second or third location doubles or triples the bill, and add-ons like extra texting, surveys, and referrals cost more on top.",
      "Annual contracts auto-renew with a reported 90-day cancellation notice window. One independent analysis also reports an innovation fee applied at auto-renewal that makes year two cost more than year one. Get the renewal terms in writing.",
      "There is no reviews-only tier. If all you want is review requests and replies, you are paying for listings, messaging, and social modules you may never open.",
      "Since nothing is published, two similar businesses can get different quotes. Use the reported figures as your opening position in the negotiation, not as the price.",
    ],
    whoShouldGet: [
      "Brands with three or more locations that need one dashboard for reviews across every site",
      "Franchise systems where headquarters wants visibility and local operators want autonomy",
      "Healthcare, automotive, and hospitality groups that need vertical review sites and HIPAA-grade security",
    ],
    whoShouldSkip: [
      "Single-location businesses (you will pay roughly four times what a reviews-only tool costs for overlapping features)",
      "Owners who want transparent pricing and a self-serve trial instead of a sales process",
      "Anyone allergic to annual contracts and per-location multiplication",
    ],
    comparison: [
      {
        tool: "Birdeye",
        price: "~$299-$449/mo per location",
        difference: "Deepest coverage (200+ sites) and best multi-location dashboards; quote-only, annual contracts",
      },
      {
        tool: "Podium",
        price: "~$399/mo (Core)",
        difference: "SMS-first unified inbox with payments; simpler to run, less multi-location analytics depth",
      },
      {
        tool: "NiceJob",
        price: "$75/mo (Reviews)",
        difference: "Reviews-only and a fraction of the cost; no multi-location machinery at all",
      },
    ],
    goingDeeper: {
      integrations: [
        "One of the deepest native integration lists in the industry, organized by vertical: Salesforce and HubSpot for CRM; Dentrix, Athenahealth, and AdvancedMD for healthcare; ServiceTitan, Jobber, and Housecall Pro for contractors; Shopify and Square for retail; QuickBooks and Xero for accounting; plus Zapier for everything else.",
        "Certified Google partnership covering Google reviews, Business Profile, and posts, which matters if Google is where most of your customers find you.",
      ],
      api: "Birdeye publishes REST APIs with developer documentation for custom integrations, plus an MCP server for AI-agent workflows. API access details depend on your plan, so confirm with sales what your tier includes.",
      privacy: [
        "SOC 2 Type II, independently audited for security, availability, and confidentiality, with the report available in Birdeye's Trust Centre.",
        "ISO/IEC 27001 certified for information security management, maintained through annual third-party audits.",
        "HIPAA support for healthcare brands, with workforce training and a business associate agreement (BAA) available on request.",
        "GDPR compliance stated, including data subject rights and a data processing agreement (DPA) available.",
      ],
      advancedWorkflowTitle: "Competitor-gap alert system",
      advancedWorkflow:
        "Use Birdeye's competitor benchmarking plus Zapier: when a tracked competitor's rating moves up or their review volume spikes, log it to a shared sheet and ping your marketing channel. Pair it with Birdeye's sentiment insights on your own reviews to spot the themes competitors are winning on (speed, price, friendliness), and turn the monthly comparison into a standing agenda item for your managers' meeting.",
    },
    faqs: [
      {
        q: "Why does Birdeye not show pricing on its website?",
        a: "Because it prices by location count, plan tier, and contract terms, and it wants that conversation with sales. Independent trackers consistently report roughly $299 to $449 per location per month on annual contracts, but your quote is the only number that matters: use those figures as your negotiating baseline.",
      },
      {
        q: "I have one location. Is Birdeye worth it?",
        a: "Almost certainly not. You would pay roughly $299 a month for a platform whose multi-location dashboards and vertical integrations you will never use, when a $75 reviews-only tool covers the same core job. Birdeye starts making sense around three locations and up.",
      },
      {
        q: "What is the difference between the Starter, Growth, and Dominate plans?",
        a: "They are module bundles, all reported from third-party sources: Starter (about $299) includes Reviews AI, Listings AI, and Messaging AI; Growth (about $349) adds Social AI; Dominate (about $449) adds a website chatbot AI. For pure review management, Starter is more than enough.",
      },
      {
        q: "Can I cancel if it is not working out?",
        a: "Plans are annual contracts, and Birdeye's terms spell out a 90-day cancellation notice window, so you cannot simply stop paying mid-term. Read the contract's cancellation and auto-renewal clauses before signing, and ask about any renewal fees in writing.",
      },
      {
        q: "Does Birdeye really monitor 200+ review sites?",
        a: "That is Birdeye's stated coverage, and it includes vertical-specific sites that Google-only tools miss, like Cars.com for dealerships, Zocdoc for medical, and TripAdvisor for hospitality. If your industry lives on a niche review site, verify your specific sites are covered during the demo.",
      },
      {
        q: "Is Birdeye HIPAA compliant for healthcare?",
        a: "Birdeye states HIPAA support for healthcare brands with workforce training and offers a business associate agreement (BAA) on request. Get the BAA signed before any patient data flows through the platform.",
      },
      {
        q: "How long does implementation take?",
        a: "Plan on a few hours per location with Birdeye's onboarding help, more if you are connecting many integrations. The platform has enough modules that most teams use a fraction of them at first; roll out reviews and listings first, then add messaging and social.",
      },
    ],
  },
  {
    name: "Podium",
    slug: "podium",
    tagline: "Turn every customer text into a review, a payment, or a booking.",
    category: "ai-review-management",
    pricing: "From ~$399/mo (Core)",
    pros: [
      "Best SMS-first workflow in this group: two-way texting, review requests, webchat, and payments all live in one unified inbox per customer",
      "Genuinely easy to use: a 9.3 out of 10 ease-of-use score on G2 and a low learning curve even for non-technical owners",
      "Text-to-pay is a real, working feature: customers pay invoices by text, which shortens the payment chase for service businesses",
      "AI inbox features handle after-hours auto-replies and appointment setting, so leads get answered when nobody is in the office",
      "Strong fit for dealerships, home services, medspas, and dental: anywhere the customer journey involves multiple touches and follow-up, the SMS workflow drives more reviews and more closed sales",
      "Unlimited users on the Pro plan, so the whole team can work the inbox without per-seat math",
    ],
    cons: [
      "Expensive for small businesses: the real monthly invoice often lands at $500 to $800 after add-ons, not the $399 headline",
      "Add-on fees stack: $5 a month per extra phone number, a $5 monthly carrier fee per location, $30 per user per month for phone seats, a reported $500 one-time setup fee, and a $99-a-month AI add-on",
      "Annual contracts are typical, and multiple customer reviews report difficulty canceling before the term ends: read the cancellation clause before signing",
      "The Core plan hard-caps bulk SMS at 250 messages a month with no metered overage, so one message past the cap forces a tier upgrade",
      "AI features score lower than the core inbox in user ratings: the automation layer is less polished than the messaging itself",
    ],
    bestFor: "Businesses that live on texting: dealerships, home services, medspas, dental practices",
    url: "https://podium.com",
    verdict:
      "Podium is the best platform here when customer conversations are the business: reviews arrive as a byproduct of great SMS workflows. It is priced like it, though, and the real invoice runs well past the $399 headline.",
    verdictBox:
      "Podium is the best platform in this group when customer conversations are the business. Every text, webchat message, review reply, payment request, and appointment reminder lives in one inbox, and reviews arrive as a second-order effect of good conversation management, not because the review feature is magic. The cost is real: the $399 Core plan is the headline, but add-ons and fees push real invoices to $500-$800 a month, on annual contracts. If your business runs on SMS, it can be worth it; if you just want reviews, it is overkill.",
    quickFacts: {
      price: "~$399/mo Core (2 locations), ~$599/mo Pro; real invoices often $500-$800 with add-ons",
      freeTier: "No free plan; demo and custom quote through sales",
      setup: "Guided onboarding; reported ~$500 one-time setup fee on phone plans",
    },
    whatIsIt: [
      "Podium is a customer communication platform built for local businesses. Instead of juggling texts, website chat, Facebook messages, and review sites separately, everything lands in one shared inbox organized by customer. You text customers from your business number, they reply, and the whole history stays in one thread.",
      "Reviews are one output of that workflow: after a service or a sale, Podium texts the customer a review invite, and the same inbox handles replies, payments, and follow-up. About 4.5 out of 5 from over 2,100 G2 reviews (checked Oct 2026).",
    ],
    businessScenarios: [
      {
        title: "The text thread becomes a Google review",
        description:
          "Your service advisor texts the customer that their car is ready, they reply thanks, and Podium follows up in the same thread with a review invite. The customer never leaves the conversation they were already in, and your review lands the same day.",
      },
      {
        title: "After-hours leads stop going cold",
        description:
          "A homeowner messages your website chat at 10pm about a roof quote. Podium's AI replies instantly, captures the details, and books the estimate call. By morning there is a qualified lead instead of a missed opportunity.",
      },
      {
        title: "Get paid by text",
        description:
          "The job is done and the invoice goes out as a text with a payment link. The customer pays from their phone, and Podium logs it, which means fewer 'the check is in the mail' conversations and faster cash flow.",
      },
      {
        title: "One inbox for the whole team",
        description:
          "The front desk, the service writer, and the owner all see the same customer threads. Nobody asks 'did anyone reply to Mrs. Chen?' because the answer is visible to everyone with access.",
      },
      {
        title: "Appointment reminders that cut no-shows",
        description:
          "Automated text reminders go out before appointments from the same number customers already know. Fewer no-shows, fuller schedule, and the reminder thread is the same one you later use for the review ask.",
      },
    ],
    howItWorks: [
      "Port your business number into Podium or get a Podium number, and install the webchat widget on your website. Customers keep texting the number they know.",
      "Import or sync your customer contacts, then set up automated review invites that go out by text after a service, a sale, or an appointment.",
      "Work the unified inbox: texts, webchat, Google and Facebook messages arrive in one place, with AI assistance for after-hours replies and review response drafts.",
      "Collect payments by text, send bulk SMS campaigns within your plan's allowance, and track reviews, response rates, and conversation volume from the dashboard.",
    ],
    pricingExplained: [
      "Podium does not publish prices on its own site, so every figure here comes from independent 2026 pricing analyses and should be confirmed with your quote. Reported plans: Core around $399 a month (up to 2 locations, up to 5 phone numbers, 250 bulk SMS a month), Pro around $599 a month (up to 5 locations, 500 bulk SMS, unlimited users, advanced automation and AI), and Signature as a custom enterprise tier. Annual contracts are typical across all plans.",
      "The headline is not the invoice. Budget for the add-ons below, because a small business on Core with phone seats, the AI module, and standard fees realistically pays $530 to $600 a month before SMS overages.",
    ],
    pricingCatches: [
      "Stacking fees: $5 a month per extra phone number, a $5 monthly carrier (10DLC) fee per location, $30 per user per month for Podium Phones seats, a reported one-time $500 setup fee, and a $99-a-month AI add-on. None of this is in the headline price.",
      "Core's 250-message monthly bulk SMS cap has no metered overage: one message past the cap reportedly forces a $200-a-month tier upgrade.",
      "Annual contracts with reported cancellation friction. Multiple customer reviews describe continued billing after attempted cancellation, so get the cancellation process and notice terms in writing before you sign.",
      "Extra locations cost a reported $50 a month each beyond what your plan includes, so multi-location math needs its own quote.",
    ],
    whoShouldGet: [
      "Car dealerships, home-service companies, medspas, and dental practices where SMS is the highest-converting channel",
      "Businesses that will actually use the whole stack: inbox, webchat, payments, and reviews together",
      "Teams that want one shared inbox instead of four separate tools",
    ],
    whoShouldSkip: [
      "Businesses that only want review requests and replies (a $75 to $125 reviews-only tool does that for a fraction of the cost)",
      "Anyone who cannot commit to an annual contract or balks at $500-plus real monthly cost",
      "Shops that rarely text customers and would not use the messaging inbox",
    ],
    comparison: [
      {
        tool: "Podium",
        price: "~$399/mo (Core)",
        difference: "Best SMS-first unified inbox; real cost $500-$800 with add-ons; annual contracts",
      },
      {
        tool: "Birdeye",
        price: "~$299-$449/mo per location",
        difference: "Broader reputation platform with 200+ review sites and multi-location analytics; less messaging polish",
      },
      {
        tool: "Broadly",
        price: "$79/mo (Reputation AI)",
        difference: "Far cheaper entry with webchat and payments bundled; less polished, smaller team",
      },
    ],
    goingDeeper: {
      integrations: [
        "A Zapier app with useful triggers and actions: new-review triggers that log reviews to Google Sheets or ping Slack, and actions that send Podium messages from form submissions, new leads, or CRM updates. Native-style connections cover Salesforce, HubSpot, and ServiceTitan through the automation layer.",
        "Website webchat widget, Google Business Profile messaging, and Facebook Messenger all feed the same unified inbox, so every channel stays in one thread per customer.",
      ],
      api: "Podium publishes a developer API (OAuth-based) with developer documentation for custom integrations. API access tiers vary by plan, so ask your rep what your quote includes; most small businesses will find the Zapier app covers their needs without code.",
      privacy: [
        "Healthcare customers report that Podium offers HIPAA support and will sign a business associate agreement (BAA). Confirm the BAA in writing before any patient data touches the platform.",
        "Podium does not publish a full public security report, so route compliance questions (SOC 2, data retention, data processing agreements) through your sales rep and get answers in writing.",
        "Your customer conversations live in Podium's inbox; clarify data export and deletion terms before signing, especially given the annual contract.",
      ],
      advancedWorkflowTitle: "Review-request timing by sentiment signal",
      advancedWorkflow:
        "Use Podium's Zapier triggers to watch for positive signals before asking: when a customer pays an invoice by text or replies with thanks in the inbox, wait an hour, then send the review invite into that same thread. Asking right after a payment or a thank-you converts far better than a fixed three-day delay, and because it all happens in the existing conversation, it feels personal instead of automated.",
    },
    faqs: [
      {
        q: "What does Podium actually cost per month?",
        a: "Podium does not publish pricing, but independent 2026 analyses consistently report about $399 a month for Core and $599 for Pro, on annual contracts. Add the real extras: $5 per extra phone number, $5 monthly carrier fee per location, $30 per user per month for phone seats, a reported $500 setup fee, and a $99 AI add-on. Most small businesses end up at $500 to $800 a month all-in. Get every fee in your written quote.",
      },
      {
        q: "Is Podium a review tool or a texting tool?",
        a: "It is a texting and messaging platform first, with review generation as one output. That is its strength: reviews arrive as a byproduct of conversations you were already having. If you only want review requests, buy a reviews-only tool for a tenth of the price.",
      },
      {
        q: "Can customers pay me through Podium?",
        a: "Yes. Text-to-pay lets you send payment links by text and customers pay from their phones. It is a real, working feature and one of the main reasons service businesses justify the cost.",
      },
      {
        q: "What happens if I go over the 250 bulk SMS limit on Core?",
        a: "There is no metered overage: independent analyses report that exceeding the cap forces an upgrade to the next tier (about $200 more a month). If you plan SMS campaigns, size the plan for your real volume before signing.",
      },
      {
        q: "Can I cancel if it does not work out?",
        a: "Plans are typically annual contracts, and multiple customer reviews report difficulty canceling before the term ends, including continued billing after cancellation attempts. Get the cancellation process, notice period, and any fees in writing before you sign.",
      },
      {
        q: "Does Podium work for a medical or dental practice?",
        a: "Many practices use it, and healthcare customers report Podium offers HIPAA support with a BAA. Confirm the business associate agreement in writing before any patient data goes through the platform, and check that the messaging workflows fit how your practice books and follows up.",
      },
      {
        q: "How is Podium different from Birdeye?",
        a: "Podium is messaging-first: the unified SMS inbox is the product, and reviews are one output. Birdeye is reputation-first: 200+ review sites, listings, and multi-location dashboards, with messaging alongside. Choose Podium if conversations run your business; choose Birdeye if multi-location reputation analytics is the job.",
      },
    ],
  },
  // ------------------------------------------------------------------
  // AI marketing
  // ------------------------------------------------------------------
  {
    name: "Jasper",
    slug: "jasper",
    tagline: "Premium AI writing platform that keeps your brand voice consistent across teams.",
    category: "ai-marketing",
    pricing: "From $69/mo (Pro); 7-day free trial",
    pros: [
      "Best-in-class brand voice: train it on your writing samples and every draft sounds like you, not a chatbot",
      "Long-form quality and consistency: blog posts and guides come out structured and rarely need a full rewrite",
      "Built for marketing teams: 100+ ready-made AI agents, a no-code workflow builder, and the Canvas collaboration workspace",
      "Unlimited word generation on all plans, so you never watch a credit meter while writing",
      "Serious security posture: SOC 2 and GDPR compliance, and your inputs are never used to train models",
      "Native Surfer SEO integration for writing search-optimized content in one workflow",
    ],
    cons: [
      "Premium pricing with no free plan: a 7-day trial is all you get before paying $69 a month",
      "An older $49 Creator plan appears in many reviews, but the current pricing page (checked October 2026) lists Pro at $69 and Business custom, so confirm plan names at signup",
      "API access is reserved for the custom Business tier, so technical integrations need the expensive plan",
      "The Surfer SEO integration needs a separate Surfer subscription, which is a second bill",
      "Output can still read generic on unfamiliar topics and always needs a human edit before publishing",
      "Overkill for occasional writing: at $20 a month, a general AI chatbot handles basic drafts fine",
    ],
    bestFor: "Marketing teams and serious content producers who need high volumes of on-brand copy",
    url: "https://www.jasper.ai",
    verdict:
      "Jasper is the premium pick for marketing teams that live or die on content quality and brand consistency. Solo writers who just need occasional drafts will find it expensive.",
    verdictBox:
      "Jasper is the closest thing to an AI writing department: train it on your brand voice, and it produces blog posts, ads, emails, and product copy that actually sound like your company. At $69 a month for the Pro plan, it is priced for teams that produce content weekly, not for the occasional blogger. The security posture is genuinely enterprise-grade, which matters if you are feeding it proprietary information. If you just need a draft here and there, a $20 general AI chatbot does the job and this is overkill.",
    quickFacts: {
      price: "From $69/mo (Pro, billed monthly) or $59/mo annual; Business is custom",
      freeTier: "No free plan. 7-day free trial with no credit card required",
      setup: "Signup and writing in minutes; brand voice training takes about an hour of uploading samples",
    },
    whatIsIt: [
      "Jasper is an AI writing platform built specifically for marketing teams. Where a general chatbot gives you generic answers, Jasper is set up around marketing work: blog posts, ad copy, email campaigns, product descriptions, and social posts.",
      "Its standout feature is brand voice. You feed it examples of your writing (or your client's), and Jasper learns to mimic your tone and style, so every piece of content comes out sounding like you. It also holds company knowledge: product details, audiences, and positioning, which it injects into everything it generates.",
    ],
    businessScenarios: [
      {
        title: "Publish blog posts that sound like you wrote them",
        description:
          "You run a marketing team producing two articles a week. With your brand voice trained, each first draft arrives in your tone, with your terminology, so editors spend their time sharpening arguments instead of rewriting introductions.",
      },
      {
        title: "Generate 30 ad variations in an afternoon",
        description:
          "Your ad account needs fresh creative for testing. Jasper's agents generate dozens of headline and copy variations in your brand voice, and you pick the winners instead of staring at a blank doc.",
      },
      {
        title: "Keep five writers consistent",
        description:
          "Freelancers and staff each write differently. Jasper's brand voice and knowledge assets act as a shared baseline, so content from five people reads like it came from one team.",
      },
      {
        title: "Turn one brief into a full campaign",
        description:
          "Jasper Campaigns takes a single brief and produces the blog post, the email sequence, the social posts, and the ad copy as a coordinated set, instead of you prompting each piece separately.",
      },
      {
        title: "Write SEO content without switching tools",
        description:
          "The Surfer SEO integration scores your draft for search optimization while you write, so you publish content that is both readable and rank-ready in one workflow (needs a separate Surfer subscription).",
      },
    ],
    howItWorks: [
      "Choose how you want to start: pick one of 50+ templates for a specific task (blog intro, ad headline, email subject line), or open Jasper Chat and describe what you need in plain language.",
      "Train your brand voice. Paste or upload writing samples and answer a few questions about your tone. Jasper analyzes the samples and applies that voice to everything it generates from then on.",
      "Add company knowledge. Upload product details, audience descriptions, and positioning documents as knowledge assets, so Jasper stops writing generic copy and starts writing your copy.",
      "Generate, edit in Canvas, and publish. Draft in the Canvas workspace where you can rewrite sections, run brand-voice checks, and collaborate with teammates, then export or push content out through integrations like Google Docs, Webflow, or Zapier.",
    ],
    pricingExplained: [
      "Jasper currently sells two plans (verified on its pricing page in October 2026). Pro is $69 per month, or $59 per month billed annually, and includes unlimited word generation, brand voices, knowledge assets, audience profiles, the Canvas workspace, AI image generation, and a plagiarism checker. Business is custom-priced with a 12-month minimum and adds unlimited everything, advanced agents, Jasper Grid, the no-code agent builder, API access, SSO, and a dedicated manager.",
      "There is no free plan, only a 7-day free trial on Pro. A 20% nonprofit discount is available.",
    ],
    pricingCatches: [
      "Many review sites still quote a $49 Creator plan. That plan no longer appears on Jasper's live pricing page, so treat any source quoting it as outdated and confirm current plan names before you pay.",
      "API access, SSO, and audit logs are Business-tier features. If you need to plug Jasper into your own systems programmatically, budget for the custom tier.",
      "The Surfer SEO integration is included as a connector, but Surfer itself is a separate paid subscription.",
      "Unlimited words means unlimited generation, not unlimited quality control. Long-form pieces still need a human editor, and poor inputs produce poor outputs faster.",
    ],
    whoShouldGet: [
      "Marketing teams producing content weekly who need consistent brand voice across writers",
      "Businesses whose content is a revenue channel: blogs, SEO, paid ads, email campaigns",
      "Regulated or careful businesses that want SOC 2 and GDPR compliance with no model training on their data",
    ],
    whoShouldSkip: [
      "Solo writers who produce the occasional post (a $20 general AI tool covers this)",
      "Teams that need a public API without paying for a custom enterprise tier",
      "Anyone expecting publish-ready output with zero editing; Jasper drafts well but still needs a human",
    ],
    comparison: [
      {
        tool: "Jasper",
        price: "$69/mo (Pro)",
        difference: "Premium brand voice and team workflow platform; best quality floor in the category",
      },
      {
        tool: "Copy.ai",
        price: "$29/mo (Chat)",
        difference: "Cheaper, multi-model access, strong workflow automation; brand voice and long-form quality are weaker",
      },
      {
        tool: "ChatGPT Plus",
        price: "$20/mo",
        difference: "General AI with excellent drafts when prompted well, but no brand voice training or marketing templates",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native connections include Surfer SEO, Grammarly, Copyscape, Google Docs, Google Sheets, Slack, Webflow, WordPress, and Zapier, which extends Jasper to thousands of other apps.",
        "Jasper claims 1,000+ integrations and extensions overall, including MCP and agent support for embedding Jasper's capabilities into existing marketing stacks.",
      ],
      api: "API access is a Business-tier feature (custom pricing, 12-month minimum). On lower tiers there is no public self-serve API, so Zapier or Make are the practical integration route.",
      privacy: [
        "Jasper publishes SOC 2 and GDPR compliance and states that customer inputs are never used to train models or shared across accounts.",
        "Enterprise-grade features on the Business tier include SSO, AI audit logs, and admin controls for managing who can access brand voices and knowledge assets.",
        "AI-generated content still needs human review: Jasper itself notes that outputs may not be completely accurate, so do not publish straight from the draft.",
      ],
      advancedWorkflowTitle: "Brand-consistent content pipeline with human approval",
      advancedWorkflow:
        "Connect Jasper's Canvas to your CMS through Zapier: when a draft is marked final in Jasper, it creates a draft post in WordPress or Webflow automatically, tagged for review. Add a Slack notification to your editor so every finished draft lands in the same channel with its plagiarism-check result. The team writes and generates in Jasper; publishing stays a one-click human decision, and the brand voice stays locked in because it is set at the account level, not per writer.",
    },
    faqs: [
      {
        q: "Is Jasper better than ChatGPT for marketing content?",
        a: "For structured marketing work, usually yes. Jasper's brand voice training, 50+ templates, campaign workflows, and knowledge assets mean less prompting and more consistent output than a general chatbot. For one-off drafts, ChatGPT at $20 a month is fine and Jasper is not worth the premium.",
      },
      {
        q: "What happened to the $49 Creator plan?",
        a: "Jasper retired it. Its current pricing page (checked October 2026) lists Pro at $69 a month and a custom Business tier. If a review quotes Creator at $49, that pricing is outdated.",
      },
      {
        q: "Does Jasper train its AI on my content?",
        a: "No. Jasper states that customer inputs are never used to train models or shared across accounts, and it holds SOC 2 and GDPR compliance.",
      },
      {
        q: "Can Jasper write a full blog post for me?",
        a: "Yes, including long documents, and its output is generally more structured than competitors'. But it still needs human editing for facts, originality, and final polish before publishing.",
      },
      {
        q: "Do I need the Surfer SEO subscription?",
        a: "Only if you want the SEO scoring inside Jasper. The integration is built in, but Surfer itself is a separate paid product. If SEO is not your focus, Jasper works fine without it.",
      },
      {
        q: "Can my whole team use one Jasper account?",
        a: "Pro includes up to 5 seats with role-based permissions, so a small team can share brand voices, templates, and campaigns. Larger teams need the Business tier.",
      },
    ],
  },
  {
    name: "Copy.ai",
    slug: "copy-ai",
    tagline: "AI writing plus workflow automation for repetitive marketing and sales tasks.",
    category: "ai-marketing",
    pricing: "From $29/mo (Chat); automation tiers from $249/mo",
    pros: [
      "Chat plan is genuine value: $29 a month, 5 seats, unlimited words, and access to OpenAI, Anthropic, and Gemini models in one workspace",
      "Workflow automation is the real differentiator: multi-step pipelines that research, enrich, and personalize at scale",
      "90+ templates remove the need to learn prompt engineering for common marketing tasks",
      "SOC 2 Type II compliance with a stated zero-training policy on customer data",
      "Easy enough for non-technical marketers, with a visual workflow builder",
    ],
    cons: [
      "The pricing cliff is brutal: $29 a month for Chat, then $249 for Agents, then $1,000+ a month for Growth, with nothing in between",
      "Whether a free plan is still open to new signups is unclear: some billing FAQs say it was sunset, so confirm at signup",
      "Long-form content can feel generic or obviously AI-written and needs editing",
      "Positioned as a go-to-market platform now, which is overbuilt if you just want blog and social copy",
      "API access and bulk workflow runs are gated behind a custom Enterprise contract",
      "Mixed reviewer reports on support responsiveness and billing experiences",
    ],
    bestFor: "Teams that produce the same marketing copy repeatedly and want to automate the busywork",
    url: "https://www.copy.ai",
    verdict:
      "Copy.ai's $29 Chat plan is one of the best-value AI writing deals available. Just know that the automation features that make headlines live on tiers costing 8x to 35x more, and plan accordingly.",
    verdictBox:
      "Think of Copy.ai as two products sharing a name. The Chat plan at $29 a month is a bargain: unlimited writing across three AI model families for five people, with templates that make short-form marketing copy fast. The other product is an AI workflow automation platform for sales and marketing teams, and that one starts at $249 a month and climbs to $1,000, $2,000, or $3,000. The danger is building your processes on the cheap tier and assuming the automation tier costs a little more. It does not. Buy the Chat plan for what it is, and budget honestly for what the automation costs.",
    quickFacts: {
      price: "Chat $29/mo (5 seats); Agents $249/mo; Growth $1,000/mo and up (annual)",
      freeTier: "A free starting tier has existed, but new-signup availability is unclear from current sources; new Chat accounts get a one-time grant of 200 workflow credits",
      setup: "Signup and writing in minutes; building reliable workflows takes an afternoon of setup and testing",
    },
    whatIsIt: [
      "Copy.ai is an AI platform for marketing and sales content. At its simplest, it is a writing workspace: you describe what you need, and it drafts ads, emails, social posts, and blog outlines using models from OpenAI, Anthropic, and Google.",
      "Its deeper product is workflow automation. Instead of writing one piece of copy at a time, you build reusable pipelines: a workflow can pull a list of prospects, research each one, write a personalized email for each, and hand the results to your sales team. Since its 2025 acquisition by Fullcast, the company has leaned hard into this go-to-market automation positioning.",
    ],
    businessScenarios: [
      {
        title: "Write 20 ad variations before lunch",
        description:
          "You need fresh creative for a Facebook campaign. Describe the product once, pick a template, and Copy.ai generates dozens of headline and body variations. You spend your time picking winners, not writing first drafts.",
      },
      {
        title: "Personalize outreach at scale",
        description:
          "On the Agents tier, a workflow takes your prospect list, researches each company, and drafts a tailored first line or full email for each one, so your outreach stops sounding like a template.",
      },
      {
        title: "Keep LinkedIn content consistent",
        description:
          "Train a content agent once on your voice and topics, and your team generates on-brand LinkedIn posts every week without re-explaining the brief each time.",
      },
      {
        title: "Turn one webinar into a month of content",
        description:
          "Feed the webinar transcript into a workflow that outputs the blog summary, the email recap, and five social posts, each formatted for its channel.",
      },
      {
        title: "Enrich leads before they reach sales",
        description:
          "A workflow pulls new signups, looks up company details, scores fit, and routes the hot ones to sales with a summary, so reps call with context instead of cold.",
      },
    ],
    howItWorks: [
      "Start in Chat: describe what you need or pick from 90+ templates, choose your AI model (OpenAI, Anthropic, or Gemini), and generate. Unlimited words on paid plans.",
      "Save what works. Turn your best prompts into reusable workflows in the visual builder: chain steps like research, generate, enrich, and format.",
      "On the Agents tier, train Content Agents: reusable AI setups that produce the same content shapes consistently, like your weekly LinkedIn posts or outbound emails.",
      "Connect your stack. Pipe workflow results into HubSpot, Salesforce, Slack, or Google Sheets through native integrations or Zapier, so finished copy lands where your team already works.",
    ],
    pricingExplained: [
      "Copy.ai's current self-serve pricing (checked September 2026): Chat is $29 a month, or $24 a month billed annually, and covers 5 seats with unlimited words in Chat and access to OpenAI, Anthropic, and Gemini models. It does not include a monthly workflow credit allowance; new accounts get a one-time grant of 200 bonus credits.",
      "Agents is $249 a month, covers up to 10 seats, and adds 10,000 workflow credits a month plus Content Agent Studio. Growth is $1,000 a month (billed annually) with 20,000 workflow credits; Expansion is $2,000; Scale is $3,000. Enterprise is custom-priced and adds API access, bulk runs, and 20+ integrations.",
    ],
    pricingCatches: [
      "The gap between Chat ($29) and Agents ($249) is the whole story. There is no mid-tier for a growing team: the next step after Chat is roughly 8x the price.",
      "Workflow credits are consumed by actions (generation, research, API use), not words, so estimate your monthly workflow runs before choosing a tier.",
      "Growth, Expansion, and Scale are annual-billing only, and API access with bulk workflow runs is Enterprise-only, so programmatic use lands in a sales conversation.",
      "Older reviews quote $49 Starter and $99 Pro plans. Those tiers are phased out and no longer appear on the live pricing page.",
    ],
    whoShouldGet: [
      "Small teams that want cheap, multi-model AI writing with unlimited words",
      "Marketing and sales teams doing repetitive, templated work they can automate into workflows",
      "Anyone who wants to test properly first (confirm current free or trial terms at signup)",
    ],
    whoShouldSkip: [
      "Businesses between Chat and Agents in budget: there is no tier for you",
      "Teams that need a public API without an enterprise contract",
      "Anyone who only needs occasional drafts and finds even $29 a month hard to justify",
    ],
    comparison: [
      {
        tool: "Copy.ai (Chat)",
        price: "$29/mo",
        difference: "Best-value writing workspace; multi-model, 5 seats, unlimited chat words",
      },
      {
        tool: "Jasper",
        price: "$69/mo (Pro)",
        difference: "Better brand voice and long-form quality; more than double the price for the writing tier",
      },
      {
        tool: "DIY with Zapier + ChatGPT",
        price: "~$20-40/mo",
        difference: "Build your own automations for less; more setup work and no ready-made templates",
      },
    ],
    goingDeeper: {
      integrations: [
        "Native integrations include Salesforce, HubSpot, Gong, Outreach, Slack, Google Sheets, Google Docs, WordPress, Shopify, Buffer, Notion, and Airtable, plus a Zapier app that connects workflow runs to thousands of other tools.",
        "Workflows can trigger on CRM stage changes in Salesforce and HubSpot and write results back, which is the core of its go-to-market automation pitch.",
      ],
      api: "There is no public self-serve API on Chat or Agents tiers. API access and bulk workflow runs are Enterprise-only features, priced by custom contract.",
      privacy: [
        "Copy.ai reports SOC 2 Type II certification and GDPR alignment, with a stated policy that customer data is not used to train underlying models.",
        "Workflows that touch your CRM use OAuth connections; review the permission scopes before granting write access to customer records.",
      ],
      advancedWorkflowTitle: "Self-running outbound personalization",
      advancedWorkflow:
        "On the Agents tier, build a workflow that runs weekly: it pulls new prospects from your CRM, researches each company's recent news, drafts a personalized first email referencing that news, and saves drafts to a review queue instead of sending. Your salesperson spends Monday morning approving or tweaking 30 personalized drafts instead of writing them from scratch. Approval stays human; the research and drafting are automated, and the workflow credits are predictable because the run count is fixed.",
    },
    faqs: [
      {
        q: "Is Copy.ai free?",
        a: "Copy.ai has offered a free tier with 2,000 words a month, but its billing FAQs have said the free plan was sunset for new customers, while other pages still mention getting started free. Treat the free plan as uncertain and confirm what is available when you sign up. The paid Chat plan starts at $29 a month.",
      },
      {
        q: "What is the difference between Chat and Agents?",
        a: "Chat ($29/month) is the writing workspace: unlimited words, 5 seats, multiple AI models. Agents ($249/month) adds the automation layer: 10,000 workflow credits a month and Content Agent Studio for training reusable content agents. Buy Chat for writing, Agents for automation.",
      },
      {
        q: "Why does pricing jump from $29 to $249?",
        a: "Because they are different products. Chat is priced like a writing tool; Agents and above are priced like go-to-market automation software for teams. The jump catches people who assume automation is a small add-on, so plan for it before you build processes on the platform.",
      },
      {
        q: "Which AI models does Copy.ai use?",
        a: "It offers access to models from OpenAI, Anthropic, and Google (Gemini) in one subscription, and you can switch models per task.",
      },
      {
        q: "Can Copy.ai write long blog posts?",
        a: "It can, but long-form is not its strength. Reviews consistently say long pieces come out generic or repetitive and need real editing. Jasper or a human writer are better for long-form.",
      },
      {
        q: "Does Copy.ai integrate with my CRM?",
        a: "Yes, natively with Salesforce and HubSpot, plus Zapier for everything else. Workflow results can be written back to CRM records automatically.",
      },
    ],
  },
  {
    name: "HubSpot",
    slug: "hubspot",
    tagline: "Free CRM plus marketing, sales, and service tools in one connected platform.",
    category: "ai-marketing",
    pricing: "Free; paid from $20/seat/mo (Marketing Hub Starter)",
    featured: true,
    pros: [
      "The free plan is genuinely useful: a real CRM, 2,000 branded email sends a month, forms, and live chat for 2 users, free forever with no credit card",
      "Everything in one system: contacts, email, landing pages, automation, and sales pipeline share one database, so nothing falls through integration cracks",
      "1,500+ integrations, so it plugs into nearly any tool you already use",
      "Breeze AI is built across the platform: writing help, prospecting, and data enrichment without a separate AI subscription",
      "HubSpot Academy offers free certifications and training, which genuinely shortens the learning curve",
    ],
    cons: [
      "The Starter-to-Professional cliff is one of the steepest in software: from about $20 a seat to $890 a month plus a mandatory $3,000 onboarding fee",
      "Pricing is a maze of hubs, seats, contacts, and credits, which makes the true cost hard to predict",
      "Contact-based pricing means your bill grows as your list grows, and overages apply automatically",
      "Real automation, custom reporting, and removing branding all require paid tiers",
      "Not purpose-built for ecommerce email flows like abandoned cart; dedicated ecommerce tools do those better",
    ],
    bestFor: "Growing businesses that want their CRM, email marketing, and sales pipeline in one place",
    url: "https://www.hubspot.com",
    verdict:
      "HubSpot's free tier is the best starting point in marketing software, full stop. Just go in with eyes open: the upgrade path from Starter to Professional is a cliff, not a ramp.",
    verdictBox:
      "HubSpot is the rare marketing platform that is genuinely free to start: two users get a real CRM, 2,000 email sends a month, forms, and chat without paying anything. For a small business, that covers the first year or two of marketing infrastructure. Where it bites is growth: Starter is a modest $20 a seat, but the moment you need real automation and reporting, you are looking at $890 a month plus a mandatory $3,000 onboarding fee. Used deliberately, free-then-Starter is unbeatable value. Used carelessly, it becomes one of the most expensive tools you own.",
    quickFacts: {
      price: "Free; Starter $20/seat/mo (list; promotional $7 for new customers); Pro $890/mo; Enterprise $3,600/mo",
      freeTier: "Free forever: 2 users, CRM, 2,000 branded email sends/month, no credit card required",
      setup: "Free tier set up in an afternoon; Professional realistically needs the paid onboarding",
    },
    whatIsIt: [
      "HubSpot is an all-in-one platform for marketing, sales, and customer service, built around a free CRM. The CRM is the shared database: every contact, email, deal, and support ticket lives in one record that your whole team can see.",
      "For marketing specifically, it covers email campaigns, landing pages, forms, social media, automation workflows, and reporting. Its AI layer, called Breeze, adds writing assistance, prospecting, and data enrichment across the platform, metered by HubSpot Credits.",
    ],
    businessScenarios: [
      {
        title: "Run your first email newsletter for free",
        description:
          "You have 800 contacts and send a monthly newsletter. The free plan's 2,000 monthly sends cover it completely, with signup forms feeding new subscribers straight into your CRM, at zero cost.",
      },
      {
        title: "Never lose track of a lead again",
        description:
          "A prospect fills out your contact form, downloads a guide, and opens three emails. HubSpot records all of it on one timeline, so when you call, you know exactly what they have seen.",
      },
      {
        title: "Automate your follow-up",
        description:
          "On Starter and up, a new lead automatically gets a welcome email series, gets assigned to the right person, and gets a reminder task if nobody follows up. The manual chasing disappears.",
      },
      {
        title: "Prove which marketing actually works",
        description:
          "On Professional, every deal ties back to the campaign, email, or page that sourced it, so you can see which half of your marketing budget is pulling its weight.",
      },
      {
        title: "Enrich leads with AI",
        description:
          "Breeze AI fills in company details, drafts outreach, and scores leads using your HubSpot Credits, so a two-person team works with the context of a much bigger one.",
      },
    ],
    howItWorks: [
      "Import your contacts (or start from zero) into the free CRM. Every email, form fill, and website visit attaches to the contact's timeline automatically.",
      "Build your marketing assets: drag-and-drop emails and landing pages, signup forms, and live chat, all pulling from the same contact data.",
      "Set up automation. Even simple workflows on Starter (welcome series, lead assignment) run on their own; Professional unlocks lead scoring, branching logic, and multi-channel campaigns.",
      "Measure and iterate. Dashboards show opens, clicks, and (on paid tiers) revenue attribution, and Breeze AI helps draft the next round of content.",
    ],
    pricingExplained: [
      "HubSpot prices by hub, seat, and contacts. The free tools cost $0 forever for 2 users, including the CRM, 2,000 branded email sends a month, forms, and live chat. Marketing Hub Starter lists at $20 per seat per month (a limited-time $7 per seat offer for new customers has been running), includes 1,000 marketing contacts and 500 HubSpot Credits for AI features.",
      "Marketing Hub Professional is $890 a month (annual commitment), includes 3 seats and 2,000 marketing contacts, and requires a one-time $3,000 onboarding fee. Enterprise is $3,600 a month with 5 seats and 10,000 contacts. Additional contacts and seats raise the price from there, and extra HubSpot Credits cost about a cent each.",
    ],
    pricingCatches: [
      "The Starter-to-Professional step is the whole decision: roughly 40x the price for a small team, with no tier in between. Upgrade only when you need Professional's automation depth, not just because your list grew.",
      "Onboarding fees are mandatory at Professional ($3,000) and Enterprise ($7,000), which makes the first year much more expensive than the sticker price.",
      "Contact overages apply automatically as your list grows past your tier's allowance, so an unexpected import can bump your bill without warning.",
      "The $7 per seat Starter price is promotional for new customers; the list price is $20, so budget for the real number.",
    ],
    whoShouldGet: [
      "Small businesses that want a free, real CRM with email marketing built in",
      "Growing teams that will use one platform for marketing, sales, and service instead of five tools",
      "Businesses willing to invest in learning one system deeply (HubSpot Academy helps)",
    ],
    whoShouldSkip: [
      "Anyone who just needs to send newsletters and will never use a CRM (Mailchimp or Constant Contact are simpler and cheaper)",
      "Ecommerce stores whose core need is abandoned-cart and post-purchase email flows",
      "Teams that need advanced automation now but cannot stomach $890 a month plus onboarding",
    ],
    comparison: [
      {
        tool: "HubSpot",
        price: "Free / $20/seat/mo (Starter)",
        difference: "Best free start; CRM included; upgrade path is a cliff",
      },
      {
        tool: "Mailchimp",
        price: "From $13/mo",
        difference: "Simpler and cheaper for pure email; no real CRM; costs grow with list size",
      },
      {
        tool: "Constant Contact",
        price: "From $12/mo",
        difference: "Easiest email tool with phone support; weaker automation; no CRM",
      },
    ],
    goingDeeper: {
      integrations: [
        "HubSpot lists 1,500+ integrations in its app marketplace, including Salesforce, Slack, Shopify, Gmail, Outlook, Zoom, Stripe, and WordPress. Most connect in a few clicks with no code.",
        "Because the CRM is the center of the platform, integrations write to the same contact record your marketing uses, which is the main advantage over bolting a CRM onto an email tool.",
      ],
      api: "HubSpot publishes a full public developer API with extensive documentation. Developers build custom integrations through private apps or OAuth, and API access is available on all tiers including free, with rate limits that scale by plan.",
      privacy: [
        "Your customer data lives inside HubSpot's platform, and you control user roles, data exports, and deletion. Paid tiers add granular permissions and audit features for larger teams.",
        "HubSpot publishes its security and compliance program on its trust center. If you need specific certifications for your industry, verify them there before committing, since requirements vary by plan and data region.",
      ],
      advancedWorkflowTitle: "Automatic lead scoring with sales handoff",
      advancedWorkflow:
        "On Professional, build a workflow that scores every lead on engagement: email opens, page visits, and form fills add points, and inactivity subtracts them. When a lead crosses your threshold, the workflow creates a task for the assigned salesperson, enrolls the lead in a personal follow-up sequence, and posts to a Slack channel. Sales only touches leads that have shown real interest, and every touch is logged on the contact timeline, so nothing depends on anyone remembering to check a spreadsheet.",
    },
    faqs: [
      {
        q: "Is HubSpot really free?",
        a: "Yes, for real: 2 users, a working CRM, 2,000 branded email sends a month, forms, and live chat, free forever with no credit card. The limits are branding on emails, basic reporting, and no automation. It stops being free when you need those.",
      },
      {
        q: "Why does everyone warn about HubSpot pricing?",
        a: "Because the jump from Starter (about $20 a seat) to Professional ($890 a month plus $3,000 onboarding) is enormous, and there is no middle tier. The pricing is also genuinely complex: hubs, seats, contacts, and AI credits all move the bill. Start free, upgrade to Starter deliberately, and only go Professional when you need its automation.",
      },
      {
        q: "What are HubSpot Credits?",
        a: "Credits are how HubSpot meters its Breeze AI features. Starter includes 500 a month, Professional 3,000, Enterprise 5,000, and extras cost about a cent each. They reset monthly and do not roll over.",
      },
      {
        q: "Do I need the paid onboarding?",
        a: "At Professional and Enterprise, yes: the onboarding fee ($3,000 and $7,000 respectively) is mandatory, not optional. Budget it into your first year.",
      },
      {
        q: "Is HubSpot good for ecommerce email?",
        a: "It works, especially with the Shopify integration, but it was not purpose-built for ecommerce flows like abandoned cart and post-purchase series. Tools like Klaviyo or Omnisend specialize in those.",
      },
      {
        q: "Can I use HubSpot just as a CRM and keep Mailchimp for email?",
        a: "You can, and many businesses do exactly that during the transition. HubSpot integrates with Mailchimp, so contacts sync between the two. The tradeoff is paying for two tools and maintaining the sync.",
      },
      {
        q: "What happens to my data if I cancel?",
        a: "You can export your contacts and core data before canceling. Plan the export ahead of time, because rebuilding automation workflows in a new tool is the painful part of leaving, not the data.",
      },
    ],
  },
  {
    name: "Mailchimp",
    slug: "mailchimp",
    tagline: "The best-known email marketing platform, with deep integrations and serious automation.",
    category: "ai-marketing",
    pricing: "Free; paid from $13/mo (Essentials)",
    pros: [
      "300+ native integrations: if a tool you use has only one email integration, it is usually Mailchimp",
      "Easy drag-and-drop builder that a non-technical owner can learn in an afternoon",
      "Serious automation on Standard: up to 200 multi-step flows with branching, included from $20 a month",
      "Intuit Assist generative AI is included at no extra cost on Standard and up",
      "14-day free trials on paid plans, plus a pay-as-you-go credit option for infrequent senders",
      "Owned by Intuit, so it is not going anywhere; stability matters for a tool holding your customer list",
    ],
    cons: [
      "The free plan was cut sharply in January 2026: now just 250 contacts and 500 emails a month, with Mailchimp branding and no automation",
      "Unsubscribed and non-subscribed contacts still count toward your billing tier, so you pay for people who will never open another email",
      "Prices climb fast as your list grows: a 5,000-contact list costs $75 to $100 a month, and one extra contact can bump you into the next tier",
      "Transactional email is a separate product costing from $20 a month for a block of 25,000 emails, on top of your plan",
      "SMS is a paid add-on, not included in any plan",
      "Premium at $350 a month is a big leap with little in between for mid-size senders",
    ],
    bestFor: "Small businesses that mainly need email newsletters, promotions, and ecommerce automation",
    url: "https://mailchimp.com",
    verdict:
      "Mailchimp is the safe, capable default for email marketing, especially if you sell online. Just keep your list clean, because its billing counts contacts you cannot even email.",
    verdictBox:
      "Mailchimp earned its reputation: it is easy to use, connects to everything, and its automation on the $20 Standard plan is genuinely powerful for the price. The catch is the billing model. Unsubscribed contacts still count toward your tier, prices rise steeply as your list grows, and transactional emails cost extra. A business with a clean, engaged list gets excellent value. A business with years of accumulated unsubscribes pays for ghosts. Archive ruthlessly and it stays affordable.",
    quickFacts: {
      price: "Free; Essentials from $13/mo; Standard from $20/mo; Premium from $350/mo (all scale with contacts)",
      freeTier: "Free: 250 contacts, 500 sends/month, Mailchimp branding, no automation, support for first 30 days only",
      setup: "Under an hour for basic campaigns; automation flows take a day to build and test",
    },
    whatIsIt: [
      "Mailchimp is an email marketing platform, now owned by Intuit. You build a list of contacts, design emails with a drag-and-drop builder, and send newsletters, promotions, and automated sequences. It also handles landing pages, signup forms, and basic audience analytics.",
      "For online stores it goes further: abandoned-cart emails, post-purchase follow-ups, and product recommendations that pull straight from your store's catalog through integrations with Shopify, WooCommerce, and others.",
    ],
    businessScenarios: [
      {
        title: "Send a weekly newsletter that looks professional",
        description:
          "You run a local business with 1,200 subscribers. Pick a template, drag in your content, and send. Intuit Assist drafts subject lines and body copy when you are stuck, and scheduling means it goes out Tuesday at 9am whether you remember or not.",
      },
      {
        title: "Recover abandoned carts automatically",
        description:
          "Your online store connects to Mailchimp, and anyone who leaves items in their cart gets a reminder email an hour later, then a discount offer the next day. On Standard, this multi-step flow runs itself.",
      },
      {
        title: "Welcome every new subscriber properly",
        description:
          "A signup form on your website triggers a welcome series: an instant hello, your best content on day three, and an offer on day seven. You build it once and every subscriber gets the same polished introduction.",
      },
      {
        title: "Win back customers who went quiet",
        description:
          "Segment customers who have not bought in six months and send them a targeted win-back campaign with an incentive. Mailchimp's segmentation makes this a ten-minute job.",
      },
      {
        title: "Test what actually gets opened",
        description:
          "A/B test two subject lines on a portion of your list, and Mailchimp automatically sends the winner to everyone else. No guesswork about what your audience responds to.",
      },
    ],
    howItWorks: [
      "Build your audience: import contacts, add signup forms and popups to your website, or connect your store so buyers join automatically.",
      "Design your email: choose a template, drag and drop content blocks, and use Intuit Assist to draft or polish copy and subject lines.",
      "Send or automate: send a campaign now, schedule it for later, or build automation flows (up to 4 steps on Essentials, up to 200 with branching on Standard) that trigger on signup, purchase, or inactivity.",
      "Track and clean: watch opens, clicks, and revenue per campaign, and regularly archive unsubscribed and inactive contacts so you stop paying for them.",
    ],
    pricingExplained: [
      "Four plans, all priced by contact count. Free is $0 for up to 250 contacts and 500 emails a month. Essentials starts at $13 a month for 500 contacts with monthly sends up to 10x your contact count, 3 users, and simple automation up to 4 steps. Standard starts at $20 a month for 500 contacts with sends up to 12x contacts, 5 users, up to 200 automation flows, and Intuit Assist AI. Premium starts at $350 a month for 10,000 contacts with sends up to 15x contacts, unlimited users, and phone support.",
      "Going over your contact or send limit triggers overage fees on paid plans; on the free plan, sending simply pauses until you upgrade or shrink your list. A pay-as-you-go option sells email credits in blocks starting at 5,000 for infrequent senders.",
    ],
    pricingCatches: [
      "Unsubscribed contacts count toward your billing tier. The fix is archiving, not deleting: archiving removes them from the bill while preserving the suppression record so they are never accidentally re-emailed.",
      "Crossing your contact limit by a single person bumps you into the next pricing tier automatically, and the same person in two audiences counts twice.",
      "Transactional emails (order confirmations, password resets) are a separate product from $20 a month per 25,000-email block, and require a paid Mailchimp plan.",
      "Mailchimp raised prices roughly 11 to 13% in April 2026, so older articles will underquote current rates.",
    ],
    whoShouldGet: [
      "Small businesses whose main marketing channel is email newsletters and promotions",
      "Online stores that want abandoned-cart and post-purchase automation without enterprise software",
      "Teams that value having the most integrations available of any email platform",
    ],
    whoShouldSkip: [
      "Anyone with a large, messy list full of unsubscribes (clean it first or pay for ghosts)",
      "Businesses that need transactional email included in one price",
      "Senders who need phone support without paying $350 a month for Premium",
    ],
    comparison: [
      {
        tool: "Mailchimp",
        price: "From $20/mo (Standard)",
        difference: "Best all-rounder for email; strongest automation at this price; billing punishes messy lists",
      },
      {
        tool: "Constant Contact",
        price: "From $12/mo (Lite)",
        difference: "Easier to learn with phone support; weaker automation; no free plan",
      },
      {
        tool: "HubSpot",
        price: "Free / $20/seat/mo (Starter)",
        difference: "Free CRM plus email; better for lead tracking; email automation needs paid tiers",
      },
    ],
    goingDeeper: {
      integrations: [
        "Mailchimp connects natively to 300+ apps, including Shopify, WooCommerce, BigCommerce, Salesforce, QuickBooks, WordPress, Canva, and social ad platforms. If a tool you rely on offers only one email integration, it is usually Mailchimp.",
        "Zapier extends this further, and being owned by Intuit means native ties to QuickBooks for tying email campaigns to actual revenue data.",
      ],
      api: "Mailchimp publishes a Marketing API for managing audiences, campaigns, and automation, plus a separate Transactional API (formerly Mandrill) for order confirmations and other one-to-one emails. The transactional service is billed separately from $20 a month per 25,000-email block and requires a paid Mailchimp plan.",
      privacy: [
        "Your contact lists, campaign data, and analytics live in Mailchimp's systems, and you can export or delete audience data from your account at any time.",
        "Archived contacts keep their suppression history, which protects you from accidentally re-emailing someone who unsubscribed. Deleting wipes that record, so archive instead of delete.",
        "Mailchimp is owned by Intuit and publishes its privacy and security practices on its own trust pages; verify the specifics you need there, especially if you handle regulated data.",
      ],
      advancedWorkflowTitle: "Hands-off ecommerce email engine",
      advancedWorkflow:
        "Connect your Shopify store and build three flows on Standard: an abandoned-cart series (reminder at one hour, incentive at 24 hours), a post-purchase series (thank you, how-to content, review request), and a win-back flow for customers inactive 90 days. Tag buyers by product category so each email recommends relevant products. Once built, the only recurring work is a monthly list-hygiene pass: archive unsubscribes and bounced addresses so your bill tracks your real audience, not your history.",
    },
    faqs: [
      {
        q: "Is Mailchimp still free?",
        a: "Barely. The free plan was cut in January 2026 to 250 contacts and 500 emails a month, with branding, no automation, and support only for the first 30 days. It is fine for testing, but any real list outgrows it in weeks.",
      },
      {
        q: "Why am I paying for contacts I cannot email?",
        a: "Mailchimp counts unsubscribed and non-subscribed contacts toward your billing tier. Archive them (Audience, filter by status, then archive): archiving removes them from your bill while keeping the suppression record so they can never be accidentally re-emailed.",
      },
      {
        q: "What is the difference between Essentials and Standard?",
        a: "Essentials ($13+) is for simple newsletters: basic automation up to 4 steps, 3 users. Standard ($20+) unlocks the real power: up to 200 automation flows with branching, send-time optimization, retargeting ads, and Intuit Assist AI. Most growing businesses land on Standard.",
      },
      {
        q: "Does Mailchimp handle transactional emails?",
        a: "Only as a separate paid product. Mailchimp Transactional (formerly Mandrill) costs from $20 a month per 25,000-email block and requires a paid Mailchimp plan. If transactional email is core to your business, compare dedicated services before committing.",
      },
      {
        q: "How many emails can I send per month?",
        a: "It scales with your plan and list size: Essentials allows up to 10x your contact count, Standard 12x, Premium 15x. A 5,000-contact list on Standard gets 60,000 sends a month.",
      },
      {
        q: "Can I pay only for the months I send?",
        a: "Yes, through pay-as-you-go email credits sold in blocks starting at 5,000. It suits seasonal senders, but regular senders almost always pay less on a monthly plan.",
      },
    ],
  },
  {
    name: "Constant Contact",
    slug: "constant-contact",
    tagline: "The easiest email marketing tool, with real phone support and built-in event tools.",
    category: "ai-marketing",
    pricing: "From $12/mo (Lite); 60-day free trial, no free plan",
    pros: [
      "The easiest email builder in the category: genuinely learnable in under an hour, even for non-technical owners",
      "Phone support on every paid plan, which is rare at this price and a lifeline when something breaks before a big send",
      "A 60-day free trial with no credit card, long enough to actually learn the tool before paying",
      "Built-in event management with ticketing and RSVP, which competitors charge extra for or lack entirely",
      "Nonprofits get up to 30% off with annual prepay, one of the better discounts in the industry",
      "AI content generator and BrandKit help with subject lines and drafts without leaving the editor",
    ],
    cons: [
      "No free plan since June 2025, while Mailchimp and most rivals offer one",
      "Real automation is gated: Lite gets one automation template, and meaningful automation needs Standard or Premium",
      "Send caps (10x, 12x, 24x your contact count) with overage fees, so heavy senders pay more than the sticker price suggests",
      "Prices escalate fast as your list grows: doubling from 500 to 1,000 contacts reportedly jumps Lite from $12 to about $30",
      "More expensive than competitors for the feature set, and automation depth lags behind ActiveCampaign and others at similar prices",
      "Some reviewers report that canceling requires contacting customer service rather than clicking a button",
    ],
    bestFor: "Nonprofits, local businesses, and event organizers who want the simplest possible email tool with human support",
    url: "https://www.constantcontact.com",
    verdict:
      "Constant Contact is the friendliest email tool for non-marketers, and its phone support plus event features are genuinely distinctive. You pay a premium for that friendliness, and power users will outgrow it.",
    verdictBox:
      "Constant Contact is built for the business owner who wants to send a good-looking newsletter without learning marketing software. The editor is the easiest in the category, a human answers the phone when you need help, and event invitations with RSVP tracking are built right in. The tradeoff is price and power: there is no free plan, real automation starts at $35 a month, and the cost climbs steeply as your list grows. For nonprofits, local shops, and event-driven businesses, the simplicity is worth it. For anyone who wants deep automation, competitors give you more for less.",
    quickFacts: {
      price: "Lite $12/mo; Standard $35/mo; Premium $80/mo (all at 500 contacts, scaling up)",
      freeTier: "No free plan; 60-day free trial with no credit card required",
      setup: "Under an hour; live 1:1 onboarding with experts is included on paid plans",
    },
    whatIsIt: [
      "Constant Contact is an email marketing platform aimed at small businesses, nonprofits, and local organizations. You create email campaigns with a drag-and-drop editor, manage your contact lists, and track who opens and clicks.",
      "It stands out in two ways: human support (phone, chat, and email on paid plans) and built-in event marketing, with invitations, registration, ticketing, and RSVP tracking inside the same tool you use for email.",
    ],
    businessScenarios: [
      {
        title: "Promote your fundraiser without hiring a marketer",
        description:
          "Your nonprofit is hosting a gala. Build the invitation email, sell tickets, track RSVPs, and send reminders, all inside Constant Contact, then apply the nonprofit discount to the bill.",
      },
      {
        title: "Send a monthly newsletter in 30 minutes",
        description:
          "You run a local shop. Pick a template, drop in this month's offers and photos, and send to your customer list. The AI content generator drafts the subject line when you are stuck.",
      },
      {
        title: "Welcome new subscribers automatically",
        description:
          "On Standard, a new signup triggers a welcome series and the system resends to people who did not open the first email, so nobody slips through because they missed one message.",
      },
      {
        title: "Fill seats for a workshop",
        description:
          "Create the event, email your list the invitation, track registrations, and send a reminder the day before. No separate event platform, no spreadsheet of RSVPs.",
      },
      {
        title: "Run a flash sale by text",
        description:
          "On Premium, 500 SMS messages a month are included, so your flash-sale announcement reaches phones, not just inboxes, for the customers most likely to act fast.",
      },
    ],
    howItWorks: [
      "Start the 60-day trial with no credit card. Import your contacts or add signup forms to your website to start collecting them.",
      "Pick a template and build your email in the drag-and-drop editor. The AI content generator helps with subject lines and body copy, and BrandKit keeps your logo and colors consistent.",
      "Send now or schedule for later. On Standard and up, set up automation templates (welcome series, resend-to-non-openers) and segment your list so the right people get the right message.",
      "Track results in the reporting dashboard: opens, clicks, and on Premium, revenue reporting that ties campaigns to sales.",
    ],
    pricingExplained: [
      "Three plans, all priced by contact count. Lite is $12 a month for up to 500 contacts: 1 user, monthly sends up to 10x your contact count, basic automation with 1 template, AI content assistance, and social posting. Standard is $35 a month: 3 users, sends up to 12x contacts, 3 automation templates, automatic resend to non-openers, 10 custom segments, and A/B subject-line testing. Premium is $80 a month: unlimited users, sends up to 24x contacts, advanced automation, dynamic content, unlimited segments, and 500 SMS messages a month.",
      "Pay annually to save up to 15%, and nonprofits save up to 30% with 12-month prepay. There is no free plan; the 60-day trial needs no credit card, and a 30-day money-back guarantee backs paid plans.",
    ],
    pricingCatches: [
      "The advertised prices assume a 500-contact list. Costs rise steeply from there: moving from 500 to 1,000 contacts reportedly takes Lite from $12 to about $30 a month.",
      "Above 10,001 contacts you are moved to a higher Email Plus tier automatically, so model that cost before you cross the threshold.",
      "Send limits are real: Lite's 10x cap means 5,000 sends a month on a 500-contact list, and overages run about $0.002 per extra email.",
      "Lite's automation is minimal (one template). If automation is why you are buying, you need Standard at minimum.",
    ],
    whoShouldGet: [
      "Non-technical owners who want the simplest possible path to a professional newsletter",
      "Nonprofits and community organizations (the discount plus event tools are a strong combination)",
      "Businesses that run events and want invitations, ticketing, and email in one place",
    ],
    whoShouldSkip: [
      "Anyone who wants a free plan to start (Mailchimp and others offer one)",
      "Marketers who need deep, custom automation (look at ActiveCampaign or HubSpot instead)",
      "Budget-focused senders with growing lists (the price escalation is the steepest complaint)",
    ],
    comparison: [
      {
        tool: "Constant Contact",
        price: "From $35/mo (Standard)",
        difference: "Easiest to use with phone support and event tools; weaker automation per dollar",
      },
      {
        tool: "Mailchimp",
        price: "From $20/mo (Standard)",
        difference: "Cheaper with stronger automation and a free plan; no phone support without Premium",
      },
      {
        tool: "HubSpot",
        price: "Free / $20/seat/mo (Starter)",
        difference: "Free CRM with email included; steeper learning curve; upgrade cliff later",
      },
    ],
    goingDeeper: {
      integrations: [
        "Constant Contact offers 300+ integrations, including Shopify, Eventbrite, Canva, Salesforce, QuickBooks, WordPress, Facebook, and Zapier for connecting to thousands more apps.",
        "The Eventbrite integration is worth calling out: import event registrants into your lists and email them before and after the event, with confirmed opt-in handling.",
      ],
      api: "Constant Contact publishes a developer API (V3) with documentation and a developer portal for registering applications, so technical teams can build custom integrations with contacts, campaigns, and events.",
      privacy: [
        "Your contacts and campaign data live in Constant Contact's systems, with standard export and list-management controls in your account.",
        "Constant Contact publishes its privacy and security practices on its own pages; verify the specifics you need there, particularly around data residency if that matters to your business.",
      ],
      advancedWorkflowTitle: "Event-to-email fundraising loop",
      advancedWorkflow:
        "For a nonprofit or event-driven business: connect Eventbrite, and after each event, import attendees into a dedicated list, send a thank-you email with photos the next day, then a feedback survey a week later. Segment attendees who opened everything into a VIP list for early-bird invitations to the next event. The whole loop runs from two actions: importing the attendee list and scheduling the sequence, and it turns one-time attendees into repeat supporters without manual follow-up.",
    },
    faqs: [
      {
        q: "Is there a free plan?",
        a: "No. Constant Contact removed its free plan in June 2025. What you get instead is a 60-day free trial with no credit card required, which is longer than most competitors' trials.",
      },
      {
        q: "What is the difference between Lite, Standard, and Premium?",
        a: "Lite ($12) is basic broadcast email for tiny lists. Standard ($35) adds the automation, segmentation, and A/B testing that make email actually work as a channel. Premium ($80) adds advanced automation, dynamic content, unlimited users, and 500 SMS a month. Most growing businesses need Standard at minimum.",
      },
      {
        q: "How many emails can I send?",
        a: "Your monthly allowance is a multiple of your contact count: 10x on Lite, 12x on Standard, 24x on Premium. With 500 contacts on Standard, that is 6,000 emails a month. Automated emails are generally excluded from the cap.",
      },
      {
        q: "Is Constant Contact good for nonprofits?",
        a: "It is one of the best fits: up to 30% off with annual prepay, built-in event management with ticketing, and phone support for teams without a marketing specialist. That combination is hard to match.",
      },
      {
        q: "Can I cancel easily?",
        a: "Some reviewers report that canceling requires contacting customer service rather than a self-serve button. Ask about the cancellation process during your trial so there are no surprises.",
      },
      {
        q: "How does it compare to Mailchimp?",
        a: "Constant Contact is easier to learn and offers phone support on all paid plans, plus event tools Mailchimp lacks. Mailchimp is cheaper, has a free plan, and offers deeper automation. Choose Constant Contact for simplicity and support, Mailchimp for price and power.",
      },
    ],
  },
];
