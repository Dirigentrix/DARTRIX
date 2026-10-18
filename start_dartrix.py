#!/usr/bin/env python3
"""DARTRIX OS v2.0 - boot banner and deterministic kernel start.
Autor: Daniel Adrian Ratajczyk (Dirigentrix)
"""

from dartrix_os import DARTRIX_OS

BANNER = """
==============================================
  DARTRIX OS v2.0
  Deterministic Meta-OS for Agent Orchestration
  Autor: Daniel Adrian Ratajczyk (Dirigentrix)
==============================================
"""


def main():
    print(BANNER)
    os_instance = DARTRIX_OS()
    os_instance.boot()
    result = os_instance.run_cycle({"type": "SYSTEM_CHECK", "payload": "v2.0 boot"})
    for res in result:
        print(f"-> {res['role']}: {res['status']}")


if __name__ == "__main__":
    main()
