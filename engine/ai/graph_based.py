import json
import re


class GraphBasedProvider:
    """Offline response policy for peace talks.

    The negotiation engine supplies a posture score. This provider follows a
    small state graph so the offline mode remains predictable and testable.
    """

    name = "graph"

    def configure(self, **config):
        if config:
            raise ValueError("Graph-based mode does not accept configuration.")

    def ask(self, prompt):
        scorematch = re.search(r"POSTURE_SCORE:\s*(-?\d+(?:\.\d+)?)", prompt)
        score = float(scorematch.group(1)) if scorematch else 50.0
        finalrequest = "FINAL_PROPOSAL: yes" in prompt

        if score >= 65:
            decision = "ACCEPT"
            message = "These terms are difficult, but they are preferable to further destruction."
        elif score >= 42:
            decision = "COUNTER"
            message = "We will continue talking, but the territorial burden must be reduced."
        else:
            decision = "REJECT"
            message = "Those terms would leave our nation without a defensible future."

        if not finalrequest:
            decision = "CONTINUE"
            if score >= 65:
                message = "Your position is understood. A restrained settlement may be possible."
            elif score >= 42:
                message = "There is room for compromise if your demands remain proportionate."
            else:
                message = "Your approach is hardening our delegation's resistance."

        return json.dumps({"decision": decision, "message": message})
