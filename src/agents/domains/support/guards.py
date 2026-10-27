"""Guardrails around the support agent: check the question before the LLM sees it and the reply before the customer does.

Real data security is in the tools (runtime.context); these guards are a second wall for quality and safety.
"""

import logging
import re
from pathlib import Path
from typing import Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from agents.core.prompts import load_prompt
from apps.customers.models import Customer
from config.env import env
from infra.llm.gateway import get_chat_model

from .state import BlockedReason, Language

logger = logging.getLogger(__name__)

INPUT_GUARD_PROMPT = Path(__file__).parent / "prompts" / "input_guard.v1.md"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"\+?\d[\d\s-]{7,}\d")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
ORDER_RE = re.compile(r"\bORD-\d+\b", re.IGNORECASE)

# Lower-case; first-person claims only, so "order ORD-1 was refunded" (a real status) stays allowed.
BANNED_PHRASES = (
    "payment link", "orders page", "order page", "click here", "dashboard", "portal",
    "i have refunded", "i've refunded", "i have cancelled", "i've cancelled",
    "i have forwarded", "i've forwarded", "i will forward", "i'll forward",
    "i have escalated", "i've escalated", "i will escalate", "i'll escalate",
    "i have sent", "i've sent", "i will send", "i'll send",
    "refund kar diya", "cancel kar diya", "forward kar diya", "forward kar deta", "link bhej", "bhej diya",
)

REPLY_LANGUAGE = {
    "english": "English",
    "roman_urdu": "Roman Urdu (Urdu written in English letters), never in Urdu or Hindi script",
    "urdu": "Urdu in Urdu script",
}

REFUSALS: dict[BlockedReason, dict[Language, str]] = {
    "other_customer": {
        "english": "For privacy reasons I can only help with your own account and orders. I can't share or look up anyone else's details.",
        "roman_urdu": "Privacy ki wajah se main sirf aap ke apne account aur orders mein madad kar sakta hoon. Kisi aur ki maloomat main nahi dekh sakta.",
        "urdu": "رازداری کی وجہ سے میں صرف آپ کے اپنے اکاؤنٹ اور آرڈرز میں مدد کر سکتا ہوں۔ کسی اور کی معلومات میں نہیں دیکھ سکتا۔",
    },
    "prompt_injection": {
        "english": "I can't change how I work or share internal information. I'm happy to help with your own profile, orders and spending.",
        "roman_urdu": "Main apne rules nahi badal sakta aur andar ki maloomat share nahi kar sakta. Aap ke apne profile, orders aur kharche mein madad kar sakta hoon.",
        "urdu": "میں اپنے اصول نہیں بدل سکتا اور اندرونی معلومات شیئر نہیں کر سکتا۔ آپ کی اپنی پروفائل، آرڈرز اور خرچ میں مدد کر سکتا ہوں۔",
    },
    "off_topic": {
        "english": "I can only help with your account here: your profile, your orders and your spending.",
        "roman_urdu": "Main yahan sirf aap ke account mein madad kar sakta hoon: profile, orders aur kharcha.",
        "urdu": "میں یہاں صرف آپ کے اکاؤنٹ میں مدد کر سکتا ہوں: پروفائل، آرڈرز اور خرچ۔",
    },
}

SAFE_FALLBACK: dict[Language, str] = {
    "english": "Sorry, I can't confirm that from your account data. Here I can help with your profile, orders and spending; for anything else please contact the support team.",
    "roman_urdu": "Maazrat, main ye baat aap ke account ke data se confirm nahi kar sakta. Yahan main profile, orders aur kharche mein madad kar sakta hoon; baqi cheezon ke liye support team se rabta karein.",
    "urdu": "معذرت، میں یہ بات آپ کے اکاؤنٹ کے ڈیٹا سے تصدیق نہیں کر سکتا۔ یہاں میں پروفائل، آرڈرز اور خرچ میں مدد کر سکتا ہوں؛ باقی کے لیے سپورٹ ٹیم سے رابطہ کریں۔",
}


class InputVerdict(BaseModel):
    decision: Literal["allowed", "other_customer", "prompt_injection", "off_topic"] = Field(
        description="What kind of message this is."
    )
    language: Language = Field(description="Language of the customer's latest message.")


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def mentions_other_person(message: str, customer: Customer) -> bool:
    """Free check before any LLM call: an email or phone number in the message that is not the customer's own."""
    own_email = (customer.email or "").lower()
    if any(email.lower() != own_email for email in EMAIL_RE.findall(message)):
        return True
    own_phone = _digits(customer.phone)[-9:]
    return any(_digits(phone)[-9:] != own_phone for phone in PHONE_RE.findall(message) if len(_digits(phone)) >= 9)


def classify_input(message: str, *, company_name: str, customer_name: str, previous_language: Language) -> InputVerdict:
    prompt = load_prompt(
        INPUT_GUARD_PROMPT, company_name=company_name, customer_name=customer_name, previous_language=previous_language
    )
    llm = get_chat_model(model=env.llm_guard_model).with_structured_output(InputVerdict)
    return llm.invoke([SystemMessage(prompt), HumanMessage(message)])


def _normalize(text: str) -> str:
    # The LLM writes typographic hyphens, spaces and apostrophes (e.g. U+2011 in "ORD‑1002") that plain regexes miss.
    text = re.sub(r"[  ]", " ", text).replace("’", "'")
    return re.sub(r"[‐-―−]", "-", text)


def check_output(reply: str, messages: list[BaseMessage]) -> list[str]:
    """Return what is wrong with the reply (empty list = fine): ungrounded emails, links or order numbers, or banned claims."""
    reply = _normalize(reply)
    evidence = _normalize(" ".join(str(m.content) for m in messages if isinstance(m, (HumanMessage, ToolMessage)))).lower()
    flags = [f"ungrounded_email:{email}" for email in EMAIL_RE.findall(reply) if email.lower() not in evidence]
    flags += [f"ungrounded_link:{url}" for url in URL_RE.findall(reply) if url.lower() not in evidence]
    flags += [f"ungrounded_order:{number}" for number in ORDER_RE.findall(reply) if number.lower() not in evidence]
    lower_reply = reply.lower()
    flags += [f"banned_phrase:{phrase}" for phrase in BANNED_PHRASES if phrase in lower_reply]
    return flags
