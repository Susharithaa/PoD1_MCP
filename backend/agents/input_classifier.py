"""InputClassifier — determines DOC vs CHAT mode."""

import os
from agents.base import BaseAgent
from models.agent_session import AgentSession


class InputClassifier(BaseAgent):
    name = "input_classifier"

    async def run(self, session: AgentSession) -> AgentSession:
        if session.file_path and os.path.exists(session.file_path):
            session.mode = "DOC"
            # raw_input is set to the file path — ParsingAgent handles extraction
            session.raw_input = session.file_path
        else:
            session.mode = "CHAT"
            # raw_input already set by caller
        return session
