import argparse
import json
import os
import string

# -- Constants
PREFIX    = "xs"
CHARSET   = string.digits + string.ascii_lowercase  # 0-9, a-z (36 chars)
STATE_FILE = "hostname_state.json"

ENV_MAP = {"nonprod": "n", "prod": "p"}
OS_MAP  = {"windows": "w", "linux": "l"}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"counter": 0, "used": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def index_to_suffix(n, length=7):
    # LCP scramble: spreads sequential counters far apart visually
    # while staying a strict 1-to-1 mapping (no duplicates ever)
    base    = len(CHARSET)
    space   = base ** length
    PRIME   = 2_562_047_978_853_597
    SALT    = 0x5A5A5A5A5A5A5
    n       = ((n * PRIME) ^ SALT) % space
    digits  = []
    for _ in range(length):
        digits.append(CHARSET[n % base])
        n //= base
    return "".join(reversed(digits))


def generate(env, os_type, count, state):
    # Build each hostname: xs + env_char + os_char + 7-char unique suffix = 11 chars
    hostnames = []
    for _ in range(count):
        suffix   = index_to_suffix(state["counter"])
        hostname = f"{PREFIX}{ENV_MAP[env]}{OS_MAP[os_type]}{suffix}"
        # Windows hostnames are uppercase, Linux are lowercase
        hostname = hostname.upper() if os_type == "windows" else hostname.lower()
        state["counter"] += 1
        state["used"].append(hostname)
        hostnames.append(hostname)
    return hostnames


def main():
    parser = argparse.ArgumentParser(description="Generate unique 11-char server hostnames.")
    parser.add_argument("--environment", "-e", required=True, choices=["nonprod", "prod"])
    parser.add_argument("--os",          "-o", required=True, choices=["windows", "linux"], dest="os_type")
    parser.add_argument("--count",       "-c", type=int, default=1)
    parser.add_argument("--list",        "-l", action="store_true", help="List all generated hostnames")
    args = parser.parse_args()

    state = load_state()

    if args.list:
        if not state["used"]:
            print("No hostnames generated yet.")
        else:
            for i, h in enumerate(state["used"], 1):
                print(f"  [{i:>3}] {h}")
        return

    if args.count < 1:
        print("Error: --count must be at least 1.")
        raise SystemExit(1)

    hostnames = generate(args.environment, args.os_type, args.count, state)
    save_state(state)

    # Print results — workflow step will parse these lines for GITHUB_OUTPUT
    print(f"environment={args.environment}")
    print(f"os={args.os_type}")
    print(f"count={args.count}")
    print(f"total_ever={len(state['used'])}")
    for i, h in enumerate(hostnames, 1):
        print(f"hostname_{i}={h}")


if __name__ == "__main__":
    main()
