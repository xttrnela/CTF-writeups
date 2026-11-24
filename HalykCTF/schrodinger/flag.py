def rotl8(val: int, shift: int) -> int:
    shift &= 7
    val &= 0xFF
    return ((val << shift) | (val >> (8 - shift))) & 0xFF


def jit_eval(c: int, idx: int) -> int:
    s = idx & 7
    u_var2 = rotl8(0x5C, s) if s != 0 else 0x5C
    term1 = ((c * (-0x55)) ^ u_var2) & 0xFF
    term2 = (idx * 0x11) & 0xFF
    return (term1 + term2) & 0xFF


table = bytes.fromhex("21e8b25031d9522498629baec55faeb000d0")
key = bytes.fromhex("5a3c91e712886df0")

targets = [table[i] ^ key[i % 8] for i in range(18)]

chars = []
for idx in range(18):
    matches = [chr(c) for c in range(32, 127) if jit_eval(c, idx) == targets[idx]]
    print(f"idx={idx:02d}: target=0x{targets[idx]:02x} -> {matches}")
    chars.append(matches[0] if len(matches) == 1 else "?")

flag = "HalykCTF{" + "".join(chars) + "}"
print("Candidate flag:", flag)

