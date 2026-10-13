# LEGAL REVIEW REQUIRED BEFORE PUBLICATION.
# This file contains the v1 legal documents for 24x7 AI as plain data. Every bracketed
# placeholder (e.g. [LEGAL ENTITY NAME], [REGISTERED ADDRESS], [GOVERNING LAW ...],
# [ARBITRATION VENUE/COURT], [SUBPROCESSOR LIST PUBLISHED AT ...], [DPO CONTACT],
# [DATE OF PUBLICATION]) marks a legal fact that is unknown to engineering and MUST be
# filled in and approved by qualified legal counsel before these documents are published.
"""Pure-data legal document content for 24x7 AI (v1).

Standard library only. No backend imports. Defines exactly four public constants:

- ``TERMS_V1_MARKDOWN``   -- Terms & Conditions, markdown, rendered with
  react-markdown + remark-gfm (GitHub-flavored markdown).
- ``PRIVACY_V1_MARKDOWN`` -- Privacy Policy, markdown, same renderer.
- ``TERMS_V1_SUMMARY``    -- one-line ``summary_of_changes`` for the v1 row.
- ``PRIVACY_V1_SUMMARY``  -- one-line ``summary_of_changes`` for the v1 row.

Product naming in user-facing text: "24x7 AI" (website: https://247ai.live).
"""

# ---------------------------------------------------------------------------
# Terms & Conditions
# ---------------------------------------------------------------------------
TERMS_V1_MARKDOWN = """# Terms & Conditions — 24x7 AI

**Effective date:** [DATE OF PUBLICATION]
**Version:** 1.0
**Provider:** [LEGAL ENTITY NAME], with registered address at [REGISTERED ADDRESS] ("**24x7 AI**", "**we**", "**us**", or "**our**")
**Website:** https://247ai.live

These Terms & Conditions (these "**Terms**") govern your access to and use of the 24x7 AI
platform, websites, software, and related services (collectively, the "**Service**"). By
creating an account, signing in through an OAuth provider, or otherwise accessing or using
the Service, you agree to be bound by these Terms. If you are using the Service on behalf of
an organization, you represent that you have authority to bind that organization, and
"**you**" and "**Customer**" refer to that organization.

Please read these Terms carefully. They contain important limitations of liability,
disclaimers of warranties, and a dispute resolution provision. If you do not agree to these
Terms, do not use the Service.

---

## 1. Agreement to These Terms

**1.1 Acceptance.** You accept these Terms by (a) clicking "I agree" or a similar acceptance
control at signup, (b) completing registration or authentication through a supported OAuth
provider (for example Google or GitHub single sign-on), or (c) accessing or using the Service
after receiving notice of these Terms. Acceptance is recorded against the version of these
Terms in effect at the time of acceptance, together with the date, source (signup, OAuth, or
re-acceptance), user agent, and IP address where available.

**1.2 Version and effective date.** This is version 1.0 of these Terms.
**Effective date: [DATE OF PUBLICATION].** Each published version of these Terms is stored
and identified by its version number and effective date. The version presented to you at
acceptance, and the version currently published on the Service, are the controlling versions.

**1.3 Authority.** If you accept these Terms on behalf of a company, partnership, or other
entity, you represent and warrant that you are authorized to bind that entity and that the
entity agrees to be bound by these Terms. If you do not have that authority, or if you do not
agree to these Terms, you must not accept them or use the Service.

**1.4 Related documents.** Our Privacy Policy, located at https://247ai.live/privacy, is
incorporated into these Terms by reference and applies to the processing of personal data in
connection with the Service. Additional terms may apply to specific features or to
third-party services you choose to connect; where those additional terms conflict with these
Terms, the more specific terms control for that feature or service.

---

## 2. Eligibility & Accounts

**2.1 Age requirement.** You must be at least 18 years old, and the age of legal majority in
your jurisdiction, to create an account or use the Service. The Service is not directed to
children, and we do not knowingly permit registration by anyone under 18.

**2.2 Account registration.** You agree to provide accurate, current, and complete
registration information and to keep it up to date. You may not register an account using
false pretenses or impersonate any other person or entity.

**2.3 Account security.** You are responsible for safeguarding your credentials, OAuth
tokens, API keys, and any device used to access the Service. You must notify us promptly at
**legal@247ai.live** of any suspected unauthorized access to or use of your account. We are
not liable for losses arising from unauthorized access that results from your failure to
safeguard credentials, except to the extent caused by our breach of these Terms or our
failure to implement reasonable security measures.

**2.4 Organization administrators.** If you use the Service as part of an organization, the
organization's administrators are responsible for (a) managing seats and user access,
(b) configuring agents, workflows, tools, and integrations for their users, (c) ensuring that
all users under the organization's account comply with these Terms, and (d) reviewing and
validating any AI output before it is relied upon or acted upon. The organization is
responsible for the acts and omissions of its users.

**2.5 One account per user.** You may not share a single login among multiple individuals
except through features expressly designed for shared access, and you may not create accounts
by automated means or circumvent any access controls we apply.

---

## 3. Description of the Service

**3.1 Overview.** 24x7 AI is an AI voice-agent platform that enables businesses to configure,
deploy, and operate artificial-intelligence voice agents that handle telephone calls and
browser-based calls. The Service is provided as a self-service software platform.

**3.2 Capabilities.** Depending on your configuration and plan, the Service may include:

| Capability | Description |
| --- | --- |
| AI voice agents | Configurable conversational agents (prompts, voices, behavior, escalation rules) that conduct real-time spoken conversations. |
| Inbound calls | Agents that answer calls routed to phone numbers you provision or connect through the Service. |
| Outbound calls | Agents that place calls to phone numbers you supply, subject to the Acceptable Use Policy and applicable telemarketing law. |
| Browser calls | Voice sessions started from a web interface, without a traditional phone number. |
| Telephony | Call transport and phone numbers provided through third-party telephony providers, including Twilio, and other carriers or communications platforms we may use. |
| Call artifacts | Call recordings, transcripts, call summaries, and related metadata generated in connection with calls. |
| Agent configuration | Workspaces, agent definitions, prompts, tools, knowledge sources, and testing/simulation features. |
| Tools & integrations | Connections to third-party systems you configure, including Google Calendar via the Model Context Protocol (MCP), webhooks, HTTP tools, and customer-managed credentials. |
| Credits-based usage | Metered consumption of calling and AI resources through prepaid or subscription credits. |

**3.3 Changes to the Service.** We may modify, add, or remove features from time to time.
We will use reasonable efforts to avoid materially degrading core functionality during a
paid subscription period. We do not guarantee that any particular feature, integration,
model provider, or telephony route will remain available.

**3.4 Beta features.** Features labeled alpha, beta, preview, or similar are provided for
evaluation, may be changed or discontinued at any time, and are provided without warranties
of any kind to the maximum extent permitted by law.

**3.5 No emergency services.** The Service is not a replacement for traditional telephone
service and does not support emergency calling (for example, 911 or 112) in any jurisdiction.
You must make alternative arrangements for emergency communications.

---

## 4. Your Account Registration & Organization

**4.1 Workspaces and organizations.** The Service organizes usage into workspaces or
organizations. When an organization is provisioned, the provisioning user becomes an
administrator unless otherwise designated. Administrators may invite users, assign seats,
and delegate administrative permissions.

**4.2 Seats.** Access is granted per named user (a "seat") unless we agree otherwise in
writing. You are responsible for all activity under seats assigned to your organization.

**4.3 Administrator duties.** Organization administrators must (a) maintain accurate user
lists and promptly remove users who should no longer have access, (b) configure call
handling and integrations in accordance with applicable law, including obtaining any
required call-recording notices and consents, and (c) ensure that agents and prompts used by
their organization comply with these Terms.

**4.4 Customer configuration.** You control the configuration of your agents, the phone
numbers you use, the recipients of outbound calls, the tools you connect, and the credentials
you supply. We are not responsible for consequences arising from your configuration choices,
including the content of calls your agents conduct.

---

## 5. Acceptable Use Policy

**5.1 Lawful use.** You must use the Service only for lawful purposes and in accordance with
these Terms and all applicable laws and regulations, including telemarketing, consumer
protection, privacy, wiretapping, and recording laws.

**5.2 Telemarketing and robocall compliance.** You are solely responsible for compliance with
all laws governing outbound calling and automated messaging, including, where applicable, the
U.S. Telephone Consumer Protection Act (TCPA), the Telemarketing Sales Rule (TSR), the CAN-SPAM
Act's related calling provisions, and analogous state and international laws. This includes
maintaining and honoring do-not-call lists, obtaining prior express written consent where
required, providing required caller identification, honoring opt-out requests, and observing
time-of-day calling restrictions. 24x7 AI does not obtain consents on your behalf and does not
manage your do-not-call obligations.

**5.3 Call-recording consent.** Recording calls, capturing voice, or transcribing
conversations may require the consent of one or all parties to the call depending on the
jurisdiction. You are responsible for determining which consent rules apply (including
one-party versus all-party consent regimes), providing any required notices or audio
announcements, and disabling recording where consent cannot lawfully be obtained.

**5.4 Prohibited conduct.** You must not, and must not permit others to:

- send spam, unlawful robocalls, or unsolicited bulk communications;
- harass, threaten, stalk, defame, or abuse any person through the Service;
- commit or facilitate fraud, phishing, impersonation, or social engineering, including
  impersonating any person, company, or government entity without authorization;
- transmit unlawful, infringing, obscene, or harmful content, or content that violates the
  rights of others;
- use the Service to make calls to emergency numbers, or to numbers you are not permitted to
  contact;
- probe, scan, or test the vulnerability of the Service or any system or network, bypass or
  breach security or authentication measures, or attempt to gain unauthorized access;
- interfere with or disrupt the Service, including by overloading, flooding, or introducing
  malicious code;
- reverse engineer, decompile, or attempt to extract source code or models from the Service
  except to the extent this restriction is prohibited by applicable law;
- resell, sublicense, or provide the Service to third parties except as expressly permitted;
- use the Service to develop a competing product by systematically extracting output,
  prompts, or configurations from the Service.

**5.5 Monitoring and enforcement.** We may investigate violations of this Acceptable Use
Policy and may suspend or terminate access where we reasonably believe a violation has
occurred. We may remove or disable content or configurations that we reasonably believe are
unlawful or harmful.

---

## 6. Health & Payment Data Restrictions

**6.1 No protected health information (PHI).** You must not submit, transmit, or otherwise
make protected health information (as defined by the U.S. Health Insurance Portability and
Accountability Act (HIPAA) or similar laws), or other regulated health data, available to the
Service — including through agent prompts, call audio, recordings, transcripts, summaries,
tool payloads, or knowledge sources — unless we have entered into a signed Business Associate
Agreement (BAA) with you. Absent a signed BAA, the Service is not designed or approved for
PHI, and you must not use it for PHI.

**6.2 No cardholder data.** You must not collect, transmit, or store payment card numbers or
other cardholder data (as defined by the PCI Data Security Standard) through voice agents,
call recordings, transcripts, tool integrations, or any other part of the Service. The Service
is not a PCI-compliant payment capture channel. Payment processing for your subscription is
handled by our third-party payment processor, not by the voice agents.

**6.3 Other regulated data.** You are responsible for determining whether your intended use
involves other categories of sensitive or regulated data (for example, government identifiers
or biometric identifiers) and for not submitting such data unless the Service expressly
supports that use and we have agreed to it in writing.

---

## 7. Customer Content, Recordings & AI Output

**7.1 Customer Content.** "**Customer Content**" means the data and content you or your users
submit to or generate through the Service, including agent configurations, prompts, knowledge
sources, phone numbers, contact lists, call audio, call recordings, transcripts, summaries,
tool inputs and outputs, and feedback you provide about your use of the Service.

**7.2 Ownership.** As between you and 24x7 AI, you retain all right, title, and interest in
and to Customer Content, including your call recordings and transcripts. These Terms do not
transfer ownership of Customer Content to us.

**7.3 License to 24x7 AI.** You grant 24x7 AI a worldwide, non-exclusive, royalty-free license
to host, store, reproduce, process, transmit, display, and otherwise use Customer Content
solely as necessary to provide, maintain, secure, support, and improve the Service, to comply
with law, and as otherwise described in our Privacy Policy. We do not use Customer Content to
train generalized AI or machine-learning models (see the Privacy Policy for details).

**7.4 Recordings and transcripts.** The Service can record calls and generate transcripts and
summaries. Recording behavior is controlled by your configuration. You are responsible for
enabling or disabling recording, for providing required notices, and for retaining or
deleting recordings in accordance with your own policies and legal obligations.

**7.5 AI output.** Output generated by AI voice agents — including spoken responses,
transcripts, summaries, classifications, and any decisions or actions taken by tools — is
machine-generated and probabilistic. **AI output may be inaccurate, incomplete, out of date,
or inappropriate, and it may not reflect real events or the true intent of any caller.**

**7.6 Review and validation.** You must review and independently validate AI output before
relying on it, before communicating it to third parties as fact, and before taking or
automating any action based on it. You remain responsible for all decisions, communications,
and actions taken through or informed by the Service and your agents.

**7.7 No professional advice.** AI output is not professional advice of any kind — including
legal, medical, financial, tax, insurance, or emergency advice. You must not represent AI
output as professional advice, and you must not use the Service as a substitute for
qualified professional judgment.

**7.8 Human oversight.** Where your agents operate autonomously — including outbound calling,
scheduling, or tool execution — you must implement appropriate human oversight, escalation,
and review procedures for your use case.

---

## 8. Third-Party Services & Model Providers

**8.1 Third-party components.** The Service depends on third-party services, including
telephony carriers and communications providers (such as Twilio), cloud hosting providers,
large-language-model (LLM) providers, speech-to-text and text-to-speech providers, payment
processors, and integrations you connect (such as Google Calendar through MCP).

**8.2 Their terms apply.** Your use of third-party services may be subject to those
providers' terms, policies, and privacy notices. You are responsible for reviewing and
complying with them. 24x7 AI is not responsible for third-party services and does not control
their availability, accuracy, or practices.

**8.3 Customer-managed credentials.** Where you connect third-party systems using your own
credentials, tokens, or API keys, you are responsible for those credentials and for the
permissions you grant. We store such credentials encrypted, but we are not responsible for
actions taken through credentials you provide.

**8.4 Model changes.** We may change the model, speech, or telephony providers used to
deliver the Service from time to time. Such changes may alter the behavior, latency, voice
characteristics, or output of your agents.

**8.5 Subprocessors.** We engage subprocessors to process personal data on our behalf. Our
current list of subprocessors is [SUBPROCESSOR LIST PUBLISHED AT …]. We will provide notice of
material changes to our subprocessor list as described in the Privacy Policy.

---

## 9. Fees, Credits & Billing

**9.1 Paid plans.** Access to paid features of the Service is provided through subscription
plans and/or prepaid or recurring credits as described on the pricing page or in an order form.
Fees are quoted in the currency stated at purchase and are exclusive of taxes unless stated
otherwise.

**9.2 Credit model.** Usage of metered resources — including outbound and inbound call
minutes, AI/voice processing, telephony, and certain tool invocations — consumes credits.
Credit consumption rates may vary by resource and may be updated prospectively with notice.

| Item | Basis | Notes |
| --- | --- | --- |
| Subscription fee | Monthly or annual | Grants a plan allowance and/or credits. |
| Credit consumption | Per unit of metered usage | Rates published in the Service. |
| Overage | Beyond plan allowance | Charged at then-current overage rates or deducted from additional credits. |
| Third-party pass-through | Where offered | Carrier or partner charges may be passed through at cost plus any disclosed margin. |

**9.3 Payment.** You authorize us (or our payment processor) to charge your selected payment
method for subscription fees, credit purchases, and overages as they become due. Subscription
fees are charged in advance; usage-based charges may be charged in arrears.

**9.4 Taxes.** You are responsible for all applicable taxes, duties, and governmental charges
arising from your purchases, except for taxes based on our net income. If we are required to
collect taxes, they will be added to your invoice unless you provide valid exemption evidence.

**9.5 No refunds.** Except where required by law or expressly stated in writing by 24x7 AI,
all fees, credit purchases, and charges are non-refundable, including for unused credits,
partial billing periods, and termination for your convenience.

**9.6 Price changes.** We may change prices and credit rates prospectively. For recurring
subscriptions, we will provide reasonable advance notice (email to the account owner is
sufficient). Continued use after the effective date of a price change constitutes acceptance.

**9.7 Suspension for non-payment.** If any amount is overdue, we may suspend access to the
Service after providing notice and a reasonable opportunity to pay. Suspension does not
relieve you of payment obligations, and we may charge reasonable collection costs and interest
at the lower of 1.5% per month or the maximum rate permitted by law.

---

## 10. Intellectual Property

**10.1 24x7 AI ownership.** 24x7 AI and its licensors own all right, title, and interest in
and to the Service, including the platform, software, models we develop, user interfaces,
designs, documentation, trademarks, and all improvements or derivative works. Except for the
limited rights expressly granted in these Terms, no rights are granted to you by implication
or otherwise.

**10.2 Limited license to you.** Subject to your compliance with these Terms and payment of
applicable fees, we grant you a limited, non-exclusive, non-transferable, revocable license to
access and use the Service for your internal business purposes during your subscription term.

**10.3 Feedback.** If you provide feedback, suggestions, or ideas about the Service, you grant
us a perpetual, irrevocable, worldwide, royalty-free license to use, reproduce, modify, and
exploit that feedback for any purpose without obligation or compensation to you.

**10.4 Usage data.** We may collect and use data about access to and use of the Service in
aggregate or de-identified form to operate, secure, and improve the Service, consistent with
the Privacy Policy.

---

## 11. Confidentiality

**11.1 Confidential information.** Each party may receive non-public information from the
other that is identified as confidential or that reasonably should be understood to be
confidential ("**Confidential Information**"). Customer Content and the non-public features,
performance, and security of the Service are Confidential Information of the respective
disclosing party.

**11.2 Obligations.** The receiving party will use Confidential Information only to perform
under these Terms, will protect it with at least reasonable care, and will disclose it only to
personnel and contractors who need to know it and who are bound by confidentiality
obligations at least as protective as these.

**11.3 Carve-outs.** Confidential Information does not include information that (a) is or
becomes public through no fault of the receiving party, (b) was rightfully known to the
receiving party without confidentiality obligation before disclosure, (c) is rightfully
received from a third party without breach of any confidentiality obligation, or (d) is
independently developed without use of the disclosing party's Confidential Information.

**11.4 Compelled disclosure.** A party may disclose Confidential Information to the extent
required by law, provided it gives reasonable prior notice (where legally permitted) and
cooperates with efforts to obtain confidential treatment.

**11.5 Duration.** These confidentiality obligations continue for three (3) years after the
end of these Terms, except that trade secrets remain protected for as long as they remain
trade secrets, and Customer Content remains protected as described in the Privacy Policy.

---

## 12. Privacy

**12.1 Privacy Policy.** Our Privacy Policy, available at https://247ai.live/privacy,
explains how we collect, use, disclose, and protect personal data in connection with the
Service. By using the Service, you acknowledge the Privacy Policy.

**12.2 Roles.** For account, website, and billing data, 24x7 AI acts as a data controller (or
business under U.S. state privacy laws). For Platform Data that our customers process through
the Service — including call audio, recordings, transcripts, and caller information — 24x7 AI
acts as a processor or service provider on the customer's behalf.

**12.3 Versioning.** The Privacy Policy is versioned in the same way as these Terms. Where a
material change to the Privacy Policy affects your rights, we will provide notice as described
in Section 14 (Changes to these Terms) and in the Privacy Policy.

---

## 13. Suspension & Termination

**13.1 Termination for convenience.** You may stop using the Service and close your account at
any time through the account settings or by contacting us. We may discontinue the Service or
terminate your access for convenience upon at least thirty (30) days' prior written notice,
with a pro-rata refund of prepaid, unused subscription fees for the terminated portion of the
then-current term where required by law or good faith.

**13.2 Termination for cause.** Either party may terminate these Terms immediately upon notice
if the other party materially breaches these Terms and fails to cure the breach within fifteen
(15) days after receiving written notice describing it, or immediately if the breach is not
curable (including any serious violation of the Acceptable Use Policy or the data restrictions
in Section 6). We may suspend or terminate immediately where necessary to prevent harm, comply
with law, or address non-payment after notice.

**13.3 Effect of termination.** Upon termination, your right to access the Service ceases.
Termination does not relieve you of payment obligations incurred before termination.

**13.4 Data export window.** After termination or closure of your account, we will make
Customer Content available for export for a period of thirty (30) days (the "**export
window**") upon request made during that period. After the export window, we may delete
Customer Content in accordance with our retention practices and the Privacy Policy, except
where retention is required by law or needed to establish, exercise, or defend legal claims.

**13.5 Survival.** The following sections survive termination: Section 6 (Health & Payment
Data Restrictions, as to obligations accrued), Section 7 (Customer Content, Recordings & AI
Output, as to accrued obligations), Section 9 (Fees, Credits & Billing, as to unpaid amounts),
Section 10 (Intellectual Property), Section 11 (Confidentiality), Section 12 (Privacy), Section
15 (Disclaimer of Warranties), Section 16 (Limitation of Liability), Section 17
(Indemnification), Section 18 (Governing Law & Disputes), Section 19 (Export & Sanctions
Compliance), and Section 20 (General).

---

## 14. Changes to these Terms

**14.1 Versioned documents.** These Terms are maintained as a versioned document. Each
published version records its version number, effective date, and a summary of changes.

**14.2 Notice of material changes.** For material changes, we will send email notice to the
account owner at least thirty (30) days before the changes take effect. Non-material changes
may take effect when published.

**14.3 Continued use.** After the effective date of changes, your continued use of the Service
constitutes acceptance of the changed Terms. The changed Terms do not retroactively alter
rights accrued for prior versions.

**14.4 Objection.** If you do not agree to a material change, you must stop using the Service
and close your account before the effective date of the change. Closing your account does not
relieve you of payment obligations accrued before closure, and we will handle any Customer
Content in accordance with Section 13.4.

---

## 15. Disclaimer of Warranties

**15.1 AS IS.** TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE SERVICE IS PROVIDED "AS IS" AND
"AS AVAILABLE", WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, STATUTORY, OR
OTHERWISE, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE,
NON-INFRINGEMENT, AND ANY WARRANTIES ARISING FROM COURSE OF DEALING OR USAGE OF TRADE.

**15.2 No guarantees.** We do not warrant that the Service will be uninterrupted, secure, or
error-free; that AI output will be accurate, reliable, or suitable for any purpose; that calls
will be completed or delivered; or that any particular integration or third-party service will
be available.

**15.3 No uptime SLA in v1.** This version of the Service is provided without any service
level agreement, uptime commitment, or support response-time guarantee. Any service levels
must be agreed in a separate written agreement signed by 24x7 AI.

**15.4 AI-specific disclaimer.** You acknowledge that AI voice agents can misunderstand
speech, produce incorrect statements, or behave unexpectedly, and that you are responsible for
reviewing output and implementing safeguards appropriate to your use case.

---

## 16. Limitation of Liability

**16.1 Exclusion of indirect damages.** TO THE MAXIMUM EXTENT PERMITTED BY LAW, NEITHER PARTY
WILL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE
DAMAGES, OR FOR LOST PROFITS, LOST REVENUE, LOSS OF GOODWILL, LOSS OF DATA, OR BUSINESS
INTERRUPTION, ARISING OUT OF OR RELATED TO THESE TERMS OR THE SERVICE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGES.

**16.2 Aggregate cap.** TO THE MAXIMUM EXTENT PERMITTED BY LAW, EACH PARTY'S TOTAL AGGREGATE
LIABILITY ARISING OUT OF OR RELATED TO THESE TERMS OR THE SERVICE WILL NOT EXCEED THE GREATER
OF (A) ONE HUNDRED U.S. DOLLARS (US$100) OR (B) THE TOTAL FEES PAID OR PAYABLE BY YOU TO 24x7
AI IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO THE CLAIM.

**16.3 Carve-outs.** The limitations in Sections 16.1 and 16.2 do not apply to: (a) a party's
breach of Section 11 (Confidentiality); (b) indemnification obligations under Section 17;
(c) your misuse of the Service or infringement of 24x7 AI's intellectual property; (d) your
payment obligations; or (e) liability that cannot be limited or excluded under applicable law.

**16.4 Basis of the bargain.** The parties agree that these limitations reflect a reasonable
allocation of risk and are a fundamental basis of the bargain.

---

## 17. Indemnification

**17.1 Customer indemnity.** You will defend, indemnify, and hold harmless 24x7 AI and its
affiliates, officers, directors, employees, and agents from and against any third-party claims,
damages, losses, and expenses (including reasonable attorneys' fees) arising out of or related
to: (a) Customer Content, including your calls, recordings, transcripts, and agent
configurations; (b) your use of the Service in violation of these Terms or the Acceptable Use
Policy; (c) your violation of applicable law, including telemarketing, TCPA, do-not-call, and
call-recording consent laws; (d) your disputes with callers, contacts, or end users; and (e)
your configuration of tools, integrations, and credentials.

**17.2 24x7 AI indemnity.** We will defend, indemnify, and hold harmless you from and against
any third-party claim that the Service, as provided by us and used in accordance with these
Terms, infringes a third party's intellectual property right, and we will pay damages and
costs finally awarded (or agreed in settlement we approve).

**17.3 IP indemnity exclusions.** Our indemnity in Section 17.2 does not apply to claims
arising from: (a) modification of the Service by anyone other than us; (b) combination of the
Service with items not provided by us where the claim would not arise but for the combination;
(c) Customer Content or your configurations; or (d) use of the Service after we notify you to
stop due to an infringement claim.

**17.4 Procedure.** The indemnified party must give prompt written notice of the claim,
reasonable cooperation at the indemnifying party's expense, and sole control of the defense
and settlement (provided no settlement imposes obligation or admission on the indemnified
party without its consent).

---

## 18. Governing Law & Disputes

**18.1 Governing law.** These Terms and any dispute arising out of or relating to them or the
Service are governed by the laws of **[GOVERNING LAW — e.g. State of Delaware, USA]**, without
regard to conflict-of-law principles, and without regard to the United Nations Convention on
Contracts for the International Sale of Goods.

**18.2 Venue / arbitration — REQUIRES LEGAL REVIEW.** Any dispute that is not resolved
informally will be resolved in **[ARBITRATION VENUE/COURT]**. *(Placeholder: whether disputes
are resolved by binding arbitration or in courts, and the seat/venue and rules of any
arbitration, must be decided by legal counsel before publication.)*

**18.3 Informal resolution.** Before filing a claim, the parties agree to attempt to resolve
the dispute informally by contacting the other party at **legal@247ai.live** and attempting to
reach a resolution for at least thirty (30) days.

**18.4 Jury trial waiver.** TO THE MAXIMUM EXTENT PERMITTED BY LAW, EACH PARTY IRREVOCABLY
WAIVES ANY RIGHT TO A TRIAL BY JURY IN ANY ACTION OR PROCEEDING ARISING OUT OF OR RELATING TO
THESE TERMS OR THE SERVICE.

**18.5 Injunctive relief.** Nothing in these Terms prevents a party from seeking injunctive or
other equitable relief to prevent unauthorized use or disclosure of Confidential Information or
infringement of intellectual property rights.

---

## 19. Export & Sanctions Compliance

**19.1 Export laws.** You must comply with all applicable export control and sanctions laws,
including the U.S. Export Administration Regulations, U.S. sanctions administered by the
Office of Foreign Assets Control (OFAC), and equivalent laws of other jurisdictions.

**19.2 Restrictions.** You may not access or use the Service in, or export or re-export the
Service to, any country or person subject to comprehensive sanctions, or by any person on any
sanctions or restricted-party list. You represent that you are not located in such a country
and are not such a person.

**19.3 Legal process.** We may suspend access where we reasonably believe it is necessary to
comply with applicable export, sanctions, or other legal requirements.

---

## 20. General

**20.1 Force majeure.** Neither party is liable for failure or delay in performance (except
payment obligations) caused by events beyond its reasonable control, including natural
disasters, war, terrorism, labor disputes, governmental action, epidemics, failures of the
internet or third-party telecommunications, or failures of third-party service providers.

**20.2 Assignment.** You may not assign these Terms without our prior written consent, except
to an affiliate or in connection with a merger, acquisition, or sale of substantially all
assets, provided the assignee agrees to be bound by these Terms. We may assign these Terms
freely. Any prohibited assignment is void.

**20.3 Severability.** If any provision of these Terms is held unenforceable, it will be
modified to the minimum extent necessary to make it enforceable, and the remaining provisions
will remain in full force.

**20.4 Entire agreement.** These Terms, together with the Privacy Policy and any order form or
written agreement signed by 24x7 AI, are the entire agreement between the parties regarding the
Service and supersede all prior or contemporaneous agreements on the subject matter.

**20.5 Waiver.** Failure to enforce any provision is not a waiver of the right to do so later.

**20.6 Relationship.** The parties are independent contractors. These Terms do not create a
partnership, joint venture, agency, or employment relationship.

**20.7 Notices.** We may give notice by email to the account owner, by in-product
notification, or by posting on the Service. You must give notice to us in writing by email to
**legal@247ai.live** or by mail to **[REGISTERED ADDRESS]**, attention Legal. Notices are
effective on receipt.

**20.8 No third-party beneficiaries.** These Terms do not confer rights on any third party
except as expressly stated.

**20.9 Interpretation.** Headings are for convenience only. "Including" means "including
without limitation."

---

## 21. Contact

If you have questions about these Terms, contact us:

- **Legal:** legal@247ai.live
- **Entity:** [LEGAL ENTITY NAME]
- **Registered address:** [REGISTERED ADDRESS]
- **Website:** https://247ai.live

*(Placeholder notice: the entity name, registered address, governing law, arbitration
venue/court, and contact details above are placeholders and must be confirmed by legal counsel
before publication.)*
"""

# ---------------------------------------------------------------------------
# Privacy Policy
# ---------------------------------------------------------------------------
PRIVACY_V1_MARKDOWN = """# Privacy Policy — 24x7 AI

**Effective date:** [DATE OF PUBLICATION]
**Version:** 1.0
**Controller / Provider:** [LEGAL ENTITY NAME], [REGISTERED ADDRESS]
**Website:** https://247ai.live

This Privacy Policy explains how **24x7 AI** ("**we**", "**us**", "**our**") collects, uses,
discloses, and protects personal data in connection with the 24x7 AI platform, websites, and
related services (the "**Service**"). It also explains your privacy rights and how to exercise
them. If you do not agree with this Policy, please do not use the Service.

This Policy is versioned alongside our Terms & Conditions. Version 1.0.
**Effective date: [DATE OF PUBLICATION].**

---

## 1. Who We Are & Scope

**1.1 Who we are.** 24x7 AI is an AI voice-agent platform that enables businesses to operate
AI voice agents handling inbound and outbound phone calls and browser-based calls. The data
controller for account, website, and billing data is **[LEGAL ENTITY NAME]**, **[REGISTERED
ADDRESS]**.

**1.2 Roles — controller vs. processor.** Depending on the data, we act in different roles:

| Data category | Our role | Your role |
| --- | --- | --- |
| Account, contact, website, billing, support, and marketing data | Controller / business | Data subject |
| "Platform Data" — call audio, recordings, transcripts, summaries, caller phone numbers, agent configurations, tool data processed on your instruction | Processor / service provider | Controller / business |

**1.3 Platform Data.** "**Platform Data**" means personal data that our customers (our
"**Customers**") and their end users process through the Service — including the content of
phone calls, call parties' phone numbers, recordings, transcripts, and summaries. For Platform
Data, the Customer determines the purposes and means of processing; 24x7 AI processes that data
only to provide the Service on the Customer's documented instructions (including as set out in
the Terms & Conditions and the Customer's configuration) and as required by law. If you are a
caller or an end user of one of our Customers' voice agents and wish to exercise rights over
your data, please contact that Customer directly; we will assist the Customer as described in
Section 12.

**1.4 Scope.** This Policy applies to the Service, our websites, and our related
communications. It does not apply to third-party services that our Customers connect to the
Service (for example, their own CRM, telephony accounts, or Google Workspace tenancies), which
are governed by those third parties' privacy policies and our Customers' own practices.

---

## 2. Information We Collect

**2.1 Account and contact data.** When you register or manage an account, we collect your
name, work email address, organization name, job title, password (stored hashed), OAuth
identifiers (for example, Google or GitHub account identifiers when you sign in with SSO),
locale, and account preferences.

**2.2 Billing data.** For paid plans, we collect billing contact details, company tax or VAT
details where applicable, subscription and credit purchase history, and payment method
metadata. Full payment card details are collected and processed by our payment processor; we
receive only limited metadata (such as card brand, last digits, and expiry) and transaction
status.

**2.3 Platform Data (processed for our Customers).** In the course of providing the Service to
our Customers, we process Platform Data, which may include:

- **Call parties and phone numbers:** caller and callee phone numbers, caller display names
  where available, call direction, timestamps, call duration, and disposition metadata;
- **Call audio and recordings:** audio of calls where recording is enabled in the Customer's
  configuration;
- **Transcripts:** machine-generated text of conversations;
- **Summaries:** AI-generated summaries, classifications, extracted fields, and notes;
- **Agent configurations:** agent names, prompts, voices, behavior rules, escalation
  settings, knowledge sources, and test conversations;
- **Tool data:** inputs and outputs of tools and integrations the Customer configures
  (including Google Calendar events accessed via the Google Calendar MCP integration);
- **Credentials:** API keys, OAuth tokens, and other credentials the Customer connects to
  third-party systems — stored **encrypted**;
- **Call logs:** technical logs of calls (SIP/WebRTC metadata, error codes, latency and
  quality indicators) used for delivery, debugging, and abuse prevention.

**2.4 Usage, device, and cookie data.** We collect information about how you access and use
the Service: IP address, browser type and version, device and operating system, referring URLs,
pages viewed, feature usage, timestamps, and diagnostic events. We and our analytics providers
use cookies and similar technologies as described in Section 5.

**2.5 Support and communications.** When you contact us (for example at
**privacy@247ai.live** or **legal@247ai.live**), participate in surveys, or interact with our
support, we collect the content of your messages, contact details, and any diagnostic data you
share.

**2.6 Data provided about others.** If you provide personal data about other people (for
example, contact lists for outbound calling), you represent that you have authority to do so
and to instruct us to process that data as described in this Policy.

---

## 3. How We Use Information

**3.1 To operate the Service.** We use account, contact, usage, and Platform Data to provide,
maintain, and deliver the Service — including placing and receiving calls, generating
recordings, transcripts, and summaries, executing tools and integrations you configure, and
managing credits and billing.

**3.2 To improve and debug.** We analyze usage data, error logs, and aggregated or
de-identified information to understand how the Service is used, diagnose problems, improve
reliability, and develop features. **We do not train generalized AI or machine-learning models
on Customer Platform Data or on Google Workspace API data.** Limited, human-reviewed quality
improvement may use data only as described in this Section 3.2 and Section 7, and never to
build generalized models from your call content.

**3.3 Analytics.** We use analytics tools to measure feature adoption, performance, and
trends. Where required by law, we do so on the basis of consent (see Section 5).

**3.4 Security and abuse prevention.** We use data to detect, prevent, and respond to fraud,
abuse, spam, security incidents, and violations of our Terms & Conditions (including the
Acceptable Use Policy), and to verify accounts.

**3.5 Support and communication.** We use your contact details to respond to requests, provide
transactional notices (such as billing receipts, service notices, and acceptance records), and
send service-related and, where permitted, marketing communications (which you can opt out of).

**3.6 Legal compliance.** We use and retain data as necessary to comply with law, respond to
lawful requests and legal process, enforce our agreements, and establish, exercise, or defend
legal claims.

---

## 4. Legal Bases

Where the EU/UK General Data Protection Regulation (GDPR) or similar laws apply, we rely on
the following legal bases:

- **Performance of a contract:** to provide the Service you or your organization have signed
  up for, including call delivery, recordings, transcripts, and billing;
- **Legitimate interests:** to secure and protect the Service, prevent abuse, debug and
  improve the Service, and manage our business — balanced against your rights;
- **Consent:** where required — for example, for non-essential cookies, certain marketing
  communications, and processing where you or the Customer must obtain consent (notably
  call-recording consent, which is the Customer's responsibility);
- **Legal obligation:** to comply with applicable laws, tax requirements, and lawful requests.

For Platform Data, we process on the documented instructions of the relevant Customer, who is
responsible for establishing the applicable legal basis for its processing.

---

## 5. Cookies & Similar Technologies

**5.1 Essential.** We use strictly necessary cookies and similar technologies to operate the
Service — for example, to keep you signed in, remember preferences, protect against
cross-site request forgery, and ensure security. These cannot be disabled through our cookie
controls because the Service does not function without them.

**5.2 Analytics.** With your consent where required, we use analytics cookies to understand
how the Service is used and to improve it (for example, page views, feature usage, and
performance metrics).

**5.3 Your choices.** You can control cookies through our cookie banner (where presented),
your browser settings, and, where offered, device-level settings. Blocking some cookies may
degrade Service functionality. We do not currently respond to "Do Not Track" browser signals;
however, where legally required, we honor recognized opt-out preference signals (such as
Global Privacy Control) for the sale/sharing of personal data — and we do not sell or share
personal data for cross-context behavioral advertising (see Section 6).

---

## 6. Sharing & Subprocessors

**6.1 How we share.** We disclose personal data only as follows:

| Recipient | Purpose | Categories |
| --- | --- | --- |
| Cloud hosting & infrastructure | To run and store the Service | Account data, Platform Data, logs |
| Telephony carriers & communications providers (including Twilio) | To route and connect calls | Call audio, phone numbers, call metadata |
| LLM / STT / TTS model providers | To power real-time agent conversations | Audio and text content of calls, agent prompts, as needed to generate responses |
| Payment processor | To process subscriptions and credit purchases | Billing contact and payment metadata |
| Integration providers you connect (e.g. Google Calendar via MCP) | To perform actions you request | Data required for the specific action |
| Professional advisors | Legal, accounting, insurance, audit | As needed for advice and compliance |
| Authorities & legal process | To comply with law, respond to lawful requests, protect rights | As required |
| Business transfers | Merger, acquisition, financing, or sale of assets | Subject to confidentiality and this Policy |

**6.2 No sale; no cross-context behavioral advertising.** We do not sell personal data for
money. We do not share personal data for cross-context behavioral advertising as those terms
are defined under the California Consumer Privacy Act as amended by the CPRA or similar laws.

**6.3 Subprocessors.** We engage subprocessors to process personal data on our behalf under
written agreements that impose confidentiality and data-protection obligations. Our current
subprocessor list is **[SUBPROCESSOR LIST PUBLISHED AT …]**. Where required, we will give
advance notice of material changes to our subprocessor list (by email to the account owner or
by updating the published list) and provide an opportunity to object on reasonable
data-protection grounds.

---

## 7. Google Workspace API Data Disclosure

**7.1 What we access.** If you connect Google Calendar through our Google Calendar MCP
integration, we access limited Google Workspace API data — typically calendar identifiers,
event titles, times, attendees, and free/busy availability — solely to provide the calendar
functionality you requested (for example, booking or rescheduling calls and appointments).

**7.2 Restricted use.** We use Google Workspace API data only to provide the requested calendar
functionality and related features you enable. **We do not use Google Workspace API data to
train generalized AI or machine-learning models.**

**7.3 No advertising use.** We do not use Google Workspace API data for advertising, and we do
not transfer it to third parties except (a) as necessary to provide the requested functionality
(for example, to our infrastructure subprocessors under appropriate protections) or (b) as
required by law.

**7.4 Revocation.** You can revoke our access to Google Workspace data at any time through
your Google account permissions (https://myaccount.google.com/permissions) or by disconnecting
the integration in the Service.

---

## 8. International Transfers

**8.1 Global infrastructure.** We and our subprocessors may process personal data in countries
other than the country where it was collected, including the United States and the European
Economic Area. Data-protection laws in those countries may differ from those of your country.

**8.2 Safeguards.** Where we transfer personal data from the EEA, UK, or Switzerland to a
country not recognized as providing an adequate level of protection, we implement appropriate
safeguards — typically the European Commission's Standard Contractual Clauses (and UK
equivalents) together with supplementary measures where needed — or rely on another lawful
transfer mechanism. **[DPO CONTACT]** can provide more information about our transfer
safeguards upon request.

---

## 9. Retention

**9.1 Account and billing data.** We retain account and billing data for as long as your
account is active and for a reasonable period afterward as needed to comply with law, resolve
disputes, enforce agreements, and maintain financial records.

**9.2 Platform Data.** For our Customers, we retain call recordings, transcripts, summaries,
and call logs in accordance with the Customer's configuration and as needed to provide the
Service. Customers control retention and deletion settings for recordings and transcripts, and
must ensure their retention practices comply with the laws that apply to them (including
call-recording and data-minimization requirements).

**9.3 Deletion on request.** Where required by law, we delete or anonymize personal data upon
a valid request (see Section 12), subject to legal retention requirements and to data needed
to establish, exercise, or defend legal claims. For Platform Data, deletion requests from
individuals are directed to the relevant Customer.

**9.4 Backups.** Residual copies in encrypted backups are purged on a rolling schedule and
are not used for any purpose other than disaster recovery.

---

## 10. Security

**10.1 Measures.** We implement administrative, technical, and organizational measures
appropriate to the risk, including: encryption of personal data in transit (TLS) and at rest;
**encryption of stored tool credentials and API keys**; access controls and least-privilege
principles for our personnel; authentication controls for the Service; logging and monitoring
for security events; and procedures for handling security incidents.

**10.2 No overclaiming.** No method of transmission or storage is completely secure. We do not
claim any specific certification (such as SOC 2 or ISO 27001) unless and until we expressly
state it in a current, published statement. If you have questions about our security measures,
contact **[DPO CONTACT]** or **privacy@247ai.live**.

**10.3 Incident response.** Where required by law, we will notify affected Customers and
authorities of a personal-data breach without undue delay and provide information reasonably
needed for their own notification obligations.

---

## 11. Customer Responsibility for Call Content

**11.1 Recording notices and consent.** Recording calls, capturing voice, or transcribing
conversations may require notice to — and consent from — one or all parties to a call,
depending on the jurisdiction. Our Customers are solely responsible for providing required
notices and audio announcements and for obtaining consents (whether one-party or all-party)
before enabling recording or transcription.

**11.2 Telemarketing compliance.** Our Customers are solely responsible for compliance with
telemarketing and robocalling laws applicable to their outbound campaigns, including the U.S.
Telephone Consumer Protection Act (TCPA), the Telemarketing Sales Rule, do-not-call list
requirements, time-of-day restrictions, and prior-express-consent rules.

**11.3 What we provide.** We provide configuration controls (for example, the ability to
disable recording or to configure announcements), but we do not obtain consents on Customers'
behalf and we do not provide legal advice. If you are an individual whose call was recorded or
handled by one of our Customers' AI voice agents and you have a question or complaint about
that call, please contact that Customer directly. We will assist our Customers in responding to
verified requests as required by law.

---

## 12. Your Rights

**12.1 Rights available to you.** Subject to applicable law (including the GDPR and the
California Consumer Privacy Act as amended by the CPRA), you may have the right to:

- **access** the personal data we hold about you and obtain a copy;
- **correct** inaccurate or incomplete personal data;
- **delete** personal data, subject to legal exceptions;
- **portability** — receive your data in a structured, commonly used, machine-readable format;
- **object to or restrict** certain processing, including processing based on legitimate
  interests;
- **withdraw consent** where processing is based on consent, without affecting prior
  processing;
- **opt out of "sale"/"sharing"** of personal data — note that we do not sell or share
  personal data for cross-context behavioral advertising (Section 6.2);
- **non-discrimination** for exercising your privacy rights.

**12.2 How to exercise.** Submit requests to **privacy@247ai.live** with the subject line
"Privacy Request", or by mail to **[REGISTERED ADDRESS]**, attention Privacy. We may need to
verify your identity before acting on a request, and we will respond within the time required
by applicable law.

**12.3 Platform Data requests.** If your request relates to Platform Data processed for a
Customer (for example, a call handled by one of our Customers' voice agents), please contact
that Customer directly. We will support our Customers in responding to verified requests as
required by law and as agreed with the Customer.

**12.4 Authorized agents.** You may use an authorized agent to submit a request where
permitted by law. We will require proof of the agent's authority and may need to verify your
identity directly with you.

**12.5 Appeals.** If we decline your request, you may appeal by replying to our decision
email with "Appeal" in the subject line, or by writing to **privacy@247ai.live**. If you remain
unsatisfied, you have the right to complain to your local data-protection authority (for EU/UK
data subjects) or to your state attorney general (for California residents).

**12.6 California notice.** For California residents: in the preceding twelve months we have
collected the categories described in Section 2 (identifiers, commercial information, internet
activity, geolocation at city level where inferred from IP, audio/electronic content, and
professional information) and disclosed them to the recipients in Section 6 for business
purposes. We have not sold personal data or shared it for cross-context behavioral advertising.

---

## 13. Children

The Service is not directed to children under 18. We do not knowingly collect personal data
from anyone under 18. If you believe a child has provided us with personal data, contact
**privacy@247ai.live** and we will take appropriate steps to delete it.

---

## 14. Changes to this Policy

**14.1 Versioned.** This Policy is versioned. Each published version records its version number
and effective date, and material changes are accompanied by a summary of changes.

**14.2 Notice of material changes.** For material changes, we will provide email notice to the
account owner at least thirty (30) days before the changes take effect (in line with the
notice provision in our Terms & Conditions). Non-material changes take effect when the updated
Policy is published.

**14.3 Current version.** The current version of this Policy is always published at
https://247ai.live/privacy. Your continued use of the Service after the effective date of
changes constitutes acceptance of the updated Policy. If you do not agree, please stop using
the Service and close your account.

---

## 15. Contact

For privacy questions, requests, or complaints:

- **Privacy:** privacy@247ai.live
- **Legal:** legal@247ai.live
- **Data protection officer / representative:** [DPO CONTACT]
- **Controller / Provider:** [LEGAL ENTITY NAME]
- **Registered address:** [REGISTERED ADDRESS]
- **Website:** https://247ai.live

*(Placeholder notice: the entity name, registered address, DPO contact, and subprocessor list
location above are placeholders and must be confirmed by legal counsel before publication.)*
"""

# One-line summaries stored in `summary_of_changes` for the seeded v1 rows.
TERMS_V1_SUMMARY = "Initial published version."
PRIVACY_V1_SUMMARY = "Initial published version."
