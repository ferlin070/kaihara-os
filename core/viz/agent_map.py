"""
Agent Map - visualize agents working in real-time.
Inspired by ai-town: agents move between stations, show speech bubbles.
Kaihara version: "Control Room" layout instead of a town.
"""

import time
import json
import math
from datetime import datetime
from typing import Any


class AgentMap:
    """Track agent positions, movements, and interactions for visualization."""

    # Town buildings (x, y = center of building on 800x600 canvas)
    STATIONS = {
        "command_center": {"x": 400, "y": 280, "w": 100, "h": 80,
                            "label": "Command Center", "type": "hq",
                            "color": "#3b82f6"},
        "coding_desk": {"x": 130, "y": 130, "w": 90, "h": 70,
                         "label": "Coding Lab", "type": "lab",
                         "color": "#10b981"},
        "security_terminal": {"x": 670, "y": 130, "w": 90, "h": 70,
                               "label": "Security HQ", "type": "fort",
                               "color": "#ef4444"},
        "marketing_hub": {"x": 130, "y": 470, "w": 90, "h": 70,
                           "label": "Market", "type": "shop",
                           "color": "#f59e0b"},
        "deploy_station": {"x": 670, "y": 470, "w": 90, "h": 70,
                            "label": "Deploy Bay", "type": "garage",
                            "color": "#8b5cf6"},
        "research_desk": {"x": 400, "y": 80, "w": 90, "h": 60,
                           "label": "Library", "type": "library",
                           "color": "#06b6d4"},
        "storage_vault": {"x": 400, "y": 520, "w": 90, "h": 60,
                           "label": "Vault", "type": "warehouse",
                           "color": "#6b7280"},
        "meta_observatory": {"x": 730, "y": 300, "w": 70, "h": 70,
                              "label": "Observatory", "type": "tower",
                              "color": "#ec4899"},
    }

    # Agent home stations (where they start)
    AGENT_HOMES = {
        "kaihara": "command_center",
        "coding": "coding_desk",
        "marketing": "marketing_hub",
        "security": "security_terminal",
        "deploy": "deploy_station",
        "research": "research_desk",
        "meta": "meta_observatory",
    }

    def __init__(self):
        self.agents: dict[str, dict] = {}
        self.events: list[dict] = []
        self.interactions: list[dict] = []
        self._init_agents()

    def _init_agents(self):
        """Initialize all agents at their home stations."""
        import random
        for agent, station in self.AGENT_HOMES.items():
            home = self.STATIONS[station]
            self.agents[agent] = {
                "name": agent,
                "x": home["x"],
                "y": home["y"],
                "target_x": home["x"],
                "target_y": home["y"],
                "station": station,
                "status": "idle",
                "task": "",
                "speech": "",
                "speech_expires": 0,
                "color": home["color"],
                "moving": False,
                "progress": 0,
                "wander_timer": random.uniform(3, 10),
                "wander_count": 0,
                "wander_limit": random.randint(2, 5),
                "anim_state": "idle",
                "anim_frame": 0,
                "anim_timer": 0,
                "direction": "down",
                "last_update": time.time(),
            }

    def move_agent(self, agent: str, station: str,
                    task: str = "", progress: int = 0):
        """Move an agent to a station."""
        if agent not in self.agents:
            return
        if station not in self.STATIONS:
            return
        dest = self.STATIONS[station]
        self.agents[agent]["target_x"] = dest["x"]
        self.agents[agent]["target_y"] = dest["y"]
        self.agents[agent]["station"] = station
        self.agents[agent]["status"] = "moving"
        self.agents[agent]["task"] = task
        self.agents[agent]["progress"] = progress
        self.agents[agent]["moving"] = True
        self._add_event("move", agent,
                         {"from": self.agents[agent].get("station"),
                          "to": station, "task": task})

    def set_agent_status(self, agent: str, status: str,
                          task: str = "", progress: int = 0):
        """Update agent status without moving."""
        if agent not in self.agents:
            return
        self.agents[agent]["status"] = status
        if task:
            self.agents[agent]["task"] = task
        if progress:
            self.agents[agent]["progress"] = progress
        self.agents[agent]["moving"] = (status == "moving")

    def set_speech(self, agent: str, text: str,
                    duration: int = 10):
        """Show a speech bubble for an agent."""
        if agent not in self.agents:
            return
        self.agents[agent]["speech"] = text
        self.agents[agent]["speech_expires"] = time.time() + duration
        self._add_event("speech", agent, {"text": text})

    def add_interaction(self, agent_a: str, agent_b: str,
                         interaction_type: str, details: str = ""):
        """Record an interaction between two agents (A2A)."""
        interaction = {
            "agent_a": agent_a,
            "agent_b": agent_b,
            "type": interaction_type,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.interactions.append(interaction)
        if len(self.interactions) > 100:
            self.interactions = self.interactions[-100:]
        self._add_event("interaction", agent_a,
                         {"with": agent_b, "type": interaction_type})

    def _add_event(self, event_type: str, agent: str, data: dict):
        """Add a map event."""
        self.events.append({
            "type": event_type,
            "agent": agent,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.events) > 200:
            self.events = self.events[-200:]

    def tick(self):
        """Update agent positions + idle wander + animation states."""
        import random
        now = time.time()
        dt = 0.1  # approx 100ms per tick

        for agent in self.agents.values():
            elapsed = now - agent.get("last_update", now)
            agent["last_update"] = now

            # Movement towards target
            if agent["moving"]:
                dx = agent["target_x"] - agent["x"]
                dy = agent["target_y"] - agent["y"]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 5:
                    agent["x"] = agent["target_x"]
                    agent["y"] = agent["target_y"]
                    agent["moving"] = False
                    agent["status"] = "working"
                    agent["anim_state"] = "type"
                    agent["anim_frame"] = 0
                else:
                    speed = 30
                    agent["x"] += (dx / dist) * speed
                    agent["y"] += (dy / dist) * speed
                    agent["anim_state"] = "walk"
                    # Determine direction
                    if abs(dx) > abs(dy):
                        agent["direction"] = "right" if dx > 0 else "left"
                    else:
                        agent["direction"] = "down" if dy > 0 else "up"

            # Idle wander (pixel-agents style)
            elif agent["status"] == "idle" and not agent["moving"]:
                agent["wander_timer"] -= elapsed
                if agent["wander_timer"] <= 0:
                    if agent["wander_count"] >= agent["wander_limit"]:
                        # Return to home station
                        home = self.STATIONS.get(agent["station"], {})
                        if home:
                            agent["target_x"] = home["x"]
                            agent["target_y"] = home["y"]
                            agent["moving"] = True
                            agent["anim_state"] = "walk"
                        agent["wander_count"] = 0
                        agent["wander_limit"] = random.randint(2, 5)
                        agent["wander_timer"] = random.uniform(5, 15)
                    else:
                        # Wander to random nearby position
                        offset_x = random.randint(-60, 60)
                        offset_y = random.randint(-40, 40)
                        agent["target_x"] = agent["x"] + offset_x
                        agent["target_y"] = agent["y"] + offset_y
                        agent["moving"] = True
                        agent["anim_state"] = "walk"
                        agent["wander_count"] += 1
                        agent["wander_timer"] = random.uniform(2, 6)
                else:
                    # Standing idle — play idle animation
                    agent["anim_state"] = "idle"

            elif agent["status"] == "working" and not agent["moving"]:
                agent["anim_state"] = "type"

            # Animation frame update
            agent["anim_timer"] += elapsed
            if agent["anim_timer"] >= 0.18:
                agent["anim_timer"] = 0
                state = agent["anim_state"]
                if state == "walk":
                    agent["anim_frame"] = (agent["anim_frame"] + 1) % 3
                elif state == "type":
                    agent["anim_frame"] = (agent["anim_frame"] + 1) % 2
                elif state == "read":
                    agent["anim_frame"] = (agent["anim_frame"] + 1) % 2
                elif state == "idle":
                    agent["anim_frame"] = 0

            # Clear expired speech
            if agent["speech"] and now > agent["speech_expires"]:
                agent["speech"] = ""

    def get_state(self) -> dict:
        """Get full map state for rendering."""
        # Tick to update positions
        self.tick()
        return {
            "agents": {name: {
                "name": a["name"],
                "x": round(a["x"]),
                "y": round(a["y"]),
                "target_x": round(a["target_x"]),
                "target_y": round(a["target_y"]),
                "station": a["station"],
                "status": a["status"],
                "task": a["task"],
                "speech": a["speech"],
                "color": a["color"],
                "moving": a["moving"],
                "progress": a["progress"],
                "anim_state": a.get("anim_state", "idle"),
                "anim_frame": a.get("anim_frame", 0),
                "direction": a.get("direction", "down"),
            } for name, a in self.agents.items()},
            "stations": self.STATIONS,
            "events": self.events[-20:],
            "interactions": self.interactions[-10:],
        }

    def reset(self):
        """Reset all agents to home stations."""
        self.agents.clear()
        self._init_agents()
        self.events.clear()
        self.interactions.clear()

    def status(self) -> dict:
        return {
            "agents": len(self.agents),
            "stations": len(self.STATIONS),
            "events": len(self.events),
            "interactions": len(self.interactions),
        }
