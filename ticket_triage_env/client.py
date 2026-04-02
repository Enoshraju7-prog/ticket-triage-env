from typing import Dict, Any

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import TicketTriageAction, TicketTriageObservation
except ImportError:
    from models import TicketTriageAction, TicketTriageObservation


class TicketTriageEnv(EnvClient[TicketTriageAction, TicketTriageObservation, State]):

    def _step_payload(self, action: TicketTriageAction) -> Dict[str, Any]:
        return {"text": action.text}

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[TicketTriageObservation]:
        obs_data = payload.get("observation", {})
        # Pydantic ignores unknown fields gracefully via model_validate
        obs = TicketTriageObservation.model_validate(obs_data)
        return StepResult(
            observation=obs,
            reward=float(payload.get("reward", 0.0)),
            done=bool(payload.get("done", False)),
            info=payload.get("info", {}),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        return State(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
        )
