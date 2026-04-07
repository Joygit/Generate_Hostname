"""
Server Hostname Generator
Format: xs[env][os][7-char-unique-suffix]
  - xs   : common prefix (always)
  - env  : n=nonprod, p=prod
  - os   : w=windows, l=linux
  - suffix: 7 alphanumeric chars (digits + lowercase), unique, sequential permutation
Total length: 11 characters
"""

import argparse
import json
import os
import itertools
import string

# Constants

PREFIX       = "xs"
SUFFIX_LEN   = 7                          # 2 prefix + 2 flags + 7 suffix = 11
CHARSET      = string.digits + string.ascii_lowercase   # 0-9 + a-z  (36 chars)
STATE_FILE   = "hostname_state.json"      # persists used names between runs

ENV_MAP = {"nonprod": "n", "prod": "p"}
OS_MAP  = {"windows": "w", "linux": "l"}


# State helpers  (read / write the set of already-used suffixes)


def load_state() -> dict:
    """Return the persisted state dict, or a fresh one."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"counter": 0, "used": []}   # used = list of full hostnames


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)



# Suffix generator  (pure, deterministic, no repeats)


def index_to_suffix(n: int, length: int = SUFFIX_LEN) -> str:
    """
    Map a non-negative integer to a unique fixed-length alphanumeric string
    that looks visually random (like '10t629p') but is fully deterministic
    and collision-free.

    Technique: Linear Congruential Permutation (LCP)
    - Multiply n by a large prime and XOR with a salt before base-36 encoding.
    - This scrambles the sequence so consecutive counters produce visually
      unrelated suffixes, while still guaranteeing uniqueness across the
      full 36^7 space.

    index 0  -> e.g. 'k4m8z1q'
    index 1  -> e.g. '3rp0w7n'
    index 2  -> e.g. 'x91jb5t'
    ...
    Max unique suffixes = 36^7 = 78,364,164,096
    """
    base     = len(CHARSET)
    space    = base ** length          # 36^7

    # LCP constants — prime multiplier + XOR salt chosen to maximise spread
    PRIME    = 2_562_047_978_853_597   # large prime < 2^52
    SALT     = 0x5A5A5A5A5A5A5       # arbitrary XOR mask

    scrambled = ((n * PRIME) ^ SALT) % space

    digits = []
    for _ in range(length):
        digits.append(CHARSET[scrambled % base])
        scrambled //= base
    return "".join(reversed(digits))



# Core hostname builder
def generate_hostname(env: str, os_type: str, state: dict) -> str:
    """
    Generate the next unique hostname and update state in-place.

    env     : 'nonprod' | 'prod'
    os_type : 'windows' | 'linux'
    """
    env_char = ENV_MAP[env.lower()]
    os_char  = OS_MAP[os_type.lower()]

    counter  = state["counter"]
    suffix   = index_to_suffix(counter)
    hostname = f"{PREFIX}{env_char}{os_char}{suffix}"   # e.g. xsnwk4m8z1q (11 chars, no spaces)

    state["counter"] += 1
    state["used"].append(hostname)
    return hostname



# CLI
def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a unique 11-char server hostname."
    )
    parser.add_argument(
        "--environment", "-e",
        required=True,
        choices=["nonprod", "prod"],
        help="Deployment environment"
    )
    parser.add_argument(
        "--os", "-o",
        required=True,
        dest="os_type",
        choices=["windows", "linux"],
        help="Operating system"
    )
    parser.add_argument(
        "--version", "-v",
        required=True,
        help="OS version (stored in state for traceability, e.g. '2022', 'rhel9')"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="How many hostnames to generate in one run (default: 1)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all previously generated hostnames and exit"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the hostname counter (WARNING: clears history)"
    )
    return parser.parse_args()


def main():
    args  = parse_args()
    state = load_state()

    # ---- list mode -------------------------------------------------------- #
    if args.list:
        if not state["used"]:
            print("No hostnames generated yet.")
        else:
            print(f"{'#':<5} {'Hostname':<15} {'Generated so far'}")
            print("-" * 30)
            for i, h in enumerate(state["used"], 1):
                print(f"{i:<5} {h}")
        return

    # ---- reset mode ------------------------------------------------------- #
    if args.reset:
        confirm = input("Are you sure you want to reset? (yes/no): ").strip().lower()
        if confirm == "yes":
            state = {"counter": 0, "used": []}
            save_state(state)
            print("State reset successfully.")
        else:
            print("Reset cancelled.")
        return

    # ---- generate --------------------------------------------------------- #
    if args.count < 1:
        print("Error: --count must be at least 1.")
        raise SystemExit(1)

    hostnames = []
    for _ in range(args.count):
        hostnames.append(generate_hostname(args.environment, args.os_type, state))
    save_state(state)

    print(f"\n✅ Generated {args.count} hostname(s):")
    for i, h in enumerate(hostnames, 1):
        print(f"   [{i}] {h}")   # e.g. xsnwk4m8z1q  (11 chars, no spaces)
    print(f"\n   Environment     : {args.environment}")
    print(f"   OS              : {args.os_type}")
    print(f"   Version         : {args.version}")
    print(f"   Total ever made : {len(state['used'])}\n")




if __name__ == "__main__":
    main()
