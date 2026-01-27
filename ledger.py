import json
from datetime import datetime

FILE = "ledger.json"


# =========================
# DATA LOADING / SAVING
# =========================

def load_data():
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =========================
# LEDGER STATE
# =========================

def ledger_state(data):
    if len(data["journal"]) == 0:
        return "EMPTY"
    return "HAS_RECORDS"


# =========================
# ACCOUNTS
# =========================

def add_account(data, code, name):
    if code in data["accounts"]:
        print(f"Account already exists: {code}")
        return

    data["accounts"][code] = {
        "name": name,
        "balance": 0.00
    }

    save_data(data)
    print(f"Account added: {code} - {name}")


def show_accounts(data):
    print("\nCHART OF ACCOUNTS")
    print("-" * 50)

    if not data["accounts"]:
        print("No accounts defined.")
        return

    for code, account in sorted(data["accounts"].items()):
        balance = account["balance"]
        side = "DR" if balance >= 0 else "CR"
        amount = abs(balance)
        print(f"{code:<6} {account['name']:<30} {amount:10.2f} {side}")


# =========================
# DOCUMENT HELPERS
# =========================

def next_entry_id(data):
    return len(data["journal"]) + 1


def next_doc_number(data, doc_type, posting_date_iso):
    year = posting_date_iso.split("-")[0]

    count = 0
    for entry in data["journal"]:
        if entry.get("doc_type") == doc_type and entry.get("posting_date", "").startswith(year):
            count += 1

    seq = count + 1
    return f"{doc_type}/{year}/{seq:04d}"


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


# =========================
# DECRETATION CORE
# =========================

def is_balanced(postings):
    total = 0.0
    for p in postings:
        total += p["amount"]
    return total == 0.0


def post_entry(data, entry):
    postings = entry.get("postings", [])

    if not postings:
        print("ERROR: No postings entered.")
        return

    if not is_balanced(postings):
        print("ERROR: Entry is not balanced.")
        return

    for p in postings:
        code = p["account"]
        amount = p["amount"]

        if code not in data["accounts"]:
            print(f"ERROR: Account does not exist: {code}")
            return

        data["accounts"][code]["balance"] += amount

    data["journal"].append(entry)
    save_data(data)

    print("Entry posted successfully.")
    print(f"Document: {entry['doc_number']} (ID: {entry['id']})")

def void_document(data, doc_id, reason):
    for entry in data["journal"]:
        if entry["id"] == doc_id:
            if entry["status"] != "POSTED":
                print("ERROR: Only POSTED documents can be voided.")
                return
            
            entry["status"] = "VOID"
            entry["void_reason"] = reason
            entry["void_date"] = datetime.now().date().isoformat()

            save_data(data)
            print(f"Document {entry['doc_number']} voided.")
            return
        print("ERROR: Document not found.")

def reverse_document(data, doc_id, reason):
    for entry in data["journal"]:
        if entry["id"] == doc_id:
            if entry.get("status", "POSTED") != "POSTED":
                print("ERROR: Only POSTED documents can be reversed.")
                return
            if "reversed_by" in entry:
                print("ERROR: Document already reversed.")
                return
            
            #create reversed postings 
            reversed_postings = []
            for p in entry["postings"]:
                reversed_postings.append({
                    "account": p["account"],
                    "amount": -p["amount"],
                    "description": f"REVERSAL: {p.get('description', "")}"
                })

            new_entry = {
                "id": next_entry_id(data),
                "doc_type": entry["doc_type"],
                "doc_number": next_doc_number(data, entry["doc_type"], datetime.now().date().isoformat()),
                "status": "POSTED",
                "reversal_of": entry["id"],
                "posting_date": datetime.now().date().isoformat(),
                "document_date": datetime.now().date().isoformat(),
                "counterparty": entry.get("counterparty", ""),
                "due_date": datetime.now().date().isoformat(),
                "description": f"REVERSAL OF {entry['doc_number']} - {reason}",
                "postings": reversed_postings
            }

            #apply reversed entry
            post_entry(data, new_entry)

            #mark original as reversed
            entry["status"] = "REVERSED"
            entry["reversed_by"] = new_entry["id"]

            save_data(data)
            print(f"Document {entry['doc_number']} reversed.")
        print("ERROR: Document not found")


# =========================
# MENU
# =========================

def main_menu():
    print("\nMAIN MENU")
    print("1. Add account")
    print("2. Show accounts")
    print("3. Add document")
    print("4. Void document")
    print("5. Reverse document")
    print("0. Exit")


def run_app(data):
    while True:
        main_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            code = input("Account code: ").strip()
            name = input("Account name: ").strip()

            if not code.isdigit():
                print("Account code must contain digits only.")
                continue

            add_account(data, code, name)

        elif choice == "2":
            show_accounts(data)

        elif choice == "3":
            print("\nADD PK DOCUMENT")

            # Posting date (required)
            while True:
                posting_input = input("Posting date (YYYY-MM-DD): ").strip()
                posting_date = parse_date(posting_input)

                if posting_date is not None:
                    break

                print("Invalid date format. Use YYYY-MM-DD (e.g. 2026-01-22).")

            # Document date (optional)
            doc_input = input("Document date (YYYY-MM-DD) [ENTER = posting date]: ").strip()
            if doc_input == "":
                document_date = posting_date
            else:
                parsed = parse_date(doc_input)
                if parsed is not None:
                    document_date = parsed
                else:
                    print("Invalid document date. Using posting date.")
                    document_date = posting_date

            # Counterparty
            counterparty = input("Counterparty: ").strip()

            # Payment method
            while True:
                print("Payment method:")
                print("1. Cash")
                print("2. Card")
                print("3. Bank transfer")
                pm = input("Choose (1/2/3): ").strip()

                if pm == "1":
                    payment_method = "CASH"
                    break
                elif pm == "2":
                    payment_method = "CARD"
                    break
                elif pm == "3":
                    payment_method = "TRANSFER"
                    break
                else:
                    print("Invalid option.")

            # Due date
            if payment_method == "CASH":
                due_date = document_date
            else:
                while True:
                    due_input = input("Due date (YYYY-MM-DD) [ENTER = document date]: ").strip()
                    if due_input == "":
                        due_date = document_date
                        break

                    parsed = parse_date(due_input)
                    if parsed is not None:
                        due_date = parsed
                        break

                    print("Invalid date format. Use YYYY-MM-DD (e.g. 2026-01-22).")

            # Source document number + description
            doc_ref = input("Source document number (optional): ").strip()
            description = input("Description: ").strip()

            # Postings
            postings = []
            while True:
                account = input("Account code (or ENTER to finish): ").strip()
                if account == "":
                    break

                if account not in data["accounts"]:
                    print("Account does not exist.")
                    continue

                try:
                    raw_amount = input("Amount (+ DR / - CR): ").strip()
                    raw_amount = raw_amount.replace(",", ".")
                    amount = float(raw_amount)
                except ValueError:
                    print("Invalid amount.")
                    continue

                line_desc = input("Line descritpion: ").strip()

                postings.append({"account": account, "amount": amount, "descritpion": line_desc})

            # Build entry ONCE (after postings)
            posting_iso = posting_date.isoformat()
            entry = {
                "id": next_entry_id(data),
                "doc_type": "PK",
                "doc_number": next_doc_number(data, "PK", posting_iso),
                "doc_ref": doc_ref,
                "posting_date": posting_iso,
                "document_date": document_date.isoformat(),
                "counterparty": counterparty,
                "payment_method": payment_method,
                "due_date": due_date.isoformat(),
                "description": description,
                "status": "POSTED",
                "postings": postings
            }

            post_entry(data, entry)

        elif choice == "4":
            try:
                doc_id = int(input("Document ID to void: "))
            except ValueError:
                print("Invalid ID.")
            reason = input("Reason for voiding: ").strip()
            void_document(data, doc_id, reason)

        elif choice == "5":
            try:
                doc_id = int(input("Document ID to reverse: ").strip())
            except ValueError:
                print("Invalid ID.")
                continue
            reason = input("Reason for reverse: ").strip()

        elif choice == "0":
            print("Goodbye.")
            break

        else:
            print("Invalid option.")

        reverse_document(data, doc_id, reason)


# =========================
# PROGRAM START
# =========================

data = load_data()

if ledger_state(data) == "EMPTY":
    print("OPENING BALANCES ARE 0.00")
    print("NO RECORDS FROM PREVIOUS PERIOD FOUND")

run_app(data)