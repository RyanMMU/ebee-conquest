class NpcPersonality:
    def __init__(
        self,
        name="default",
        aggression=1.0, # HIGHER = MORE AGGRESSIVE, LOWER = MORE PASSIVE
        caution=1.0, # HIGHER = MORE CAUTIOUS/DEFENSIVE, LOWER = MORE RISK-TAKING/AGGRESSIVE
        recruitmentpriority=1.0, # HIGHER = PRIORITIZE RECRUITING MORE TROOPS, LOWER = PRIORITIZE OTHER ASPECTS OF ECONOMY OR MILITARY
        defensepriority=1.0, # HIGHER = PRIORITIZE DEFENSIVE MOVEMENT AND GARRISON MANAGEMENT, LOWER = PRIORITIZE OFFENSIVE MOVEMENT AND EXPANSION
        diplomacy=1.0,
        pragmatism=1.0,
        pride=1.0,
        territoriality=1.0,
        negotiationstyle="measured",
    ):
        self.name = str(name or "default")
        self.aggression = self._safeweight(aggression)
        self.caution = self._safeweight(caution)
        self.recruitmentpriority = self._safeweight(recruitmentpriority)
        self.defensepriority = self._safeweight(defensepriority)
        self.diplomacy = self._safeweight(diplomacy)
        self.pragmatism = self._safeweight(pragmatism)
        self.pride = self._safeweight(pride)
        self.territoriality = self._safeweight(territoriality)
        self.negotiationstyle = str(negotiationstyle or "measured")

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
            diplomacy=self.diplomacy,
            pragmatism=self.pragmatism,
            pride=self.pride,
            territoriality=self.territoriality,
            negotiationstyle=self.negotiationstyle,
        )


COUNTRY_PERSONALITY_PRESETS = {
    "Malaysia": NpcPersonality(
        "coalition_builder", 0.85, 1.1, 0.95, 1.0,
        diplomacy=1.25, pragmatism=1.2, pride=0.9, territoriality=0.95,
        negotiationstyle="polite, practical, and coalition-minded",
    ),
    "Singapore": NpcPersonality(
        "strategic_realist", 0.75, 1.3, 0.9, 1.25,
        diplomacy=1.2, pragmatism=1.4, pride=1.05, territoriality=1.25,
        negotiationstyle="precise, legalistic, and security-focused",
    ),
    "Indonesia": NpcPersonality(
        "archipelago_guardian", 1.05, 1.0, 1.05, 1.05,
        diplomacy=1.0, pragmatism=1.05, pride=1.2, territoriality=1.25,
        negotiationstyle="confident, patient, and protective of sovereignty",
    ),
    "Thailand": NpcPersonality(
        "balancer", 1.0, 1.15, 1.0, 1.1,
        diplomacy=1.2, pragmatism=1.15, pride=1.1, territoriality=1.05,
        negotiationstyle="courteous, indirect, and attentive to balance",
    ),
    "Philippines": NpcPersonality(
        "alliance_seeker", 1.05, 0.95, 1.05, 0.95,
        diplomacy=1.05, pragmatism=1.0, pride=1.05, territoriality=1.15,
        negotiationstyle="direct, energetic, and alliance-conscious",
    ),
    "Vietnam": NpcPersonality(
        "resolute_defender", 1.15, 1.2, 1.1, 1.25,
        diplomacy=0.9, pragmatism=1.1, pride=1.35, territoriality=1.4,
        negotiationstyle="disciplined, terse, and fiercely territorial",
    ),
    "Myanmar": NpcPersonality(
        "security_hardliner", 1.2, 1.05, 1.15, 1.3,
        diplomacy=0.75, pragmatism=0.9, pride=1.25, territoriality=1.3,
        negotiationstyle="guarded, formal, and security-driven",
    ),
    "Cambodia": NpcPersonality(
        "transactional_survivor", 0.9, 1.1, 0.9, 1.0,
        diplomacy=1.1, pragmatism=1.35, pride=0.9, territoriality=1.0,
        negotiationstyle="transactional, flexible, and face-saving",
    ),
    "Laos": NpcPersonality(
        "cautious_mediator", 0.7, 1.3, 0.85, 1.1,
        diplomacy=1.25, pragmatism=1.3, pride=0.85, territoriality=1.05,
        negotiationstyle="quiet, cautious, and compromise-oriented",
    ),
    "Brunei": NpcPersonality(
        "status_quo_guardian", 0.65, 1.35, 0.85, 1.2,
        diplomacy=1.15, pragmatism=1.2, pride=1.1, territoriality=1.25,
        negotiationstyle="formal, reserved, and status-quo oriented",
    ),
    "Timor_Leste": NpcPersonality(
        "sovereignty_advocate", 0.8, 1.15, 0.9, 1.05,
        diplomacy=1.2, pragmatism=1.15, pride=1.2, territoriality=1.35,
        negotiationstyle="earnest, principled, and sovereignty-focused",
    ),
}


def getcountrypersonalitypreset(countryname):
    preset = COUNTRY_PERSONALITY_PRESETS.get(str(countryname))
    return preset.copy() if preset is not None else NpcPersonality.default()
