"""Talk to the streaming chat API like a frontend would and print the SSE events live.

    uv run python playground/stream_client.py "give me my orders"
    uv run python playground/stream_client.py "and why did it fail?" --conversation demo-1
    uv run python playground/stream_client.py "my orders" --customer sara@example.com
"""

import argparse
import json
import sys

import django_setup  # noqa: F401  (only used to look up the demo ids by phone/email)
import httpx
from django.db.models import Q

from apps.customers.models import Customer
from core.models import Tenant


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--tenant", default="demo-company")
    parser.add_argument("--customer", default="+923001234567", help="customer phone or email")
    parser.add_argument("--conversation", default=None, help="reuse a conversation id to continue a chat")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    tenant = Tenant.objects.get(slug=args.tenant)
    customer = Customer.objects.get(Q(phone=args.customer) | Q(email=args.customer), tenant=tenant)
    headers = {"X-Tenant-Public-Id": str(tenant.public_id), "X-Customer-Public-Id": str(customer.public_id)}
    body = {"message": args.message, "conversation_id": args.conversation}

    event = None
    with httpx.stream("POST", f"{args.base_url}/api/chat/messages/stream", json=body, headers=headers, timeout=120) as response:
        if response.status_code != 200:
            print(f"HTTP {response.status_code}: {response.read().decode()}")
            return
        for line in response.iter_lines():
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
                if event == "token":
                    sys.stdout.write(data["text"])
                    sys.stdout.flush()
                else:
                    print(f"\n[{event}] {data}")


if __name__ == "__main__":
    main()
