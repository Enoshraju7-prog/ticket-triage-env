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
