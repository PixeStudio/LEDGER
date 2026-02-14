# Ledger – Professional Money Handling with Integer Cents

## Why integer cents?
In professional financial systems, **money is never stored as float**.
Instead, values are stored as **integers representing the smallest unit** (cents / grosze).

Example:
- 19,20 € → `1920`
- -26,00 € → `-2600`

This guarantees:
- ✅ No floating-point errors
- ✅ Deterministic balancing
- ✅ Simple validation (`sum == 0`)
- ✅ Easy JSON / DB storage

This is the industry standard used by banks, payment providers, and ERP systems.

---

## Core principle

> **All calculations use `int` (cents).  
> `Decimal` is used only at input/output boundaries.**

---

## Data model (example)

```python
postings = [
    {"account": "135", "amount": -2600},
    {"account": "401", "amount": 1920},
    {"account": "401", "amount": 230},
    {"account": "401", "amount": 450},
]

assert sum(p["amount"] for p in postings) == 0
```

---

## Parsing user input (Decimal → int cents)

```python
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def parse_amount_to_cents(raw: str) -> int:
    """
    Accepts: 19.20, 19,20, -10, -10.00
    Returns: integer cents (e.g. 1920, -1000)
    """
    s = raw.strip().replace(" ", "").replace(",", ".")

    if not s:
        raise ValueError("Empty amount")

    try:
        dec = Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError("Invalid amount format")

    return int(dec * 100)
```

---

## Using it in ADD DOCUMENT

```python
raw_amount = input("Amount (+ DR / - CR): ")

try:
    amount = parse_amount_to_cents(raw_amount)
except ValueError as e:
    print(e)
    continue

postings.append({
    "account": account_code,
    "amount": amount,
})
```

---

## Balance validation (no EPS needed)

```python
def is_balanced(postings):
    return sum(p["amount"] for p in postings) == 0
```

This check is **always correct**.

---

## Displaying amounts (int cents → formatted string)

```python
from decimal import Decimal

def format_cents(amount: int) -> str:
    dec = Decimal(amount) / Decimal(100)
    return f"{dec:.2f}"
```

Example:
```python
format_cents(1920)   # "19.20"
format_cents(-2600)  # "-26.00"
```

---

## JSON storage example

```json
{
  "account": "401",
  "amount": 1920
}
```

No precision loss. No rounding surprises.

---

## Migration from float (one-time)

```python
from decimal import Decimal

def float_to_cents(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("0.01")) * 100)
```

---

## Summary (professional standard)

- ❌ float for money
- ❌ EPS-based balancing as final solution
- ✅ Integer cents for all calculations
- ✅ Decimal only for input/output
- ✅ `sum == 0` as a hard accounting rule

This approach is **production-grade**, scalable, and audit-safe.
