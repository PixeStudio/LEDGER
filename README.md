# 📘 Budget Ledger — Core Accounting Rules (README)

## 1. Purpose of the Project

Budget Ledger is a learning-oriented accounting engine designed to model **real accounting logic**, not just data entry.

Key goals:
- correctness before convenience  
- full audit trail  
- immutable accounting history  
- explicit handling of errors and corrections  

This project prioritizes **understanding accounting mechanics** over UI or automation.

---

## 2. Core Concepts

### 2.1 Accounting Document

An accounting document represents a **recorded decision**, not just numbers.

Each document contains:
- unique internal ID
- document type (e.g. PK)
- document number (auto-generated)
- dates (posting, document, due)
- counterparty
- payment method
- postings (debit / credit lines)
- status

Documents are **never deleted**.

---

### 2.2 Posting (Accounting Line)

A posting is a single accounting line containing:
- account code
- amount
- description

Rules:
- positive amount → Debit (DR)
- negative amount → Credit (CR)

A document must be **balanced**:

    sum(postings.amount) == 0.00

---

## 3. Document Statuses

### 3.1 POSTED

- default status for a valid accounting document
- affects account balances
- included in all reports

POSTED documents represent **accepted accounting facts**.

---

### 3.2 VOID

VOID marks a document as **formally invalid**.

Used when:
- a document should never have been recorded
- wrong entity
- wrong ownership
- input mistake unrelated to accounting logic

Characteristics:
- document remains in the system
- document does NOT represent a valid accounting fact
- VOID documents are excluded from accounting results
- VOID does NOT create accounting postings

VOID exists for:
- audit trail
- historical accountability
- learning from past errors

---

### 3.3 REVERSED

REVERSED marks a document whose **accounting effects were explicitly reversed**.

Characteristics:
- original document remains unchanged
- a new reversing document is created
- reversing document has opposite postings
- balances are corrected via a new accounting record

REVERSED documents represent:
- valid documents that required correction
- accounting-level adjustments (storno)

---

## 4. VOID vs REVERSE — Key Distinction

| Aspect | VOID | REVERSE |
|------|------|--------|
| Purpose | Formal invalidation | Accounting correction |
| Affects balances | No | Yes |
| Creates new document | No | Yes |
| Used for | “This should never exist” | “This was wrong financially” |
| Audit trail | Yes | Yes |

VOID and REVERSE are **independent operations**.

---

## 5. Balance Calculation Model (IMPORTANT)

### Current model (temporary):
- account balances are materialized
- balances change at posting time
- VOID does not affect balances directly
- REVERSE is required to correct balances

### Target model (planned):
- journal is the **only source of truth**
- balances are calculated dynamically
- only POSTED documents affect balances
- VOID documents are automatically ignored

This refactor is planned and documented.

---

## 6. Accounting Integrity Rules

1. Documents are immutable  
2. Balances change only via accounting documents  
3. No document is physically deleted  
4. Corrections are explicit and traceable  
5. History is preserved even for errors  

---

## 7. Design Philosophy

This system favors:
- explicit logic over hidden automation
- traceability over convenience
- correctness over speed
- learning over shortcuts

---

## 8. Roadmap (Relevant to Core Logic)

1. Finalize documentation of rules ✅  
2. Refactor balance calculation (dynamic balances)  
3. Integrate reference chart of accounts (staged)  
4. Improve CLI UX (suggestions, validation)  
5. Prepare backend interface (Flask / API)  

---

## 9. Final Note

Budget Ledger is not meant to mimic existing accounting software blindly.  
It is meant to **explain accounting by implementing it**.
