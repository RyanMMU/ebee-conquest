class NpcPersonality:
    def __init__(
        self,
        name="default",
        aggression=1.0, # HIGHER = MORE AGGRESSIVE, LOWER = MORE PASSIVE
        caution=1.0, # HIGHER = MORE CAUTIOUS/DEFENSIVE, LOWER = MORE RISK-TAKING/AGGRESSIVE
        recruitmentpriority=1.0, # HIGHER = PRIORITIZE RECRUITING MORE TROOPS, LOWER = PRIORITIZE OTHER ASPECTS OF ECONOMY OR MILITARY
        defensepriority=1.0, # HIGHER = PRIORITIZE DEFENSIVE MOVEMENT AND GARRISON MANAGEMENT, LOWER = PRIORITIZE OFFENSIVE MOVEMENT AND EXPANSION
    ):
        self.name = str(name or "default")
        self.aggression = self._safeweight(aggression)
        self.caution = self._safeweight(caution)
        self.recruitmentpriority = self._safeweight(recruitmentpriority)
        self.defensepriority = self._safeweight(defensepriority)

    @staticmethod
    def _safeweight(value):
        try:
            return max(0.0, float(value)) # no negativ
        except (TypeError, ValueError):
            return 1.0

    @classmethod
    def default(cls):
        return cls()

    def copy(self):
        return NpcPersonality(
            name=self.name,
            aggression=self.aggression,
            caution=self.caution,
            recruitmentpriority=self.recruitmentpriority,
            defensepriority=self.defensepriority,
        )


# TODO: add named country personality presets here, such as aggressive or economic.
# ALSO TODO: consider adding logic for dynamically adjusting personality traits based on current war status or other factors, such as becoming more aggressive when winning a war or more cautious when losing, or adjusting recruitment priorities based on current troop strength or economic status.
