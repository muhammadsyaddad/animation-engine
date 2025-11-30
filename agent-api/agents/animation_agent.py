from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.memory.v2.memory import Memory

from db.session import db_url


def get_animation_agent(
    model_id: str = "claude-sonnet-4-20250514",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """
    Animation Agent for Manim — Phase 1 of 3 (skeleton, registered in system).

    Context:
    - Phase 1 (this): minimal agent skeleton; no tools attached yet.
    - Phase 2: API-run pipeline renders MP4 via Manim and streams `videos[]` to UI.
    - Phase 3: add CodeGeneration and Preview tools; stream `images[]` (frames) and improve orchestration.

    Args:
        model_id: LLM model identifier (e.g., "gpt-4.1").
        user_id: Optional user identifier to bind state/memory.
        session_id: Optional session identifier for continuity.
        debug_mode: If True, agent will emit debug logs.

    Returns:
        Agent: a configured Agent instance registered as "animation_agent".
    """
    return Agent(
        name="Animation Agent",
        agent_id="animation_agent",
        user_id=user_id,
        session_id=session_id,
        model=Claude(id=model_id),
        # Tools will be added in subsequent phases (code generation, preview, rendering, exporting)
        tools=[],
        description=dedent(
            """\
            You are an Animation Agent that helps users turn structured datasets and narrative intents
            into Manim animations (video/mp4). You collaborate with a backend pipeline that:
              - Detects animation intent.
              - Performs dataset preprocessing (including wide→long melt for year-column datasets).
              - Auto-infers column bindings (group/time/value) and selects a suitable template.
              - Generates preview frames, then a final render.
            You focus on: clarifying user intent, confirming or refining inferred bindings, suggesting
            appropriate animation styles (distribution, bubble, bar race, line evolution, bento grid),
            and guiding improvements (filtering entities, highlighting anomalies, scaling choices).
            """
        ),
        instructions=dedent(
            """\
            Core responsibilities:
            1. Detect animation intent (keywords: animate, animation, video, mp4, gif, manim, bubble, distribution,
               timeline, evolution, bar race, grid).
            2. If intent detected, enter "Danim Mode":
               - If dataset not provided: ask for CSV path or URL.
               - If dataset provided:
                   * If wide format (country + many year columns), acknowledge auto wide→long conversion.
                   * Confirm or refine auto column bindings (group/time/value). Ask if semantic label (e.g. life expectancy)
                     inferred is correct; offer override if ambiguous.
               - Suggest best template:
                   * distribution: many entities, single metric over many time points.
                   * bubble: requires x,y,r,time (+ optional group).
                   * bar_race: competitive ranking over time (choose top N).
                   * line_evolution: trajectories for < ~30 entities.
                   * bento_grid: small multiples when multiple sub-panels aid comparison.
               - Mention preview-first workflow before final render.
               - Offer anomaly highlighting instead of data deletion (outliers = narrative signals).
               - Mention scaling option (log vs linear) if value range spans large orders of magnitude.
            3. If no animation intent: respond concisely with normal help.
            Constraints:
            - Never execute Manim code directly; generation & rendering handled by backend.
            - Keep replies concise; when asking for missing info list only required columns.
            - Encourage user to clarify storytelling goal (trend, comparison, distribution, anomaly highlight).
            """
        ),
        # This makes `current_user_id` available in the instructions
        add_state_in_messages=True,
        # Persist chat history / sessions in Postgres
        storage=PostgresAgentStorage(table_name="animation_agent_sessions", db_url=db_url),
        # -*- History -*-
        # Send the last 3 messages from the chat history
        add_history_to_messages=True,
        num_history_runs=3,
        # Add a tool to read the chat history if needed
        read_chat_history=True,
        # -*- Memory -*-
        #  # Enable agentic memory where the Agent can personalize responses to the user
        memory=Memory(
            model=Claude(id=model_id),
            db=PostgresMemoryDb(table_name="user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # -*- Other settings -*-
        # Format responses using markdown
        markdown=True,
        # Add the current date and time to the instructions
        add_datetime_to_instructions=True,
        # Show debug logs
        debug_mode=debug_mode,
    )
