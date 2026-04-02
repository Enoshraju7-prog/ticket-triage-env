from openenv.core.env_server import create_app

try:
    from ticket_triage_env.models import TicketTriageAction, TicketTriageObservation
    from server.environment import TicketTriageEnvironment
except ImportError:
    from models import TicketTriageAction, TicketTriageObservation
    from environment import TicketTriageEnvironment

app = create_app(
    TicketTriageEnvironment,
    TicketTriageAction,
    TicketTriageObservation,
    env_name="ticket_triage",
    max_concurrent_envs=64,
)


def main():
    import uvicorn
    import os
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
