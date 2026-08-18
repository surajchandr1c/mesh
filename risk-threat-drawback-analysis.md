# Risk, Threat & Drawback Analysis — Distributed AI Inference Mesh
**Purpose:** honest catalogue of every serious concern, loophole, and structural weakness in this system, as currently designed. This is not a "these are all solved" doc — most of these are open questions your team needs to explicitly decide on (fix, accept, or defer), not code bugs to patch quietly.

---

## 1. Trust & Integrity Risks

### 1.1 Volunteer tampers with or fakes model output
Nothing in the current design cryptographically verifies that a worker actually ran the claimed model on the claimed prompt. A worker could return altered, biased, hardcoded, or fabricated text and the orchestrator would stream it to the user as if it were legitimate.
- **Consequence:** users receive misinformation, manipulated answers, or propaganda with no way to know it happened.
- **Mitigation options (undecided):** redundant spot-check dispatch (send ~1% of tasks to 2 nodes, compare), reputation scoring per node, user "report this response" flagging.

### 1.2 Malicious or compromised worker client
The worker software (`track1_worker_node`) is something contributors download and run on their own machine. Nothing stops someone from running a modified version that:
- Mines cryptocurrency in the background, unrelated to any real task, while still appearing "online" and occasionally completing real work to stay trusted.
- Logs and exfiltrates every prompt it processes (a serious privacy leak if users submit sensitive info).
- Deliberately returns slow/garbage results to sabotage the network.
- **Consequence:** this is a supply-chain trust problem, not a per-request problem — no amount of prompt filtering fixes it, because it doesn't depend on what the user asked.
- **Open question:** is worker client code closed and signed/verified before nodes are allowed to join, or is it open-source and self-hosted (meaning verification is much harder)?

### 1.3 Malicious node impersonation
Current auth (`verify_node_key`) only proves "this is *a* registered node." It doesn't prove ongoing honest behavior. A registered-but-turned-malicious node looks identical to a healthy one to the rest of the system.

### 1.4 Prompt/response data exposure in transit or at rest
User prompts (potentially containing sensitive personal, business, or proprietary information) get sent to an untrusted third party's home computer for processing. Even without malicious intent from the volunteer, this is a fundamentally different privacy model than a centralized API — there's no way to guarantee a volunteer isn't logging, screen-recording, or otherwise capturing what runs through their machine.
- **Open question:** should there be a "no sensitive data" disclaimer/ToS for users? Is end-to-end encryption of prompt content even meaningful here, given the volunteer's machine *must* decrypt it to run inference?

---

## 2. Harm & Abuse via User-Submitted Prompts

### 2.1 Volunteer's machine used to generate harmful/illegal content
A user could submit prompts designed to generate harmful, illegal, or disturbing output, which then executes using a volunteer's electricity, hardware, and (potentially) with content briefly present on their disk — without the volunteer's knowledge or consent, despite them only signing up to donate spare compute for a "good deed."
- **Consequence:** real reputational, ethical, and potentially legal exposure for volunteers who had zero visibility into what was asked.
- **This is the single most urgent item to resolve before onboarding real volunteers** — see Section 5.

### 2.2 Using the mesh to bypass rate limits/bans on centralized AI services
Because output comes from many independent machines, a bad actor could use the mesh as a way to generate large volumes of harmful content (spam, disinformation, harassment material) that would otherwise be caught by a single provider's rate limiting or moderation.

### 2.3 Resource-exhaustion / DoS via oversized prompts
Nothing in the current design caps prompt size or token count before dispatch. An oversized prompt could freeze or crash a volunteer's machine, especially lower-spec contributor hardware.

---

## 3. Availability & Reliability Drawbacks (Structural, not just bugs)

### 3.1 No guaranteed response time
Unlike a centralized data center, volunteer availability is inherently unpredictable — nodes go offline mid-task (laptop closed, wifi drops, contributor just stops the app). The failover system (Section on `REASSIGNED`) handles this gracefully *up to 2 retries*, but there's a real ceiling: if all available nodes are unstable at once, users get a hard failure with no fallback.

### 3.2 Inconsistent output quality across nodes
Different volunteers may run different hardware, different quantization levels, or even (per 1.2) different model versions. The same prompt could produce meaningfully different quality answers depending on which random node picks it up — an inherent inconsistency a centralized service doesn't have.

### 3.3 Clean-restart-on-failover wastes generation time and compute
The team correctly chose "restart from scratch" over KV-cache migration for reliability — but this means a user near the end of a long generation, if their assigned node drops, loses all progress and starts over. For long responses this could mean a materially worse experience under network instability, and it also means the *first* volunteer's wasted compute is pure loss (no partial credit, no partial value returned).

### 3.4 No SLA-style accountability
There's no contributor commitment or accountability mechanism — a volunteer can vanish mid-task with zero consequence, which is fine ethically (they're volunteering) but means the system's reliability ceiling is capped by "how many strangers happen to be online right now," not by anything you control.

---

## 4. Security Loopholes in the Current Technical Design

### 4.1 No content moderation layer anywhere in the pipeline
As designed, `task_router.py` validates *shape* (is this valid JSON matching `TaskRequest`) but nothing validates *content*. This is a real gap, not a future nice-to-have.

### 4.2 Sandboxing strength is an assumption, not a guarantee
Track 1's job description says "Docker/containers to ensure contributor machines cannot be compromised" — but Docker alone is not a hard security boundary against a sufficiently motivated attacker (container escapes exist). If this system ever handles genuinely adversarial input at scale, standard Docker may not be enough — stronger isolation (gVisor, Firecracker microVMs) is worth a real evaluation, not an assumption.

### 4.3 Redis is a single shared nervous system with no defense-in-depth mentioned
Every track reads/writes the same Redis instance. If Redis itself is compromised or misconfigured (e.g. exposed without auth), an attacker could inject fake tasks, fake node heartbeats, or fake control frames (including fake `COMPLETED`/`ABORT` frames) — effectively controlling the whole mesh's behavior from one entry point. No mention anywhere yet of Redis AUTH, network isolation, or TLS between services.

### 4.4 API key model for worker nodes is static, not rotated
A static API key per node (mentioned in the auth design) that's leaked or stolen doesn't expire or rotate — a persistent point of compromise once exposed.

### 4.5 No rate limiting decided yet, only planned
Rate limiting is listed in Phase 5 of the build plan, meaning it's genuinely absent until then — anyone testing against the live system before that phase is unprotected against basic abuse/flooding.

---

## 5. The Two Most Urgent Open Questions (Answer Before Real Volunteers Join)

1. **Is there any content moderation on user prompts before they're dispatched to a volunteer's machine?** Without this, you're asking real people to unknowingly process potentially harmful requests on their own hardware — this is an ethical obligation to your volunteers, not just a technical nice-to-have.
2. **Is the worker client trusted software you control (signed, verified, closed-source), or can anyone run their own modified version?** This single decision determines whether Sections 1.1–1.3 (tampering, mining, impersonation) are "hard to fully prevent" or "basically unfixable" — it's an architectural choice, not a patch you add later.

---

## 6. Lower-Priority but Real Long-Term Concerns

- **Legal liability distribution** — if a volunteer's machine is ever implicated in generating illegal content, who's responsible: the platform, the user who prompted it, or the volunteer? No policy currently addresses this.
- **No incentive/reward system (by design, v1)** — this is fine for a small trusted pilot but doesn't scale to attracting large numbers of genuine volunteers long-term; worth knowing this is a deliberate v1 limitation, not an oversight.
- **Model provenance** — nothing verifies which actual model file a worker is running matches what's advertised to users (ties to 1.1/1.2).
- **No mentioned incident response process** — if a harmful output or a compromised node is discovered, there's currently no documented process for revoking that node's access quickly.

---

## How to Use This Doc

This isn't a checklist to silently fix in your own code — most of these decisions (moderation policy, worker trust model, legal ToS, redundancy tradeoffs) need your **whole team and possibly legal/policy input**, not just Teammate 2. Treat Section 5 as the two items to raise explicitly before this goes anywhere near real volunteers or real users, even in a small pilot.
