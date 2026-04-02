from pydantic import Field
from openenv.core.env_server.interfaces import Action, Observation


class TicketTriageAction(Action):
    text: str = Field(default="", description="Agent response (JSON or free-text)")


class TicketTriageObservation(Observation):
    # Note: done, reward, metadata are already on base Observation
    ticket_id: str = Field(default="")
    subject: str = Field(default="")
    body: str = Field(default="")
    customer_tier: str = Field(default="free")
    task: str = Field(default="classify")
    instructions: str = Field(default="")
    last_reward: float = Field(default=0.0)
    step: int = Field(default=0)
