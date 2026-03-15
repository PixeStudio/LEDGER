import json
import traceback
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

class CancelOperation(Exception):
    pass

FILE = "ledger.json"
EPS = 0.0001 # tolerance for float in parse_amount_to_float


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
        "name": name
    }

    save_data(data)
    print(f"Account added: {code} - {name}")


def show_accounts(data):
    balances = calculate_balances(data)
    print("\nCHART OF ACCOUNTS")
    print("-" * 50)

    if not data["accounts"]:
        print("No accounts defined.")
        return

    for code, account in sorted(data["accounts"].items()):
        balance = balances.get(code, 0.0)
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


def parse_date(value):
    if isinstance(value, date):
        return value
    
    if not isinstance(value, str):
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

def postings_total(postings):
    total = 0.0
    for p in postings:
        total += p["amount"]
    return total

def print_postings(postings):
    print("\nCURRENT POSTINGS")
    print(f"{'No':>2}. {'Account':<6} {'Amount':>10}  Description")
    print("-" * 60)

    for i, p in enumerate(postings, start=1):
        acc = p["account"]
        amt = p["amount"]
        desc = p.get("description", "")

        print(f"{i:>2}. {acc:<6} {amt:>10.2f} {desc}")

    total = postings_total(postings)
    print("-" * 60)
    print(f"TOTAL: {total:+.2f}\n")

    if abs(total) < 0.0001:
        print("DOCUMENT IS BALANCED ✓")
    else:
        print(f"Difference to balance: {-total:+.2f}")

def fix_unbalanced_postings(data, postings):
    while True:
        total = postings_total(postings)

        if abs(total) < EPS:
            return True
        
        print_postings(postings)
        print("ERROR: Entry is not balanced.")
        print("Options:")
        print("   e - edit line")
        print("   d - delete line")
        print("   a - add new line")
        print("   q - quit editor")
        print("   c - cancel document")
        
        choice = input("Choose option: ").strip().lower()

        if choice == "q":
            return True
        elif choice == "c":
            confirm = input("Cancel document? (y/n): ").strip().lower()
            if confirm == "y":
                return False
            continue
        elif choice == "d":
            idx = input("Line number to delete: ").strip()
            if idx.isdigit():
                i = int(idx)
                if 1 <= i <= len(postings):
                    postings.pop(i - 1)
        elif choice == "e":
            idx = input("Line number to edit: ").strip()
            if not idx.isdigit():
                continue

            i = int(idx)
            if not (1 <= i <= len(postings)):
                continue

            raw = input_or_cancel("New amount (+ DR / - CR): ").strip()
            try:
                postings[i-1]["amount"] = parse_amount_to_float(raw)
            except ValueError:
                print("Invalid amount")
        elif choice == "a":
            while True:
                raw = input_or_cancel("Account code (ENTER to cancel): ").strip()
                if raw == "":
                    break
                if raw in data["accounts"]:
                    account = raw
                else:
                    print_account_suggestions(data, raw)
                    continue

                try: 
                    raw_amount  = input_or_cancel("Amount (+ DR / - CR): ").strip()
                    amount = parse_amount_to_float(raw_amount)
                except ValueError:
                    print("Invalid amount.")
                    continue

                desc = input_or_cancel("Line description: ").strip()

                postings.append({
                    "account": account,
                    "amount": amount,
                    "description": desc
                })

                break
    
# =========================
# DECRETATION CORE
# =========================

def amount_calculator():
    print("\nAMOUNT CALCULATOR")
    print("Enteramounts one per line.")
    print("Press ENTER on empty line to finish.\n")

    total = 0.0

    while True:
        raw = input("value (ENTER=finish): ").strip()

        if raw == "":
            break

        raw = raw.replace(",", ".")

        try:
            value = float(raw)
        except ValueError:
            print("Invalid number.")
            continue
        total += value
        print(f"TOTAL = {total:.2f}")
    print(f"TOTAL = {total:.2f}\n")
    return total

def calculate_balances(data):
    balances = {}

    for entry in data["journal"]:
        if entry.get("status", "POSTED") != "POSTED":
            continue

        for p in entry["postings"]:
            acc = p["account"]
            amount = p["amount"]
            
            balances[acc] = balances.get(acc, 0.0) + amount
    return balances

def compare_balances(data):
    calculated = calculate_balances(data)

    print("\nBALANCE CHECK (stored vs calculated)")
    print("-" * 50)

    for code, acc in data["accounts"].items():
        stored = acc.get("balance", 0.0)
        calc = calculated.get(code, 0.0)

        status = "OK" if abs(stored - calc) < 0.0001 else "DIFF"
        print(f"{code: <6} stored={stored:10.2f} calc={calc:10.2f} [{status}]")

def parse_amount_to_float(raw):
    # Allowes to write f.e. 19.20 & round at 2 point after 0
    s = raw.strip().replace(" ", "").replace(",",".")
    if s == "":
        raise ValueError("Empty amount")
    try:
        dec = Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(dec)
    except InvalidOperation:
        raise ValueError("Invalid amount")

def ym_from_year_month(y, m):
    return f"{int(y):04d}-{int(m):02d}"

def ensure_settings(data): 
    changed = False
    
    if "settings" not in data or not isinstance(data["settings"], dict):
        data["settings"] = {}
        changed = True
    
    s = data["settings"]

    if "current_period" not in s:
        if "open_year" in s and "open_month" in s:
            cp = ym_from_year_month(s["open_year"], s["open_month"])
        else:
            today = datetime.now().date()
            cp = f"{today.year:04d}-{today.month:02d}"
        s["current_period"] = cp
        changed = True

    if "periods" not in s or not isinstance(s["periods"], dict):
        s["periods"] = {}
        changed = True
    
    if s["current_period"] not in s["periods"]:
        s["periods"][s["current_period"]] = {"status": "OPEN"}
        changed = True

    if "open_year" in s:
        del s["open_year"]; changed = True
    if "open_month" in s:
        del s["open_month"]; changed = True

    if changed:
        save_data(data)

def maybe_prompt_new_period(data):
    s = data["settings"]
    current = s["current_period"]

    today = datetime.now().date()
    today_period = f"{today.year:04d}-{today.month:02d}"

    if today_period in s["periods"]:
        return
    
    print(f"\nDetected new month!")
    print(f"Today: {today_period} | Current period: {current}")

    ans = input("Create and switch to the new period? Y/N ").strip().lower()
    if ans != "y":
        return
    
    ans2 = input(f"New period will be created: {today_period}. Confirm? Y/N").strip().lower()
    if ans2 != "y":
        return
    
    # Create if not exist:

    s["periods"].setdefault(today_period, {"status": "OPEN"})
    s["current_period"] = today_period

    save_data(data)
    print(f"Switched current period to: {today_period}")
    

def input_date_from_current_period(data, label, default_date=None):
   s = data["settings"]
   current = s["current_period"]
   year = int(current.split("-")[0])
   month = int(current.split("-")[1])
   prefix = f"{year:04d}-{month:02d}-"

   today = datetime.now().date()
   if default_date is None:
    if today.year == year and today.month == month:
        default_date = today
    else:
        default_date = datetime(year, month, 1).date()
   while True:
        raw = input_or_cancel(
            f"{label} (DD or YYYY-MM-DD) [{prefix}__] (ENTER={default_date.isoformat()}): "
        )

        if raw =="":
            return default_date
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            d = parse_date(raw)
            if d and d.year == year and d.month == month:
                return d
            print(f"Date must be within current period {current}")
            continue
        if raw.isdigit():
            try:
                return datetime(year, month, int(raw)).date()
            except ValueError:
                print("Invalid day for this month.")
                continue
        print("Invalid input. Type day (e.g. 14) or full date (YYYY-MM-DD)")          

def show_periods(data):
    s = data["settings"]
    periods = s.get("periods", {})
    current = s.get("current_period")

    print("\nACCOUNTIG PERIODS")
    print("-" * 40)

    if not periods:
        print("No periods defined.")
        return

    for p in sorted(periods):
        status = periods[p].get("status", "UNKNOWN")

        if p == current:
            marker = "<-- current"
        else:
            marker = ""

        print(f"{p:<10} {status:<10} {marker}")
    
    print("-" * 40)    

def switch_period(data):
    s = data["settings"]
    periods = s.get("periods", {})
    current = s.get("current_period")

    print("\nSWITCH ACCOUNTING PERIOD")
    print(f"Current period: {current}")

    new_period = input("Enter period (YYYY-MM) or ENTER to cancel. ")

    if new_period == "":
        print("Operation cancelled.")

    if new_period not in periods:
        print("Period does not exist.")
        return
    
    if periods[new_period].get("status") == "CLOSED":
        print("This period is closed and cannot be activated.")
        return
    
    s["current_period"] = new_period
    save_data(data)

    print(f"Switched period: {new_period}")

def close_period(data):

    s = data["settings"]
    periods = s.get("periods", {})
    current = s.get("current_period")

    print("\nCLOSE ACCOUNTING PERIOD")

    p = input("Enter period to close (YYYY-MM) or ENTER to cancel: ").strip()

    if p == "":
        print("Operation cancelled.")
        return
    
    if p not in periods:
        print("Period does not exist.")
        return
    
    if periods[p].get("status") == "CLOSED":
        print("Period already closed.")
        return
    
    if p == current:
        print("Cannot close the current active period")
        return
    
    confirm = input(f"Close period {p}? This operation cannot be undone. Y/N").strip().lower()
    
    if confirm != "y":
        print("Operation cancelled.")
        return
    
    periods[p]["status"] = "CLOSED"

    save_data(data)
    print(f"Period {p} is now CLOSED")

def is_balanced(postings):
    total = 0.0
    for p in postings:
        total += p["amount"]
    return abs(total) < EPS


def post_entry(data, entry):
    postings = entry.get("postings", [])

    if not postings:
        print("ERROR: No postings entered.")
        return

    while not is_balanced(postings):
        ok = fix_unbalanced_postings(data, postings)
        if not ok:
            return

    for p in postings:
        code = p["account"]
        amount = p["amount"]

        if code not in data["accounts"]:
            print(f"ERROR: Account does not exist: {code}")
            return


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
                    "description": f"REVERSAL: {p.get('description', '')}"
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

def trial_balance(data):
    balances = calculate_balances(data)

    total_dr = 0.0
    total_cr = 0.0

    print("\nTRIAL BALANCE")
    print("-" * 60)
    print(f"{'Account':<6} {'Debit':>12} {'Credit':>12}")
    print("-" * 60)

    for code in sorted(balances):
        amount = balances[code]

        if amount > 0:
            dr = amount
            cr = 0.0
        elif amount < 0:
            dr = 0.0
            cr = -amount
        else:
            continue

        total_dr += dr
        total_cr += cr

        print(f"{code:<6} {dr:12.2f} {cr:12.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<6} {total_dr:12.2f} {total_cr:12.2f}")

    if abs(total_dr - total_cr) < 0.0001:
        print("STATUS: BALANCED ✔")
    else:
        print("STATUS: NOT BALANCED ❌")

def format_account_line(code, acc):
    name = acc.get("name", "")
    nature = acc.get("nature", "")
    acc_type = acc.get("type", "")
    group = acc.get("group", "")

    # Short formats
    group_short = group
    if len(group_short) > 28:
        group_short = group_short[:28] + "..."

    return f"{code:<8} {name:<28} {nature:<10} {acc_type:<10} {group_short}"

def suggest_accounts(data, prefix, limit=12):
    prefix = prefix.strip()
    if prefix == "":
        return []
    
    matches = []
    for code, acc in data["accounts"].items():
        if code.startswith(prefix):
            matches.append((code, acc))

    matches.sort(key=lambda x: x[0])
    return matches[:limit]

def print_account_suggestions(data, prefix, limit=12):
    matches = suggest_accounts(data, prefix, limit=limit)

    if not matches:
        print("No matching accounts.")
        return
    
    print("\nMatching accounts:")
    print("-" * 80)
    print(f"{'Code':<8} {'Name':<28} {'Nature':<10} {'Type':<10} {'Group'}")
    print("-" * 80)

    for code, acc in matches:
        print(format_account_line(code, acc))

    print("-" * 80)
    print("Tip: type full code (e.g. 101) to select, ENTER to finish.\n")

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
    print("6. Trial balance")
    print("7. Periods")
    print("9. Check balances (diagnostic)")
    print("0. Exit")

def input_or_cancel(prompt):
    s = input(prompt).strip()
    if s.lower() == "q":
        raise CancelOperation()
    return s

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

            try:
                print("\nADD PK DOCUMENT")
                s = data["settings"]
                current = s.get("current period")
                periods = s.get("periods", {})

                status = periods.get(current,{}).get("status")

                if status == "CLOSED":
                    print(f"\nERROR: Period{current} is CLOSED.")
                    print("Posting new documents is not allowed.")
                    return

                # Posting date (required)
                while True:
                    posting_date = input_date_from_current_period(data, "Posting date")

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
                        due_date = input_date_from_current_period(
                            data,
                            "Due date",
                            default_date=document_date
                        )

                        if due_date is None:
                            print("Operation cancelled.")
                            return
                        break

                        print("Invalid date format. Use YYYY-MM-DD (e.g. 2026-01-22).")

                # Source document number + description
                doc_ref = input_or_cancel("Source document number (optional): ").strip()
                description = input_or_cancel("Description: ").strip()

                # Postings (with account suggestions)
                postings = []
                last_account = None
                last_desc = None

                while True:
                    raw = input_or_cancel("Account code (ENTER to finish, ? for help, '.' repeat last or e - edit postings): ").strip()

                    if raw == "":
                        break

                    if raw == "?":
                        print("Type account prefix to see suggestion.")
                        continue

                    #edit postings
                    if raw == "e":
                        ok = fix_unbalanced_postings(data, postings)

                        if not postings:
                            print("No postings to edit.")
                            continue

                        if not ok:
                            print("Edit cancelled.")
                            continue
                        print_postings(postings)
                        continue

                    #repeat last account
                    if raw == ".":
                        if not last_account:
                            print("No previous account to repeat.")
                            continue    
                    #full account code
                    elif raw in data["accounts"]:
                        account = raw
                    #treat as prefix
                    else:
                        print_account_suggestions(data, raw, limit=12)
                        continue
                    

                    # Amount
                    raw_amount = input_or_cancel("Amount (+ DR / - CR) [type 'c' for calculator]: ").strip()
                    
                    if raw_amount.lower() == "c":
                        amount = amount_calculator()
                    else:
                        try:
                            amount = parse_amount_to_float(raw_amount)
                        except ValueError:
                            print("Invalid amount. Use e.g. 10.00 or -10.00")
                            continue

                    # Line description
                    while True:
                        line_desc = input_or_cancel("Line description ('+' repeat last): ").strip()

                        if line_desc == "+":
                            if last_desc is None:
                                print("No previous description to repeat.")
                                continue
                            line_desc = last_desc

                        postings.append({
                            "account": account,
                            "amount": amount,
                            "description": line_desc
                        })

                        last_account = account
                        last_desc = line_desc

                        print_postings(postings)
                        break

                
                    

                    

                # Build entry ONCE (after postings)
                if due_date is None:
                    print("ERROR: Due date not set!")
                    return
                
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
            except CancelOperation:
                print("Document entry canceled.")

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
            reverse_document(data, doc_id, reason)

        elif choice == "6":
            trial_balance(data)

        elif choice == "7":

            while True:
                print("\nPERIODS")
                print("1. Show period")
                print("2. Switch period")
                print("3. Close period")
                print("0. Back")

                p_choice = input("Choose option: ").strip()

                if p_choice == "1":
                    show_periods(data)
                elif p_choice == "2":
                    switch_period(data)
                elif p_choice == "3":
                    close_period(data)
                elif p_choice == "0":
                    break
                else:
                    print("Invalid input.")

        elif choice == "9":
            compare_balances(data)

        elif choice == "0":
            print("Goodbye.")
            break

        else:
            print("Invalid option.")


# =========================
# PROGRAM START
# =========================

data = load_data()
ensure_settings(data)
maybe_prompt_new_period(data)

if ledger_state(data) == "EMPTY":
    print("OPENING BALANCES ARE 0.00")
    print("NO RECORDS FROM PREVIOUS PERIOD FOUND")

try:
    run_app(data)
except Exception as e:
    print("\nCRITICAL ERROR:", e)
    print("\nTRACEBACK:")
    traceback.print_exc()