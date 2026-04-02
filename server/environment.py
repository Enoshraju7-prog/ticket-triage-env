import json
import os
import re
from uuid import uuid4

try:
    from ticket_triage_env.models import TicketTriageAction, TicketTriageObservation
except ImportError:
    from models import TicketTriageAction, TicketTriageObservation

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

TICKETS = [
    {"id":"T001","subject":"Double charged this month","body":"I was charged twice for my Pro subscription on March 1st. Transaction IDs: TXN-4421 and TXN-4422. Please refund the duplicate charge.","customer_tier":"pro","category":"billing","priority":"high","department":"billing_team","key_points":["apologize","refund","timeline"]},
    {"id":"T002","subject":"Locked out of my account","body":"I've been locked out for 2 hours. Tried resetting password but the email never arrived. I have an important presentation tomorrow.","customer_tier":"free","category":"technical","priority":"medium","department":"tech_support","key_points":["apologize","troubleshoot","steps"]},
    {"id":"T003","subject":"Package arrived completely damaged","body":"My order #ORD-8821 arrived today crushed. The laptop stand is bent and unusable. I paid $89.99 for this.","customer_tier":"pro","category":"shipping","priority":"high","department":"logistics","key_points":["apologize","replacement","photo"]},
    {"id":"T004","subject":"How do I export my data?","body":"I need to export all my project data before my subscription expires next week. Where do I find the export option?","customer_tier":"free","category":"general","priority":"low","department":"customer_success","key_points":["steps","instructions","support"]},
    {"id":"T005","subject":"Cancel Enterprise plan and full refund","body":"We need to cancel our Enterprise plan immediately and want a full refund for unused months. This is urgent.","customer_tier":"enterprise","category":"billing","priority":"critical","department":"billing_team","key_points":["apologize","process","refund","timeline"]},
    {"id":"T006","subject":"API returning 500 errors in production","body":"Our integration has been throwing 500 errors since 3pm UTC. This affects all 10,000 of our end users. Need immediate fix.","customer_tier":"enterprise","category":"technical","priority":"critical","department":"tech_support","key_points":["apologize","escalate","workaround","update"]},
    {"id":"T007","subject":"Wrong item shipped","body":"I ordered a blue keyboard (KB-2200-BLU) but received a black one. Order #ORD-5512. Please send the correct item.","customer_tier":"free","category":"shipping","priority":"medium","department":"logistics","key_points":["apologize","return","replacement"]},
    {"id":"T008","subject":"Refund for annual plan purchased 3 days ago","body":"I bought the annual plan 3 days ago but the features I needed aren't included. I'd like a full refund please.","customer_tier":"pro","category":"billing","priority":"medium","department":"billing_team","key_points":["apologize","policy","refund","alternatives"]},
    {"id":"T009","subject":"App crashes on Windows 11 startup","body":"Your desktop app crashes every time I open it on Windows 11. I've reinstalled 3 times already. Completely unusable.","customer_tier":"pro","category":"technical","priority":"high","department":"tech_support","key_points":["apologize","logs","workaround","timeline"]},
    {"id":"T010","subject":"Want to upgrade to Enterprise for 50 users","body":"We're a team of 50 and want to upgrade to Enterprise. Can someone from sales call me to discuss pricing?","customer_tier":"pro","category":"general","priority":"medium","department":"customer_success","key_points":["acknowledge","sales_contact","features","next_steps"]},
]

VALID_CATEGORIES = {"billing","technical","shipping","general"}
VALID_PRIORITIES = {"low","medium","high","critical"}
VALID_DEPARTMENTS = {"billing_team","tech_support","logistics","customer_success"}

KEY_POINT_KEYWORDS = {
    "apologize":["sorry","apologize","apologies","regret","understand"],
    "acknowledge":["thank you","received","noted","understand","hear"],
    "refund":["refund","reimburse","return the charge","credit"],
    "timeline":["within","business day","hours","48 hours","shortly","soon"],
    "troubleshoot":["try","steps","check","verify","attempt"],
    "steps":["step","first","then","next","follow"],
    "instructions":["navigate","click","go to","find","settings","menu"],
    "replacement":["replacement","replace","send a new","ship another","exchange"],
    "photo":["photo","image","picture","photograph","documentation"],
    "return":["return label","return shipping","send back","ship back"],
    "process":["process","procedure","cancellation","cancel"],
    "escalate":["escalate","engineering","senior","team","immediately"],
    "workaround":["workaround","meanwhile","temporarily","alternative"],
    "update":["update","status","inform","notify","follow up"],
    "alternatives":["alternative","other plan","option","suggest"],
    "policy":["policy","terms","30 day","14 day","satisfaction guarantee"],
    "logs":["log","error log","diagnostic","report"],
    "sales_contact":["sales","account manager","contact you","reach out"],
    "features":["feature","capability","include","offer"],
    "next_steps":["next step","schedule","call","meeting"],
    "support":["support","help","assist","team"],
}

def _parse_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {}

def _grade_classify(text, ticket):
    parsed = _parse_json(text)
    cat = parsed.get("category","").lower().strip()
    if not cat:
        for c in VALID_CATEGORIES:
            if c in text.lower():
                cat = c; break
    return 1.0 if cat == ticket["category"] else 0.0

def _grade_triage(text, ticket):
    parsed = _parse_json(text)
    cat = parsed.get("category","").lower().strip()
    pri = parsed.get("priority","").lower().strip()
    dept = parsed.get("department","").lower().strip()
    cat_s = 1.0 if cat == ticket["category"] else 0.0
    pri_s = 1.0 if pri == ticket["priority"] else 0.0
    if pri_s == 0.0 and pri in VALID_PRIORITIES:
        order = ["low","medium","high","critical"]
        ei = order.index(ticket["priority"])
        gi = order.index(pri) if pri in order else -1
        if abs(ei - gi) == 1:
            pri_s = 0.5
    dept_s = 1.0 if dept == ticket["department"] else 0.0
    return round(0.4*cat_s + 0.4*pri_s + 0.2*dept_s, 3)

def _grade_resolve(text, ticket):
    lower = text.lower()
    points = ticket["key_points"]
    if not points:
        return 1.0
    hit = sum(1 for p in points if any(kw in lower for kw in KEY_POINT_KEYWORDS.get(p,[p])))
    return round(hit / len(points), 3)


class TicketTriageEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True
    def __init__(self):
        self._task = os.getenv("TICKET_TRIAGE_TASK", "classify")
        self._tickets = TICKETS
        self._idx = 0
        self._state = State(episode_id="", step_count=0)

    def _instructions(self):
        if self._task == "classify":
            return 'Classify this ticket. Reply with JSON only: {"category": "<billing|technical|shipping|general>"}'
        elif self._task == "triage":
            return 'Triage this ticket. Reply with JSON only: {"category": "...", "priority": "<low|medium|high|critical>", "department": "<billing_team|tech_support|logistics|customer_success>"}'
        else:
            return "Write a helpful first response to this customer. Be empathetic, acknowledge the issue, and outline next steps."

    def _make_obs(self, ticket, last_reward, done):
        extra = f"\n[Category: {ticket['category']} | Priority: {ticket['priority']}]" if self._task == "resolve" else ""
        return TicketTriageObservation(
            ticket_id=ticket["id"],
            subject=ticket["subject"],
            body=ticket["body"] + extra,
            customer_tier=ticket["customer_tier"],
            task=self._task,
            instructions=self._instructions(),
            last_reward=last_reward,
            step=self._state.step_count,
            done=done,
        )

    def reset(self):
        self._idx = 0
        self._state = State(episode_id=str(uuid4()), step_count=0)
        return self._make_obs(self._tickets[0], 0.0, False)

    def step(self, action):
        ticket = self._tickets[self._idx]
        if self._task == "classify":
            reward = _grade_classify(action.text, ticket)
        elif self._task == "triage":
            reward = _grade_triage(action.text, ticket)
        else:
            reward = _grade_resolve(action.text, ticket)

        self._idx += 1
        self._state.step_count += 1
        done = self._idx >= len(self._tickets)

        if done:
            return TicketTriageObservation(
                ticket_id="DONE", subject="Episode complete",
                body=f"Processed {len(self._tickets)} tickets for task '{self._task}'.",
                customer_tier="", task=self._task, instructions="",
                last_reward=reward, step=self._state.step_count, done=True,
            )
        return self._make_obs(self._tickets[self._idx], reward, False)

    @property
    def state(self):
        return self._state
