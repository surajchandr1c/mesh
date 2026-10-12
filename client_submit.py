"""QThorium Mesh - Distributed Task Client (PC 1 / Submitter).

This script runs on PC 1 (or any client machine) to submit tasks to PC 2
(the central orchestrator and compute mesh) and stream inference tokens in real-time.

Usage:
    # Single prompt:
    python client_submit.py --host 192.168.1.50 --prompt "Explain quantum computing in simple terms"

    # Interactive chat mode:
    python client_submit.py --host 192.168.1.50 --interactive

    # With RAG retrieval disabled:
    python client_submit.py --host 192.168.1.50 --prompt "Hello" --no-rag
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional

try:
    import httpx
except ImportError:
    print("\n[ERROR] 'httpx' is required to run the mesh client.")
    print("Install it with: pip install httpx\n")
    sys.exit(1)


# Color formatting helpers for Windows Terminal / PowerShell
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def check_orchestrator_health(base_url: str) -> bool:
    """Verify that PC 2's orchestrator is reachable and healthy."""
    health_url = f"{base_url}/health"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(health_url)
            if resp.status_code == 200:
                data = resp.json()
                print(f"{GREEN}[OK]{RESET} Connected to QThorium Orchestrator: {data.get('service')} (Redis: {data.get('redis')})")
                return True
            else:
                print(f"{RED}[FAIL]{RESET} Orchestrator responded with status {resp.status_code}: {resp.text}")
                return False
    except Exception as exc:
        print(f"{RED}[ERROR]{RESET} Cannot reach orchestrator at {health_url}: {exc}")
        print(f"{YELLOW}[HINT]{RESET} Ensure PC 2 has started uvicorn and Windows Firewall allows inbound port 8000.")
        return False


def get_auth_token(base_url: str) -> Optional[str]:
    """Retrieve a signed JWT token from the orchestrator if available."""
    token_url = f"{base_url}/api/v1/auth/token?user_id=pc1_client"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(token_url)
            if resp.status_code == 200:
                return resp.json().get("access_token")
    except Exception:
        pass
    return None


def submit_and_stream_task(
    base_url: str,
    prompt: str,
    max_tokens: int = 256,
    rag_enabled: bool = False,
    auth_token: Optional[str] = None,
) -> bool:
    """Submit prompt to orchestrator and stream tokens back in real-time."""
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    submit_url = f"{base_url}/api/v1/tasks/submit"
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "rag_enabled": rag_enabled,
        "target_model": "llama3.2:1b",
    }

    print(f"\n{CYAN}--- Submitting Task to Compute Mesh ---{RESET}")
    print(f"{DIM}Prompt:{RESET} {prompt}")
    print(f"{DIM}Target Model:{RESET} llama3.2:1b | {DIM}RAG:{RESET} {rag_enabled} | {DIM}Max Tokens:{RESET} {max_tokens}")

    start_time = time.time()
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(submit_url, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"{RED}[Submission Failed]{RESET} Status {resp.status_code}: {resp.text}")
                return False

            data = resp.json()
            task_id = data.get("task_id")
            print(f"{GREEN}[Dispatched]{RESET} Task ID: {MAGENTA}{task_id}{RESET}")

    except Exception as exc:
        print(f"{RED}[Connection Error]{RESET} Failed to submit task: {exc}")
        return False

    # Now listen to the SSE token stream from PC 2
    stream_url = f"{base_url}/api/v1/tasks/stream/{task_id}"
    print(f"{CYAN}--- Streaming Model Response from PC 2 ---{RESET}\n")

    token_count = 0
    stream_start = time.time()

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("GET", stream_url, headers=headers) as response:
                if response.status_code != 200:
                    print(f"{RED}[Stream Error]{RESET} HTTP {response.status_code}")
                    return False

                current_event = None
                for line in response.iter_lines():
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        continue

                    if line.startswith("data:"):
                        data_str = line.split(":", 1)[1].strip()
                        try:
                            chunk_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if current_event == "token":
                            token_str = chunk_data.get("token", "")
                            # Print token smoothly to stdout
                            sys.stdout.write(token_str)
                            sys.stdout.flush()
                            token_count += 1

                            if chunk_data.get("is_last"):
                                break

                        elif current_event == "error":
                            print(f"\n{RED}[Stream Error]{RESET} {chunk_data.get('message')}")
                            return False

                        elif current_event == "cancelled":
                            print(f"\n{YELLOW}[Stream Cancelled]{RESET} {chunk_data.get('message')}")
                            return False

    except httpx.ReadTimeout:
        print(f"\n{YELLOW}[Timeout]{RESET} Inference response timed out after 60s.")
    except Exception as exc:
        print(f"\n{RED}[Stream Exception]{RESET} {exc}")

    elapsed = time.time() - stream_start
    tps = token_count / elapsed if elapsed > 0 else 0.0

    print(f"\n\n{DIM}----------------------------------------{RESET}")
    print(f"{GREEN}✓ Completed in {elapsed:.2f}s | {token_count} tokens | {tps:.2f} tok/s{RESET}\n")
    return True


def interactive_mode(base_url: str, auth_token: Optional[str] = None):
    """Run an interactive prompt session with PC 2's compute mesh."""
    print(f"\n{BOLD}{CYAN}=== QThorium Mesh - Interactive Client Mode ==={RESET}")
    print(f"Connected to: {GREEN}{base_url}{RESET}")
    print("Type your prompt and press Enter. Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            prompt = input(f"{BOLD}{MAGENTA}[Mesh Client]> {RESET}").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print("Exiting client.")
                break
            submit_and_stream_task(
                base_url=base_url,
                prompt=prompt,
                max_tokens=300,
                rag_enabled=False,
                auth_token=auth_token,
            )
        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Exiting.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="QThorium Mesh Distributed Client (PC 1 Submitter)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("ORCHESTRATOR_HOST", "localhost"),
        help="Host IP or hostname of PC 2 (Main Orchestrator)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ORCHESTRATOR_PORT", "8000")),
        help="Port of PC 2 Orchestrator",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="",
        help="Prompt to execute on the mesh",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Maximum generation tokens",
    )
    parser.add_argument(
        "--rag",
        action="store_true",
        default=False,
        help="Enable RAG knowledge retrieval on PC 2",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Launch interactive conversation loop",
    )

    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    print(f"{BOLD}Connecting to QThorium Mesh Orchestrator at {base_url}...{RESET}")
    if not check_orchestrator_health(base_url):
        print(f"\n{RED}Cannot establish connection to PC 2 orchestrator.{RESET}")
        print(f"1. Make sure PC 2 is running: uvicorn track2_orchestrator.main:app --host 0.0.0.0 --port 8000")
        print(f"2. Verify IP: on PC 2 run 'ipconfig' and use its IPv4 address.")
        sys.exit(1)

    auth_token = get_auth_token(base_url)

    if args.interactive or not args.prompt:
        interactive_mode(base_url, auth_token=auth_token)
    else:
        submit_and_stream_task(
            base_url=base_url,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            rag_enabled=args.rag,
            auth_token=auth_token,
        )


if __name__ == "__main__":
    main()
