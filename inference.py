"""
Baseline inference script for Ticket Triage OpenEnv environment.
Required env vars: HF_TOKEN (or API_KEY), API_BASE_URL, MODEL_NAME
Optional: IMAGE_NAME (if running via local Docker instead of HF Space)
"""
import asyncio
import os
import textwrap
from typing import List, Optional

from openai import OpenAI
from ticket_triage_env import TicketTriageAction, TicketTriageEnv

IMAGE_NAME   = os.getenv("IMAGE_NAME")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TASK_NAME    = os.getenv("TICKET_TRIAGE_TASK", "classify")
SPACE_URL    = os.getenv("SPACE_URL", "https://enodev88-ticket-triage-env.hf.space")
BENCHMARK    = "ticket_triage"
MAX_STEPS    = 12
TEMPERATURE  = 0.3
MAX_TOKENS   = 256
SUCCESS_SCORE_THRESHOLD = 0.5
MAX_TOTAL_REWARD = MAX_STEPS * 1.0

SYSTEM_PROMPTS = {
    "classify": "You are a customer support classifier. Reply with JSON only.\nFormat: {\"category\": \"<billing|technical|shipping|general>\"}",
    "triage":   "You are a support triage agent. Reply with JSON only.\nFormat: {\"category\": \"...\", \"priority\": \"<low|medium|high|critical>\", \"department\": \"<billing_team|tech_support|logistics|customer_success>\"}",
    "resolve":  "You are a customer support agent. Write a 3-5 sentence empathetic first response to the customer. Acknowledge the issue and outline next steps.",
}

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    action_clean = str(action).replace("\n", " ")[:120]
    print(f"[STEP] step={step} action={action_clean!r} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}", flush=True)

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def get_agent_response(client, obs):
    system = SYSTEM_PROMPTS.get(TASK_NAME, SYSTEM_PROMPTS["classify"])
    user = textwrap.dedent(f"""
        Ticket ID: {obs.ticket_id}
        Customer Tier: {obs.customer_tier}
        Subject: {obs.subject}
        Body: {obs.body}
        Task: {obs.instructions}
    """).strip()
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=TEMPERATURE, max_tokens=MAX_TOKENS, stream=False,
        )
        return (completion.choices[0].message.content or "").strip() or '{"category": "general"}'
    except Exception as exc:
        print(f"[DEBUG] Model call failed: {exc}", flush=True)
        return '{"category": "general"}'

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Connect via Docker image if IMAGE_NAME set, otherwise use live HF Space
    if IMAGE_NAME:
        env = await TicketTriageEnv.from_docker_image(IMAGE_NAME)
    else:
        env = TicketTriageEnv(base_url=SPACE_URL)
        await env.connect()

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        obs = result.observation
        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break
            response_text = get_agent_response(client, obs)
            result = await env.step(TicketTriageAction(text=response_text))
            obs = result.observation
            reward = result.reward or 0.0
            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=response_text, reward=reward, done=result.done, error=None)
            if result.done:
                break
        score = min(max(sum(rewards) / MAX_TOTAL_REWARD, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD
    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)
    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())
