# OpsPilot workflows (n8n exports)

These are the 11 n8n workflows behind OpsPilot, exported as JSON from n8n Cloud. Slack is the interface.

## How a message flows

```
Slack message
  -> opspilot-router      classify intent (gpt-4o-mini), then route
       |- policy    -> policy-brain
       |- hiring    -> hr-hiring
       |- ops       -> ops-coordinator
       |- analytics -> data-analyst
       |- knowledge -> knowledge-bot
       |- support   -> support-agent   (refunds, order status, human approval)
       |- audit     -> audit-replay    ("why was ORD-1004 refunded")
       |- multi     -> orchestrator    (plans up to 3 parts, runs each part through guardrails and the right bot)
       `- other     -> fallback reply
Every bot calls shared-guardrails before acting.
Failures go to self-healing-proposer, which proposes a fix in Slack.
```

| File | What it does | Nodes |
|---|---|---|
| `opspilot-router.json` | Entry point. Classifies the message and routes it to a bot. | 27 |
| `orchestrator.json` | Splits a multi-request message into up to 3 tasks and routes each one. Fails closed. | 20 |
| `shared-guardrails.json` | Rule-based checks and the kill switch, shared by all bots. | 5 |
| `support-agent.json` | Order status and refunds. Auto-approves under the limit, blocks double refunds, asks a human above it. | 20 |
| `policy-brain.json` | Answers from company policy documents. | 9 |
| `hr-hiring.json` | Screens candidates, drafts replies, tracks hiring. | 23 |
| `ops-coordinator.json` | Creates and updates tasks, reports on them. | 23 |
| `data-analyst.json` | Answers sales questions from the sheet. A code check rejects any number the model invents. | 15 |
| `knowledge-bot.json` | Answers from a vector knowledge base (Qdrant). | 12 |
| `audit-replay.json` | Explains past decisions from the Audit Log. | 7 |
| `self-healing-proposer.json` | Error workflow. Proposes a fix when another workflow fails. | 8 |

## Importing

1. In n8n: **Workflows -> Import from file**, one file at a time.
2. Import the sub-workflows first (guardrails, bots, orchestrator), then the router last.
3. Re-link credentials (Slack, Google Sheets/Drive, Gmail, Qdrant, OpenAI). Credentials are not included in the exports.
4. Update the Execute Workflow nodes to point at your imported copies, and set the Google Sheet IDs to your own copy of the data sheet.
5. Publish each sub-workflow, otherwise the router cannot call it.

## Honest limits

- The guardrails are rule-based and can be bypassed.
- The evals are small and written by me.
- LLM classifiers can misroute a message.
- Refunds are simulated; no real money moves.
