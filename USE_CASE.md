# RTO Shield — Pre-Dispatch RTO Prevention Voice Agent

> A voice AI agent that calls every COD customer **before dispatch**, confirms intent + address + slot, and lets the brand ship only the orders that will actually get accepted.

**Industry:** Direct-to-Consumer (D2C) E-Commerce · COD-heavy categories
**Built on:** Bolna (voice agent + telephony + webhooks) + custom web app
**One-line pitch:** *Cart abandonment is solved. RTO is not. We solve the second leak.*

---

## 1. TL;DR

Indian D2C brands lose **25–35% of every COD shipment to RTO** (Return-To-Origin). Each RTO costs ₹150–₹300 in reverse logistics + product damage + capital lock — that is roughly ₹3,000+ Cr of annual industry-level bleed.

The current playbook is reactive: ship first, hope for the best, eat the loss. SMS/WhatsApp confirmation has <15% open rates and zero comprehension verification.

**RTO Shield** flips the model. Before any COD order leaves the warehouse, an Indian-language Bolna voice agent calls the customer, confirms 4 things in 45 seconds, and returns a structured outcome to the brand. Ops only ships what is confirmed. Everything else is paused, address-corrected, slot-rescheduled, or cancelled — *before* the courier picks it up.

**Result:** RTO rate moves from ~28% → <15% in 4–6 weeks. Per 1,000 COD orders that is ~₹40,000 saved at zero extra ad spend.

---

## 2. The problem, in numbers

| Metric | Indian D2C reality | Source / signal |
|---|---|---|
| COD share of D2C orders | 55–70% | Shiprocket, Unicommerce reports |
| RTO rate on COD | 25–35% (some categories 40%+) | GoKwik, Shiprocket public benchmarks |
| Cost per RTO | ₹150–₹300 | Reverse logistics + packaging + restocking |
| SMS/WhatsApp confirmation read rate | <15% | Standard CPaaS benchmark |
| Brand response today | Manual call by tele-caller (₹20–₹40/call) for high-AOV orders only | Industry default |

Two structural problems:

1. **Ship-first model is broken.** Once the order is on the line haul, there is no graceful exit — even if the customer never wanted it, the brand pays for the round trip.
2. **Pre-dispatch confirmation does not scale manually.** Tele-callers cost ₹20–₹40/call and are language-limited. Brands can only afford to confirm the top 20% of orders by AOV. The bleed lives in the long tail.

**This is not a "remind people about their cart" problem. This is a "talk to the human and get a yes/no with comprehension" problem.** That is the exact gap voice AI fills, and SMS/WhatsApp/email cannot.

---

## 3. Why this is under-built (the non-obvious part)

Most voice AI startups in this space, including Bolna's existing customer base, have built around the **pre-checkout funnel**: cart abandonment, lead qualification, COD confirmation at order placement.

The **post-order, pre-dispatch window** — typically 4–24 hours after the customer clicked "Place Order" but before the courier picks up — is almost untouched by automation. It is the one window where:

- The customer's intent has cooled (impulse buy regret kicks in)
- Address typos and pin-code errors surface
- The brand still has full control to cancel without cost

Everyone is fighting for the click. Nobody is fighting for the package. That is the wedge.

---

## 4. Why voice (and why not SMS/WhatsApp)

| Channel | Read/answer rate | Comprehension verified? | Address-edit possible? | Reschedule possible? |
|---|---|---|---|---|
| SMS | 8–12% | No | No | No |
| WhatsApp template | 30–40% open, ~5% reply | No | Form-fill only | Limited |
| Email | <2% click | No | No | No |
| Manual tele-call | 60–70% pickup | Yes | Yes | Yes |
| **Voice AI agent** | **55–65% pickup** | **Yes — verified verbally** | **Yes — captured in transcript** | **Yes — slot collected** |

Voice AI is the only channel that hits ~tele-caller comprehension at ~SMS economics.

---

## 5. The solution

### 5.1 Product surface

A simple internal-tool web app for the brand's ops team:

1. **Orders Inbox** — list of COD orders in `ready_to_ship` status synced from Shopify/WooCommerce/manual CSV.
2. **One-click "Verify"** — triggers a Bolna outbound call to the customer in their preferred language.
3. **Outcomes dashboard** — each order auto-tagged after the call:
   - `confirmed` → ship
   - `address_correction` → ops fixes address, re-verifies
   - `reschedule` → hold + new slot
   - `cancel_requested` → cancel before dispatch (saves full RTO cost)
   - `unreachable` → retry per policy
4. **Transcript drawer** — full call transcript + sentiment for compliance and audit.

### 5.2 The 45-second conversation (agent design)

The agent runs a tight, deterministic script with controlled openings for clarification. Four states, in order:

```
Greeting → Intent confirm → Address verify → Slot confirm → Goodbye
```

Sample turn-by-turn (Hinglish):

> **Agent:** "Namaste, main {Brand} se Riya bol rahi hoon. Aapne kal {Product} order kiya tha — kya main 30 second le sakti hoon?"
>
> **Agent (intent):** "Order ki value ₹{X} hai, COD pe. Confirm kar dein, aap order receive karenge?"
>
> **Agent (address):** "Aapka address {short address} hai — sahi hai? Koi landmark add karna hai?"
>
> **Agent (slot):** "Delivery {date} ko {time-window} mein aayegi — ye slot theek hai, ya kal/parso prefer karenge?"
>
> **Agent (close):** "Theek hai, confirm kar diya. Dhanyavaad."

Three guardrails worth calling out:

- **Off-script handling:** if the customer asks about return policy, refund, or product details, the agent answers from a small RAG pack of brand FAQs and *does not* hallucinate beyond it. Anything outside → graceful escalation to a human callback.
- **Language switching:** detect spoken language on first reply, switch agent voice/locale (Bolna native feature).
- **No sales pressure:** if the customer says "cancel", the agent confirms politely and tags the order as `cancel_requested`. No retention loop. This builds trust and protects the brand.

### 5.3 Webhook contract (the spine of the integration)

**Outbound (we → Bolna):** trigger call

```json
POST /v1/agents/{agent_id}/calls
{
  "to_number": "+91XXXXXXXXXX",
  "metadata": {
    "order_id": "ORD-10293",
    "brand_id": "BR-001",
    "customer_name": "Saurav",
    "product_summary": "Cotton kurta, size L",
    "order_value": 1299,
    "address_short": "Indiranagar, Bengaluru 560038",
    "scheduled_slot": "2026-05-07T14:00+05:30"
  }
}
```

**Inbound (Bolna → us):** call outcome webhook

```json
POST /webhooks/bolna/call-completed
{
  "call_id": "CL-...",
  "metadata": { "order_id": "ORD-10293", "brand_id": "BR-001" },
  "outcome": "confirmed | address_correction | reschedule | cancel_requested | unreachable",
  "extracted": {
    "address_correction": null,
    "new_slot": null,
    "cancel_reason": null
  },
  "transcript_url": "...",
  "recording_url": "...",
  "language_detected": "hi-IN",
  "duration_sec": 47,
  "sentiment": "neutral"
}
```

We persist this verbatim, then update the order's status. Idempotent on `call_id`.

---

## 6. Outcome metric (the only number that matters)

**Primary:** RTO rate on verified-COD shipments.
- Baseline (industry): ~28%
- Target after 4 weeks: **<15%**

**Secondary (board-friendly):**
- ₹ saved per 1,000 COD orders
- Verification call success rate (`confirmed` / total)
- Cancel-before-dispatch rate (pure margin saved)
- Average call cost vs. tele-caller cost (target: 80% cheaper)

We instrument every one of these in the dashboard. The pitch line for any D2C founder is: *"Show me your last 30 days of COD RTO. I will cut it in half."*

---

## 7. End-to-end demo flow (assignment Objective 4)

This is the exact 90-second demo we will record:

1. **User (ops persona)** opens the web app, sees the Orders Inbox.
2. Clicks **Verify** on a fresh COD order. Web app POSTs to backend.
3. Backend calls **Bolna API** with order metadata → Bolna places real outbound call to the demo phone.
4. The reviewer answers the phone, has a real 30-second conversation with the agent (in Hinglish or English).
5. Call ends → Bolna fires webhook → backend updates order status.
6. Web app dashboard auto-refreshes — the order now shows `confirmed`, with full transcript visible in the side drawer.
7. **The narrative line:** *"This single call just saved the brand ₹220 if the customer had said no, or earned them a clean ship if yes. Multiply by 10,000 orders/day."*

That is User → Web app → Agent → Backend logic → Output, demonstrated end-to-end on a real call.

---

## 8. What we will build in the 4-hour web app window

In scope:

- One brand, hardcoded auth (single ops user) — no multi-tenant
- Orders inbox: CSV upload + manual single-order add
- Trigger-call button → backend → Bolna
- Webhook receiver → DB update
- Dashboard: orders list with status chip + transcript drawer
- One-screen "metrics" view: RTO-saved counter (mock baseline math is fine for demo)

Explicitly out of scope (and we will say so honestly in the deck):

- Shopify/WooCommerce live sync (CSV is the stand-in)
- Multi-tenant brand onboarding
- Retry policies and call scheduling beyond manual trigger
- Compliance flows (DLT, recording consent UI) — acknowledged, not built

This honesty matters. Reviewers respect a clear "v1 vs. v2" split more than a half-baked "everything".

---

## 9. Tech shape (just enough)

- **Backend:** existing FastAPI skeleton in `backend/` — add a `domains/orders` and `domains/calls` module following the repo's domain-driven structure already documented in `backend/AGENTS.md`.
- **DB:** Postgres (Supabase) — `orders`, `calls`, `call_events` tables. Webhooks idempotent on `call_id`.
- **Frontend:** existing Next.js app in `frontend/` — three screens (Inbox, Order detail with transcript, Metrics).
- **Voice:** Bolna agent template adapted from "COD Confirmation" but rewritten for the *pre-dispatch* mental model (tone is service, not sales).
- **Telephony:** Bolna's bundled provider (Vobiz integration per their Jan 2026 update) so we do not touch raw SIP.

Total wiring: ~5 endpoints, ~3 tables, ~3 screens. Genuinely fits the 4-hour box.

---

## 10. Risks and how we frame them

| Risk | Honest answer |
|---|---|
| Customer does not pick up | Pickup rate ~60%; for misses, fall back to WhatsApp confirm card. Build retry policy in v2. |
| Customer feels spammed | Limit to 1 verification call per order, polite tone, easy cancel path — verified by transcript audit. |
| Wrong language detected | Bolna handles auto-switch; we still log `language_detected` for QA. |
| Brand worried about losing sales to "cancel" path | Counter-argument: a cancel before dispatch is a 100% margin save vs. RTO. Show the math in the deck. |
| Compliance (DLT, consent) | Voice calls in India need consent + DLT registration for the calling number. We acknowledge it as a v2 production-readiness item. |

---

## 11. Why this is the right pitch *for Bolna* specifically

Bolna's largest paying logos today (GoKwik, Hypothesis, Futwork) are concentrated in the e-commerce + payments funnel. Their existing templates dominate the **pre-checkout** moment. Their case studies do not yet show a strong **pre-dispatch** play.

RTO Shield is the natural next product on the same customer's shelf. A reviewer at Bolna reading this should immediately think: *"This is the missing template in our gallery, and it slots cleanly next to Cart Abandonment and COD Confirmation."*

That is the read I want them to have.

---

## 12. What I will deliver in the assignment package

- This document (the thinking)
- A Bolna agent configured and live (the voice)
- Web app deployed (the surface)
- A 90-second demo video showing User → App → Agent → Backend → Output on a real call
- GitHub repo with clean README and run instructions

That is the full chain the brief asks for.

---

*Author: Saurav · For: Bolna Full-Stack Engineer assignment · Version: v1*
