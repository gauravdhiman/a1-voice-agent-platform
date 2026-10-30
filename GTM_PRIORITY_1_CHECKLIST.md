# GTM Priority 1 Implementation Checklist

**Target:** Ship before any marketing push  
**Estimated Time:** 4-6 days total  
**Owner:** Next coding agent or development team

---

## Task 1.1: Create Public Pricing Page (2-3 days)

**Goal:** Add `/pricing` route with approved catalog

### Acceptance Criteria
- [ ] Route `/pricing` renders pricing comparison
- [ ] Four plans displayed: Free, Starter ($49), Pro ($149), Scale ($299)
- [ ] Annual pricing toggle shows 2-month discount
- [ ] Credit → minute conversion shown clearly (10 credits = 1 minute)
- [ ] Phone rental costs explained (80 cr/mo for extra US local)
- [ ] Premium tools badge on Scale tier only
- [ ] CTA: "Start Free Trial" → `/auth/signup`
- [ ] Mobile responsive layout
- [ ] Matches brand colors from existing site

### Files to Create/Modify
```
frontend/src/app/pricing/
  ├── page.tsx              (NEW - main pricing page)
  └── pricing-comparison.tsx (NEW - plan comparison component)

frontend/src/components/billing/
  └── plan-card.tsx          (ENHANCE - reuse for pricing page)

frontend/src/components/public-theme/
  └── public-header.tsx      (UPDATE - add "Pricing" nav link)
```

### Implementation Notes
```typescript
// Example pricing page structure
export default function PricingPage() {
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'annual'>('monthly');
  
  const plans = [
    {
      name: 'Free',
      price: 0,
      credits: 100,
      features: ['1 agent', '1 member', '~10 call minutes'],
    },
    {
      name: 'Starter',
      monthlyPrice: 49,
      annualPrice: 490,
      credits: 2500,
      features: ['Unlimited agents', 'Unlimited members', '~250 call minutes', '1 US local number', 'Embed widget'],
    },
    // ... Pro, Scale
  ];
  
  return (
    <div>
      <h1>Simple, Transparent Pricing</h1>
      <BillingToggle value={billingInterval} onChange={setBillingInterval} />
      <PlanGrid plans={plans} billingInterval={billingInterval} />
    </div>
  );
}
```

### Testing
- [ ] `/pricing` loads without errors
- [ ] Annual toggle works correctly
- [ ] All CTAs link to signup
- [ ] Mobile layout looks good (< 768px width)
- [ ] Screenshot for founder approval

---

## Task 1.2: Merge Demo Outcome Flows (1-2 days)

**Goal:** Merge `codex/demo-agents` → `main` to show demo results

### Acceptance Criteria
- [ ] Branch `codex/demo-agents` merged cleanly to `main`
- [ ] No merge conflicts or broken tests
- [ ] Demo pages show outcome cards after call completion:
  - [ ] Lead capture form submission confirmation
  - [ ] Appointment booking receipt with calendar link
  - [ ] Google Sheet row creation success message
- [ ] `/demo/dental-office` works end-to-end
- [ ] `/demo/hvac-dispatch` works end-to-end (if exists)
- [ ] Demo outcome tokens validate correctly
- [ ] Rate limiting still enforced (5 calls/hour)

### Git Steps
```bash
git fetch origin
git checkout main
git pull origin main
git merge origin/codex/demo-agents

# Resolve any conflicts
# Run tests
npm run test              # Frontend
pytest backend/tests/     # Backend
./scripts/run-e2e.sh     # E2E

# If tests pass:
git push origin main
```

### Files Likely Changed
```
backend/src/voice_agents/
  ├── demo_outcome_service.py    (outcome display logic)
  └── demo_public_routes.py      (outcome API endpoints)

frontend/src/app/demo/[slug]/
  ├── page.tsx                   (demo landing + outcome display)
  └── demo-outcome-card.tsx      (outcome result component)

frontend/src/components/demo/
  └── outcome-interest.tsx       (lead capture outcome UI)
```

### Testing
- [ ] Start demo call as visitor
- [ ] Complete appointment booking scenario
- [ ] See "Appointment booked!" outcome card with calendar link
- [ ] Complete lead capture scenario
- [ ] See "We'll contact you soon!" confirmation
- [ ] Verify outcome tokens expire after 24h
- [ ] Check no PII in logs

---

## Task 1.3: Mark Integration Status Clearly (1 day)

**Goal:** Label integrations as "Live" vs "Coming Soon"

### Acceptance Criteria
- [ ] Tool catalog has `display_status` field:
  - `'live'`: Green badge, "Live"
  - `'beta'`: Blue badge, "Beta"
  - `'coming_soon'`: Gray badge, "Coming Soon"
- [ ] UI shows status badges on:
  - [ ] Tool configuration page
  - [ ] Agent tool selection
  - [ ] Homepage integration section (if exists)
- [ ] Backend seeds correct status:
  - Google Calendar, Gmail, Sheets, Resend, HubSpot, Cal.com → `'live'`
  - Outlook, Salesforce → `'coming_soon'` (if mentioned in marketing)
- [ ] "Coming Soon" tools cannot be attached to agents (disabled in UI)

### Database Migration
```sql
-- Add display_status to platform_tools
ALTER TABLE platform_tools 
ADD COLUMN display_status VARCHAR(20) 
DEFAULT 'live' 
CHECK (display_status IN ('live', 'beta', 'coming_soon'));

-- Update existing integrations
UPDATE platform_tools 
SET display_status = 'live'
WHERE name IN (
  'google_calendar', 
  'gmail', 
  'google_sheets', 
  'resend_email', 
  'hubspot_lead_capture', 
  'calcom'
);
```

### Files to Modify
```
backend/alembic/versions/
  └── YYYYMMDD_add_tool_display_status.py  (NEW migration)

shared/voice_agents/
  └── tool_models.py                       (add display_status field)

frontend/src/components/tools/
  ├── tool-card.tsx                        (add status badge)
  └── tool-status-badge.tsx                (NEW component)
```

### Implementation
```typescript
// Tool status badge component
export function ToolStatusBadge({ status }: { status: 'live' | 'beta' | 'coming_soon' }) {
  const config = {
    live: { color: 'green', text: 'Live', icon: CheckCircle },
    beta: { color: 'blue', text: 'Beta', icon: Beaker },
    coming_soon: { color: 'gray', text: 'Coming Soon', icon: Clock },
  }[status];
  
  return (
    <Badge variant={config.color}>
      <config.icon className="w-3 h-3 mr-1" />
      {config.text}
    </Badge>
  );
}
```

### Testing
- [ ] Migration applies cleanly
- [ ] Tool cards show correct badges
- [ ] "Coming Soon" tools cannot be enabled
- [ ] Existing agent tool configurations still work
- [ ] UI looks good in light & dark mode

---

## Pre-Merge Checklist (All Tasks)

### Code Quality
- [ ] All TypeScript/Python lint checks pass
- [ ] No console.log or print() debug statements
- [ ] Error handling for all network calls
- [ ] Loading states for async operations
- [ ] Proper null checks

### Testing
- [ ] Unit tests pass: `npm run test` (frontend)
- [ ] Backend tests pass: `pytest backend/tests/`
- [ ] E2E tests pass: `./scripts/run-e2e.sh`
- [ ] Manual smoke test on local dev stack
- [ ] Test in isolated worktree if possible

### Documentation
- [ ] Update `docs/DATABASE_SCHEMA.md` if schema changed
- [ ] Update `.env.local.example` if new vars added
- [ ] Add comments for non-obvious logic
- [ ] PR description explains changes clearly

### Security
- [ ] No secrets in code or logs
- [ ] User input validated
- [ ] SQL injection protected (use parameterized queries)
- [ ] XSS protected (React escapes by default, but check)
- [ ] CSRF tokens where needed

### Deployment
- [ ] Migration is reversible (has `downgrade()`)
- [ ] No breaking changes to existing APIs
- [ ] Feature flags if risky change
- [ ] Staging deployment plan documented

---

## Rollback Plan

**If Pricing Page Breaks:**
1. Revert PR
2. Check for missing env vars
3. Review Stripe API connection
4. Redeploy previous version

**If Demo Merge Conflicts:**
1. `git merge --abort`
2. Cherry-pick specific outcome commits
3. Test each feature independently
4. Merge incrementally

**If Integration Status Migration Fails:**
1. `alembic downgrade -1`
2. Check for existing tools with null status
3. Fix migration, reapply
4. Verify existing agent configs intact

---

## Success Metrics

**Before Launch:**
- [ ] Pricing page loads in <2s
- [ ] 0 console errors on pricing page
- [ ] Demo completion rate >80% (no errors mid-call)
- [ ] Integration status badges visible to all users
- [ ] No regressions in existing features

**After Launch (Week 1):**
- [ ] 50+ pricing page visits
- [ ] 10+ demo completions with outcome views
- [ ] 0 "where's Outlook?" support tickets
- [ ] <5 min avg time on pricing page (engagement)

---

## Founder Approval Required

**Before Merging:**
- [ ] Pricing page copy reviewed by founder
- [ ] Pricing numbers confirmed ($49/$149/$299)
- [ ] Integration labels approved (Live vs Coming Soon)
- [ ] Demo outcome messaging reviewed

**After Merging (Before Production Deploy):**
- [ ] Full smoke test with founder present
- [ ] Screenshot walkthrough of all 3 changes
- [ ] Confirm no breaking changes to existing customers

---

## Handoff to Next Agent

**When Complete:**
1. Create PR with title: "GTM Priority 1: Pricing Page + Demo Outcomes + Integration Status"
2. Tag: `@founder` for review
3. Link to this checklist in PR description
4. Include screenshots of:
   - Pricing page (desktop & mobile)
   - Demo outcome card after call
   - Tool status badges in UI
5. List any blockers or open questions
6. Suggest Priority 2 next (automated paid activation)

**PR Template:**
```markdown
## Summary
Implements GTM Priority 1 blockers:
1. Public pricing page at `/pricing`
2. Demo outcome flows merged from `codex/demo-agents`
3. Integration status badges (Live vs Coming Soon)

## Testing
- [x] Pricing page loads, toggle works
- [x] Demo dental-office shows appointment outcome
- [x] Tool badges display correctly
- [x] All tests pass (unit, E2E)
- [x] No regressions

## Screenshots
(Attach 3 screenshots here)

## Deployment Notes
- Requires migration: `alembic upgrade head`
- No new env vars needed
- Safe to deploy to production

## Follow-Up
Priority 2 tasks ready to start after this merges.
```

---

**Questions? Check `ENGINEERING_BRIEF_GTM_HVAC.md` for full context.**
