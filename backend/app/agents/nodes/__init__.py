"""Pipeline nodes for the field assistant retrieval graph.

Each node is a function: (FieldAssistantState) -> dict of state updates.
Nodes are independently testable and wired together in field_assistant.py.
"""

from app.agents.nodes.classify_extract import classify_and_extract
from app.agents.nodes.route import route_intent
from app.agents.nodes.needs_search import needs_search_node
from app.agents.nodes.craft_query import craft_search_query
from app.agents.nodes.execute_search import execute_searches, execute_searches_sync
from app.agents.nodes.rerank import rerank_results
from app.agents.nodes.expand_route import expand_route_node
from app.agents.nodes.generate_answer import generate_answer
from app.agents.nodes.log_observation import log_observation_node

__all__ = [
    "classify_and_extract",
    "route_intent",
    "needs_search_node",
    "expand_route_node",
    "craft_search_query",
    "execute_searches",
    "execute_searches_sync",
    "rerank_results",
    "generate_answer",
    "log_observation_node",
]
