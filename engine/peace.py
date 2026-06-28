import json
import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


ALLOWED_DEMANDS = {
    "CEASEFIRE",
    "STATE TRANSFER",
    "PUPPET STATE",
    "MILITARY ACCESS",
    "REGIME CHANGE",
}


class NegotiationDecision(str, Enum):
    continue_talks = "CONTINUE"
    accept = "ACCEPT"
    counter = "COUNTER"
    reject = "REJECT"


class NegotiationAIResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: NegotiationDecision
    message: str = Field(min_length=1, max_length=500)
    concession_delta: int = Field(default=0, ge=-8, le=8)
    suggested_demands: list[str] = Field(default_factory=list, max_length=5)
    suggested_territory_state_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("message")
    @classmethod
    def cleanmessage(cls, value):
        return " ".join(value.split())

    @field_validator("suggested_demands")
    @classmethod
    def validatesuggesteddemands(cls, values):
        cleaned = []
        for value in values:
            demand = str(value).strip().upper()
            if demand not in ALLOWED_DEMANDS:
                raise ValueError(f"Unsupported suggested peace demand: {demand}")
            if demand not in cleaned:
                cleaned.append(demand)
        return cleaned

    @field_validator("suggested_territory_state_ids")
    @classmethod
    def validatesuggestedterritories(cls, values):
        return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


class PeaceProposal(BaseModel):
    """Only this validated object may be applied to the campaign state."""

    model_config = ConfigDict(extra="forbid")

    proposer: str = Field(min_length=1, max_length=80)
    recipient: str = Field(min_length=1, max_length=80)
    demands: list[str] = Field(default_factory=list, max_length=5)
    territory_state_ids: list[str] = Field(default_factory=list, max_length=100)
    final: Literal[True] = True

    @field_validator("demands")
    @classmethod
    def validatedemands(cls, values):
        cleaned = []
        for value in values:
            demand = str(value).strip().upper()
            if demand not in ALLOWED_DEMANDS:
                raise ValueError(f"Unsupported peace demand: {demand}")
            if demand not in cleaned:
                cleaned.append(demand)
        if not cleaned:
            raise ValueError("A peace proposal needs at least one demand.")
        return cleaned

    @field_validator("territory_state_ids")
    @classmethod
    def uniqueterritories(cls, values):
        cleaned = []
        for value in values:
            stateid = str(value).strip()
            if stateid and stateid not in cleaned:
                cleaned.append(stateid)
        return cleaned


def parse_ai_response(rawresponse, posture_score, finalproposal):
    """Validate model output and constrain it to the engine's posture policy."""
    try:
        text = str(rawresponse or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
        jsonmatch = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if jsonmatch:
            text = jsonmatch.group(0)
        responsedata = json.loads(text)
        if isinstance(responsedata, dict) and isinstance(responsedata.get("message"), str):
            message = " ".join(responsedata["message"].split())
            if len(message) > 500:
                message = message[:497].rstrip() + "..."
            responsedata["message"] = message
        response = NegotiationAIResponse.model_validate(responsedata)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError):
        return fallback_ai_response(posture_score, finalproposal)

    decision = response.decision
    if not finalproposal:
        if decision != NegotiationDecision.counter:
            decision = NegotiationDecision.continue_talks
    elif posture_score < 35 and decision == NegotiationDecision.accept:
        return fallback_ai_response(posture_score, True)
    elif posture_score >= 72 and decision == NegotiationDecision.reject:
        decision = NegotiationDecision.counter
    return response.model_copy(update={"decision": decision})


def fallback_ai_response(posture_score, finalproposal):
    if not finalproposal:
        if posture_score >= 65:
            message = "A restrained settlement may be possible. State your final terms."
        elif posture_score >= 42:
            message = "There is room for compromise, but your demands must remain proportionate."
        else:
            message = "Your current approach is hardening our delegation's resistance."
        return NegotiationAIResponse(decision="CONTINUE", message=message)
    if posture_score >= 65:
        return NegotiationAIResponse(
            decision="ACCEPT",
            message="We accept these terms to prevent further destruction.",
        )
    if posture_score >= 42:
        return NegotiationAIResponse(
            decision="COUNTER",
            message="Reduce the territorial burden and we may accept.",
        )
    return NegotiationAIResponse(
        decision="REJECT",
        message="These terms would leave our country without a viable future.",
    )


class PeaceNegotiation:
    def __init__(
        self,
        ai_manager,
        victor,
        defeated,
        player_name,
        personality,
        victor_strength,
        defeated_strength,
        available_state_ids,
        occupation_ratio=0.0,
    ):
        self.ai_manager = ai_manager
        self.victor = str(victor)
        self.defeated = str(defeated)
        self.player_name = str(player_name or "Player")
        self.personality = personality
        self.victor_strength = max(1.0, float(victor_strength))
        self.defeated_strength = max(1.0, float(defeated_strength))
        self.available_state_ids = set(str(value) for value in available_state_ids)
        self.occupation_ratio = max(0.0, min(1.0, float(occupation_ratio)))
        self.chat_history = []
        self.conversation_score = 0
        self.provider_available = True
        self.last_provider_error = None
        self.counter_requested = False

    def interpret_player_message(self, message, demands, territory_state_ids):
        lowered = " ".join(str(message).lower().replace("_", " ").split())
        updateddemands = set(demands)
        updatedterritories = set(territory_state_ids) & self.available_state_ids

        allterritoryphrases = (
            "all your territory",
            "all territory",
            "every territory",
            "everything you own",
            "entire country",
        )
        if any(phrase in lowered for phrase in allterritoryphrases):
            updateddemands.add("STATE TRANSFER")
            updatedterritories = set(self.available_state_ids)
        else:
            for stateid in self.available_state_ids:
                displayname = stateid.lower().replace("_", " ")
                if displayname and displayname in lowered:
                    updateddemands.add("STATE TRANSFER")
                    updatedterritories.add(stateid)

        demandphrases = {
            "PUPPET STATE": ("puppet", "subject state"),
            "MILITARY ACCESS": ("military access", "access rights"),
            "REGIME CHANGE": ("regime change", "change your government"),
        }
        for demand, phrases in demandphrases.items():
            if any(phrase in lowered for phrase in phrases):
                updateddemands.add(demand)

        return updateddemands, updatedterritories

    def record_player_message(self, message):
        message = " ".join(str(message).split())[:500]
        lowered = message.lower()
        positivewords = (
            "please", "peace", "fair", "rebuild", "security", "respect",
            "compromise", "guarantee", "cooperate", "stability",
        )
        negativewords = (
            "idiot", "stupid", "destroy", "annihilate", "humiliate",
            "obey", "or else", "no choice", "weakling", "everything",
            "all your territory", "all territory", "take it all",
        )
        delta = sum(2 for word in positivewords if word in lowered)
        delta -= sum(4 for word in negativewords if word in lowered)
        if len(message) >= 30:
            delta += 1
        counterphrases = (
            "what would you offer",
            "what would you like to offer",
            "what will you offer",
            "your proposal",
            "submit your proposal",
            "your counteroffer",
            "make an offer",
            "make a proposal",
            "what do you propose",
        )
        self.counter_requested = any(phrase in lowered for phrase in counterphrases)
        self.conversation_score = max(-24, min(24, self.conversation_score + delta))
        self.chat_history.append(("PLAYER", message))
        return message

    def posture_score(self, demands, territory_state_ids):
        if self.occupation_ratio >= 0.999:
            return 100.0
        demands = set(demands)
        strengthratio = self.victor_strength / self.defeated_strength
        score = 49.0 + max(-12.0, min(28.0, (strengthratio - 1.0) * 19.0))
        score += self.conversation_score
        score += (getattr(self.personality, "pragmatism", 1.0) - 1.0) * 12.0
        score += (getattr(self.personality, "diplomacy", 1.0) - 1.0) * 7.0
        score -= (getattr(self.personality, "pride", 1.0) - 1.0) * 10.0
        score += self.occupation_ratio * 18.0

        territorycount = len(set(territory_state_ids))
        availablecount = max(1, len(self.available_state_ids))
        territorialburden = territorycount / availablecount
        score -= territorialburden * 38.0 * getattr(self.personality, "territoriality", 1.0)
        if "PUPPET STATE" in demands:
            score -= 24.0
        if "REGIME CHANGE" in demands:
            score -= 13.0
        if "MILITARY ACCESS" in demands:
            score -= 5.0
        if demands == {"CEASEFIRE"}:
            score += 15.0
        return max(0.0, min(100.0, score))

    def build_prompt(self, demands, territory_state_ids, finalproposal):
        score = self.posture_score(demands, territory_state_ids)
        historylines = [
            f"{speaker}: {message}" for speaker, message in self.chat_history[-8:]
        ]
        return "\n".join([
            "You are roleplaying a defeated non-player nation in a strategy-game peace conference.",
            f"Nation: {self.defeated}",
            f"Victor: {self.victor}, represented by {self.player_name}",
            f"Personality: {getattr(self.personality, 'negotiationstyle', 'measured')}",
            f"Strength ratio (victor/defeated): {self.victor_strength / self.defeated_strength:.2f}",
            f"Occupation of defeated nation: {self.occupation_ratio * 100.0:.1f}%",
            f"Demands: {', '.join(sorted(demands)) or 'none'}",
            f"Requested state IDs: {', '.join(sorted(territory_state_ids)) or 'none'}",
            f"Allowed state IDs for a counteroffer: {', '.join(sorted(self.available_state_ids)) or 'none'}",
            f"POSTURE_SCORE: {score:.1f}",
            f"FINAL_PROPOSAL: {'yes' if finalproposal else 'no'}",
            "Recent negotiation:",
            *(historylines or ["No prior messages."]),
            "Address the player's latest message directly. Do not repeat an earlier reply.",
            "Return ONLY JSON with keys decision, message, concession_delta, suggested_demands, "
            "suggested_territory_state_ids.",
            "For chat, use COUNTER when the player asks what you offer; otherwise use CONTINUE. "
            "For a final proposal use ACCEPT, COUNTER, or REJECT.",
            "message must stay in character and be no more than two short sentences or 300 characters.",
            "For COUNTER, suggest less costly terms using only the allowed demand names and state IDs.",
            "For other decisions, return empty suggestion lists. Never invent a territory ID.",
            "concession_delta must be an integer from -8 to 8.",
        ])

    def _validated_counteroffer(self, response, demands, territory_state_ids):
        if response.decision != NegotiationDecision.counter:
            return response

        currentdemands = set(demands)
        currentterritories = sorted(set(territory_state_ids) & self.available_state_ids)
        suggesteddemands = set(response.suggested_demands)
        suggestedterritories = sorted(
            set(response.suggested_territory_state_ids) & self.available_state_ids
        )

        if not suggesteddemands:
            suggesteddemands = set(currentdemands)
            if "PUPPET STATE" in suggesteddemands:
                suggesteddemands.remove("PUPPET STATE")
            elif "REGIME CHANGE" in suggesteddemands:
                suggesteddemands.remove("REGIME CHANGE")
            elif currentterritories:
                keepcount = max(0, len(currentterritories) // 2)
                suggestedterritories = currentterritories[:keepcount]
            elif "MILITARY ACCESS" in suggesteddemands:
                suggesteddemands.remove("MILITARY ACCESS")

        suggesteddemands.add("CEASEFIRE")
        if suggestedterritories:
            suggesteddemands.add("STATE TRANSFER")
        elif "STATE TRANSFER" in suggesteddemands:
            suggesteddemands.remove("STATE TRANSFER")

        return response.model_copy(update={
            "suggested_demands": sorted(suggesteddemands),
            "suggested_territory_state_ids": suggestedterritories,
        })

    def ask(self, demands, territory_state_ids, finalproposal=False):
        prompt = self.build_prompt(demands, territory_state_ids, finalproposal)
        score = self.posture_score(demands, territory_state_ids)
        if finalproposal and self.occupation_ratio >= 0.999:
            response = NegotiationAIResponse(
                decision="ACCEPT",
                message="With our territory fully occupied, we have no remaining leverage. We accept.",
            )
        elif not self.provider_available:
            response = fallback_ai_response(score, finalproposal)
        else:
            try:
                rawresponse = self.ai_manager.ask(prompt)
            except Exception as error:
                self.provider_available = False
                self.last_provider_error = str(error)
                response = fallback_ai_response(score, finalproposal)
            else:
                self.last_provider_error = None
                response = parse_ai_response(rawresponse, score, finalproposal)
        response = self._validated_counteroffer(response, demands, territory_state_ids)
        if not finalproposal and self.counter_requested:
            response = response.model_copy(update={"decision": NegotiationDecision.counter})
            response = self._validated_counteroffer(
                response,
                demands,
                territory_state_ids,
            )
        self.counter_requested = False
        self.conversation_score = max(
            -24,
            min(24, self.conversation_score + response.concession_delta),
        )
        self.chat_history.append((self.defeated, response.message))
        return response

    def validate_proposal(self, demands, territory_state_ids):
        proposal = PeaceProposal(
            proposer=self.victor,
            recipient=self.defeated,
            demands=sorted(demands),
            territory_state_ids=sorted(territory_state_ids),
            final=True,
        )
        invalidstates = set(proposal.territory_state_ids) - self.available_state_ids
        if invalidstates:
            raise ValueError(
                f"Territory is not available in this conference: {', '.join(sorted(invalidstates))}"
            )
        if proposal.territory_state_ids and "STATE TRANSFER" not in proposal.demands:
            raise ValueError("Territory selections require the STATE TRANSFER demand.")
        return proposal


def calculate_country_strength(provincemap, countryname, economystate=None):
    provincecount = 0
    troopcount = 0
    for province in provincemap.values():
        controller = province.get("controllercountry", province.get("country"))
        if controller != countryname:
            continue
        provincecount += 1
        troopcount += max(0, int(province.get("troops", 0)))
    economystate = economystate or {}
    return (
        provincecount * 30.0
        + troopcount
        + max(0.0, float(economystate.get("gold", 0))) * 0.2
        + max(0.0, float(economystate.get("population", 0))) * 0.02
    )
