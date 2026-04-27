# CCE In Practice

This page shows exactly what happens when CCE is active. Every example traces a real interaction from query to result, with token counts and the actual output Claude receives.

---

## The Problem It Solves

Every Claude Code session starts cold. Claude has no memory of your project.

The typical workaround is pasting files. But pasting files has a cost:

```
payments.py        →  12,400 tokens
shipping.py        →  8,900 tokens
orders.py          →  11,200 tokens
models.py          →   9,500 tokens
                      ----------
                      42,000 tokens just to set the scene
```

You pay those tokens before Claude has answered a single question. Then you pay them again next session. And the session after that.

CCE replaces this pattern. Instead of pasting files, Claude queries an index and retrieves only the code relevant to the current task.

```
context_search("payment processing")  →  800 tokens
```

That is the entire premise. The rest of this page shows how it works in practice.

---

## Scenario 1: Finding a Function

**The task:** "How does shipping cost get calculated? I need to add a surcharge for oversized items."

### Without CCE

You paste `payments.py` (800 lines, 12,400 tokens) and `shipping.py` (600 lines, 8,900 tokens) so Claude has the right context. Claude reads both files in full. Total cost before the conversation starts: **21,300 tokens.**

### With CCE

Claude runs one search:

```
context_search(query="calculate shipping cost")
```

CCE returns:

```
[payments.py:45] (confidence: 0.94)
def calculate_shipping(order, warehouse, method="standard"):
    """Calculate shipping cost based on order weight, destination,
    and shipping method. Returns cost in USD."""
    total_weight = sum(item.weight * item.quantity for item in order.items)
    zone = _get_shipping_zone(warehouse.location, order.destination)
    base_rate = SHIPPING_RATES[method][zone]
    return round(base_rate * total_weight, 2)

---

[shipping.py:12] (confidence: 0.89)
SHIPPING_RATES = {
    "standard": {"domestic": 0.45, "regional": 0.62, "international": 1.20},
    "express":  {"domestic": 0.85, "regional": 1.10, "international": 2.40},
    "overnight":{"domestic": 1.50, "regional": 2.00, "international": 4.50},
}

---

[shipping.py:88] (confidence: 0.81)
def _get_shipping_zone(origin, destination):
    """Determine shipping zone (domestic/regional/international)
    based on origin and destination country codes."""
    if origin.country == destination.country:
        return "domestic"
    if origin.continent == destination.continent:
        return "regional"
    return "international"
```

**Total: 680 tokens.** Claude has the function it needs to modify, the rate table it needs to update, and the zone logic it needs to understand. Nothing else.

---

## Scenario 2: Debugging an Error

**The task:** "I'm getting a KeyError on `SHIPPING_RATES[method]` when method is 'same_day'. Where should I add it?"

### Without CCE

Same problem: you need to show Claude the rate tables, the constants file, and probably the enum or validation layer. Multiple files, thousands of tokens.

### With CCE

Claude searches for the error location:

```
context_search(query="SHIPPING_RATES method KeyError same_day")
```

And gets back the rate table plus the graph expansion adds the validation layer automatically:

```
[shipping.py:12] (confidence: 0.97)
SHIPPING_RATES = {
    "standard": {"domestic": 0.45, ...},
    "express":  {"domestic": 0.85, ...},
    "overnight":{"domestic": 1.50, ...},
}

---

[shipping.py:145] (confidence: 0.88)
VALID_METHODS = {"standard", "express", "overnight"}

def validate_shipping_method(method: str) -> None:
    if method not in VALID_METHODS:
        raise ValueError(f"Unknown method: {method!r}")

---

[orders.py:78] (confidence: 0.74)  ← graph expansion: shipping.py CALLS orders.py
def create_order(items, method="standard", ...):
    validate_shipping_method(method)
    ...
```

The graph expansion found `orders.py` automatically because `shipping.py` calls into it. Claude now knows the full picture: the missing key, the validation set that guards it, and where new methods need to be registered. **Total: 890 tokens.**

---

## Scenario 3: Cross-Session Memory

**Session 1 (Monday).** You are adding Stripe integration. At the end of the session, Claude records:

```
record_decision(
    title="Stripe over Braintree",
    context="Evaluated both for the payment gateway. Chose Stripe because the team
             already has Stripe accounts and the Python SDK is better maintained.
             Braintree requires a separate merchant account setup.",
    files_affected=["payments/gateway.py", "payments/webhooks.py"]
)
```

**Session 2 (Thursday).** New session, fresh context. You ask: "Can we switch to PayPal for international orders?"

Claude calls `session_recall` at session start and gets:

```
[Decision recorded 2026-04-14]
Title: Stripe over Braintree
Context: Evaluated both for the payment gateway. Chose Stripe because the team
         already has Stripe accounts and the Python SDK is better maintained.
         Braintree requires a separate merchant account setup.
Files: payments/gateway.py, payments/webhooks.py
```

Claude now knows the history before you type a word. It can give an informed answer about adding PayPal alongside Stripe rather than asking you to re-explain why you chose Stripe in the first place.

**Without CCE:** you paste a summary of the Monday session or re-explain the decision from scratch. With CCE: 0 extra tokens, the context is already there.

---

## Scenario 4: Exploring an Unfamiliar Area

**The task:** "I've never touched the auth system. How does token validation work end to end?"

This is the worst case for context: you don't know which files are involved, so you cannot paste the right ones. You might guess `auth.py` but miss the JWT utilities, the DB lookup, and the middleware that wraps everything.

### Without CCE

You guess. Paste `auth.py`. Claude tells you it needs to see `utils/jwt.py` too. You paste that. Then it asks for `middleware/auth_middleware.py`. Each round trip costs tokens and time.

### With CCE

Claude runs one search:

```
context_search(query="token validation authentication end to end")
```

Primary results return `auth.py:validate_token`. Graph expansion then walks CALLS edges automatically:

```
[auth.py:34] (confidence: 0.93)
def validate_token(token: str) -> User | None:
    """Validate a JWT and return the associated user, or None if invalid."""
    payload = decode_jwt(token)          # → utils/jwt.py
    if payload is None:
        return None
    return fetch_user_by_id(payload["sub"])  # → db/users.py

---

Graph expansion (auth.py CALLS utils/jwt.py):
[utils/jwt.py:12] (confidence: 0.79)
def decode_jwt(token: str) -> dict | None:
    """Decode and verify a JWT. Returns payload dict or None on failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        log.info("Token expired")
        return None
    except jwt.InvalidTokenError as exc:
        log.warning("Invalid token: %s", exc)
        return None

---

Graph expansion (auth.py CALLS db/users.py):
[db/users.py:88] (confidence: 0.76)
def fetch_user_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)

---

[middleware/auth_middleware.py:22] (confidence: 0.71)
class AuthMiddleware:
    """Extracts Bearer token from Authorization header and calls validate_token."""
    def __call__(self, request):
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            request.user = validate_token(header[7:])
        return self.app(request)
```

One query. Full end-to-end picture. Claude understands the call chain without you doing any archaeology. **Total: 1,100 tokens.** Manual approach to reach the same coverage: at minimum 4 files, roughly 18,000 tokens.

---

## Scenario 5: Working at Token Budget Limits

**The task:** "Show me everything related to order fulfilment."

This is a broad query. Suppose CCE finds 12 matching chunks but the token budget (`max_tokens`, default 8,000) is only enough for 8 of them.

Without overflow references, the last 4 results would be silently dropped. You would not know they exist.

With CCE, the response ends with:

```
---
4 more result(s) available (not shown to save tokens):
  expand_chunk(chunk_id="a1b2c3")  → fulfillment/picker.py:45    (confidence: 0.81)
  expand_chunk(chunk_id="d4e5f6")  → fulfillment/packer.py:12    (confidence: 0.78)
  expand_chunk(chunk_id="g7h8i9")  → fulfillment/shipper.py:88   (confidence: 0.74)
  expand_chunk(chunk_id="j0k1l2")  → fulfillment/tracker.py:201  (confidence: 0.71)
```

Claude sees that these files exist and can call `expand_chunk` on exactly the one it needs, paying only for that chunk. Nothing is lost, nothing is wasted.

---

## Token Comparison: A Realistic Session

A typical CCE-assisted session on a mid-size project:

```
Action                                      Tokens
────────────────────────────────────────────────────
Session start (overview + past decisions)    10,200
context_search("payment processing")           800
graph expansion (utils + db bonus chunks)      400
expand_chunk (one overflow item requested)     320
context_search("order fulfilment status")      750
────────────────────────────────────────────────────
Total                                        12,470
```

The same work without CCE:

```
Action                                      Tokens
────────────────────────────────────────────────────
Paste payments.py                           12,400
Paste shipping.py                            8,900
Paste orders.py                             11,200
Paste fulfillment/                          14,600
Paste utils/jwt.py (found mid-session)       2,100
────────────────────────────────────────────────────
Total                                       49,200
```

**CCE used 25% of the tokens for the same session.** The difference is not "compression" — it is precision. Claude only saw the code that was relevant to each specific question.

---

## What Claude Actually Has Available

Once CCE is connected, Claude can call these tools at any point without any setup from you:

| Tool | When Claude uses it | Token cost |
|------|--------------------|-----------:|
| `context_search` | Any question about code | 400–1,200 |
| `expand_chunk` | Needs full body of an overflow result | 200–600 |
| `session_recall` | Start of session, or "what did we decide about X" | 100–400 |
| `record_decision` | After any architectural choice | 0 (write-only) |
| `record_code_area` | After editing a file | 0 (write-only) |
| `index_status` | Checking index health | ~50 |
| `reindex` | After large uncommitted changes | ~50 |
| `set_output_compression` | When you ask for shorter responses | ~50 |

The read tools (`context_search`, `expand_chunk`, `session_recall`) are where token cost lives. The write tools (`record_decision`, `record_code_area`) are near-zero cost because they only confirm success.

---

## Why Precision Beats Compression

Other approaches to reducing token cost focus on compressing what gets sent. CCE focuses on not sending what is not needed.

Compression shrinks a 12,400-token file to maybe 8,000 tokens. You still loaded the whole file. You are still paying for every function Claude did not need.

Precision means Claude receives 600 tokens for `calculate_shipping` because that is the only function relevant to the question. The other 11,800 tokens in `payments.py` are never loaded at all.

This is why the savings are multiplicative, not additive. Each search is a targeted retrieval, not a compressed bulk load.

---

## See Also

- [How It Works](How-It-Works.md) — the full technical pipeline with all 9 stages
- [Configuration](Configuration.md) — tuning `top_k`, `confidence_threshold`, and compression level
- [CLI Reference](CLI-Reference.md) — all commands with examples
