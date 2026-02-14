def debug_float_sum():
    values = [19.2, 2.3, 4.5]
    total = 0.0

    for v in values:
        total += v
        print(f"after adding {v}: {total!r}")

    print("-" * 40)
    print(f"final total repr: {total!r}")

    print("final total == 26.0 ?", total == 26.0)
    print("26.0 - total =", 26.0 - total)

debug_float_sum()

def debug_order():
    total = 0.0
    for v in [2.3, 19.2, 4.5]:
        total += v
        print(f"{total!r}")

debug_order()

def debug_order_2():
    total = 19.2
    total += 4.5
    total += 2.3
    print(f"{total!r}")
    n = 0.1 + 0.2
    print(n)

debug_order_2()

