import copy
import datetime
import json
import math
import os
import random


DATA_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "game", "data", "domestic_affairs.json")
)

GAME_START_YEAR = 2020
GAME_START_DATE = datetime.date(2020, 1, 1)
DAYS_PER_TURN = 1
TURNS_PER_YEAR = int(math.ceil(365 / max(1, DAYS_PER_TURN)))
COVID_MIN_POPULATION = 1000
COVID_DEFAULT_TRANSMISSION_RATE = 0.28
COVID_DEFAULT_INFECTION_DAYS = 10.0
COVID_MCO_TRANSMISSION_MODIFIER = 0.32
COVID_HOSPITALISATION_RATE = 0.12
COVID_BASE_MORTALITY_RATE = 0.8
COVID_IMMUNITY_WANING_RATE = 1.0 / 150.0
COVID_UNCONTROLLED_BETA_BOOST = 1.22
COVID_BACKGROUND_IMPORTS_PER_100K = 7.0
COVID_LOW_CASE_RESEED_SHARE = 0.0015
COVID_DEFAULT_VACCINE_EFFECTIVENESS = 0.82
COVID_DEFAULT_VACCINE_SEVERE_PROTECTION = 0.72
COVID_ASEAN_FIRST_CASES = {
    "thailand": (datetime.date(2020, 1, 13), 1),
    "vietnam": (datetime.date(2020, 1, 23), 2),
    "singapore": (datetime.date(2020, 1, 23), 1),
    "malaysia": (datetime.date(2020, 1, 25), 3),
    "cambodia": (datetime.date(2020, 1, 27), 1),
    "philippines": (datetime.date(2020, 1, 30), 1),
    "indonesia": (datetime.date(2020, 3, 2), 2),
    "brunei": (datetime.date(2020, 3, 9), 1),
    "myanmar": (datetime.date(2020, 3, 23), 2),
    "laos": (datetime.date(2020, 3, 24), 2),
}
COVID_SRI_PETALING_CLUSTER_START = datetime.date(2020, 3, 10)
COVID_SRI_PETALING_CLUSTER_END = datetime.date(2020, 3, 24)
COVID_SRI_PETALING_DAILY_IMPORTS = {
    "malaysia": 12,
    "brunei": 3,
    "singapore": 2,
    "cambodia": 2,
    "indonesia": 2,
    "thailand": 1,
    "philippines": 1,
    "vietnam": 1,
}
COVID_RESPONSE_POLICIES = {
    "mask_mandate": {
        "label": "Mask Mandate",
        "enabled_key": "mask_mandate_enabled",
        "beta_modifier": 0.78,
        "gamma_modifier": 1.0,
        "economic_pressure": 0.03,
        "public_unrest": 0.03,
        "public_approval": -0.02,
        "investor_confidence": -0.01,
    },
    "testing_program": {
        "label": "Mass Testing",
        "enabled_key": "testing_program_enabled",
        "beta_modifier": 0.88,
        "gamma_modifier": 1.18,
        "economic_pressure": 0.05,
        "public_unrest": -0.02,
        "public_approval": 0.03,
        "investor_confidence": -0.02,
    },
    "border_controls": {
        "label": "Border Controls",
        "enabled_key": "border_controls_enabled",
        "beta_modifier": 0.92,
        "gamma_modifier": 1.0,
        "import_modifier": 0.35,
        "economic_pressure": 0.09,
        "public_unrest": 0.02,
        "public_approval": 0.01,
        "investor_confidence": -0.05,
    },
}
MALAYSIA_COUNTRY_KEY = "malaysia"
LEGISLATURE_SIDE_ORDER = {
    "government": 0,
    "neutral": 1,
    "appointed": 2,
    "military": 3,
    "vacant": 4,
    "opposition": 5,
}


def countrykey(value):
    text = str(value or "").strip().lower()
    text = text.replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def clamp(value, lower=0.0, upper=100.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = lower
    return max(lower, min(upper, number))


def safeint(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safefloat(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_domestic_affairs_configs(filepath=None):
    path = filepath or DATA_FILE
    with open(path, "r", encoding="utf-8") as fileobject:
        rawdata = json.load(fileobject)

    configs = {}
    for countrydata in rawdata.get("countries", ()):
        if not isinstance(countrydata, dict):
            continue
        countryid = str(countrydata.get("country_id") or countrydata.get("country_name") or "").strip()
        if not countryid:
            continue
        configs[countryid] = countrydata
    return configs


def create_domestic_affairs_state(configs=None):
    sourcedata = configs or load_domestic_affairs_configs()
    state = {}
    for countryid, countrydata in sourcedata.items():
        entry = copy.deepcopy(countrydata)
        entry["_last_election_year"] = None
        entry["_domestic_turns_seen"] = 0
        entry["_active_crises"] = []
        entry["_emitted_events"] = []
        refresh_government_state(entry)
        state[countryid] = entry
    return state


def get_country_entry(state, country):
    if not state or not country:
        return None

    wanted = countrykey(country)
    for countryid, entry in state.items():
        aliases = {
            countrykey(countryid),
            countrykey(entry.get("country_id")),
            countrykey(entry.get("country_name")),
        }
        if wanted in aliases:
            return entry
    return None


def turn_to_year(turnnumber):
    return turn_to_date(turnnumber).year


def turn_to_date(turnnumber):
    turn = max(1, safeint(turnnumber, 1))
    elapsed_days = (turn - 1) * DAYS_PER_TURN
    return GAME_START_DATE + datetime.timedelta(days=elapsed_days)


def turn_to_months_until_year(turnnumber, targetyear):
    target = safeint(targetyear, GAME_START_YEAR)
    current_day = (max(1, safeint(turnnumber, 1)) - 1) * DAYS_PER_TURN
    target_day = max(0, (target - GAME_START_YEAR) * 365)
    remaining_days = max(0, target_day - current_day)
    return int(math.ceil(remaining_days / 30.0))


def _lookup_economy_entry(npc_economies, countryid, countrydata):
    if not isinstance(npc_economies, dict):
        return None

    candidates = (
        countryid,
        (countrydata or {}).get("country_id"),
        (countrydata or {}).get("country_name"),
    )
    for candidate in candidates:
        if candidate in npc_economies and isinstance(npc_economies[candidate], dict):
            return npc_economies[candidate]

    wanted = countrykey(countryid or (countrydata or {}).get("country_id") or (countrydata or {}).get("country_name"))
    for economykey, economyentry in npc_economies.items():
        if countrykey(economykey) == wanted and isinstance(economyentry, dict):
            return economyentry
    return None


def _covid_country_key(countryid, countrydata):
    return countrykey((countrydata or {}).get("country_id") or (countrydata or {}).get("country_name") or countryid)


def _covid_first_case(countryid, countrydata):
    return COVID_ASEAN_FIRST_CASES.get(_covid_country_key(countryid, countrydata))


def _parse_iso_date(value):
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _active_covid_response_count(countrydata):
    response_count = 1 if countrydata.get("mco_enabled", False) else 0
    for policy in COVID_RESPONSE_POLICIES.values():
        if countrydata.get(policy["enabled_key"], False):
            response_count += 1
    if countrydata.get("covid_vaccine_rollout_active", False):
        response_count += 1
    return response_count


def _vaccine_rollout_started(countrydata, currentdate):
    if not countrydata.get("covid_vaccine_rollout_active", False):
        return False
    startdate = _parse_iso_date(countrydata.get("covid_vaccine_rollout_start_date"))
    if startdate is None:
        return True
    return currentdate is not None and currentdate >= startdate


def _apply_covid_vaccinations(countrydata, population, susceptible, recovered, currentdate):
    if not _vaccine_rollout_started(countrydata, currentdate):
        countrydata["covid_daily_vaccinations"] = 0
        return susceptible, recovered

    daily_capacity = max(0.0, safefloat(countrydata.get("covid_vaccine_daily_capacity", 0), 0.0))
    if daily_capacity <= 0 or susceptible <= 0:
        countrydata["covid_daily_vaccinations"] = 0
        return susceptible, recovered

    procurement = clamp(countrydata.get("covid_vaccine_procurement", 50)) / 100.0
    public_trust = clamp(countrydata.get("covid_vaccine_public_trust", 60)) / 100.0
    effectiveness = max(0.0, min(1.0, safefloat(countrydata.get("covid_vaccine_effectiveness", COVID_DEFAULT_VACCINE_EFFECTIVENESS), COVID_DEFAULT_VACCINE_EFFECTIVENESS)))
    capacity_modifier = 0.55 + procurement * 0.65
    uptake_modifier = 0.45 + public_trust * 0.70
    administered = min(susceptible, daily_capacity * capacity_modifier * uptake_modifier)
    protected = min(susceptible, administered * effectiveness)
    susceptible = max(0.0, susceptible - protected)
    recovered = min(population, recovered + protected)
    countrydata["covid_vaccinated"] = int(round(min(population, safefloat(countrydata.get("covid_vaccinated", 0), 0.0) + administered)))
    countrydata["covid_daily_vaccinations"] = int(round(administered))
    return susceptible, recovered


def _seed_covid_if_needed(countryid, countrydata, currentdate, population):
    first_case = _covid_first_case(countryid, countrydata)
    has_existing_model = any(
        countrydata.get(key) is not None
        for key in ("covid_susceptible", "covid_infectious", "covid_recovered")
    )
    if first_case is None:
        if not has_existing_model and countrydata.get("covid_cases") is None:
            countrydata["covid_cases"] = 0
            countrydata["covid_infectious"] = 0
            countrydata["covid_recovered"] = 0
            countrydata["covid_susceptible"] = int(round(population))
        return

    first_date, imported_cases = first_case
    countrydata["covid_first_case_date"] = first_date.isoformat()
    if currentdate < first_date and not countrydata.get("_covid_seeded"):
        countrydata["covid_cases"] = 0
        countrydata["covid_infectious"] = 0
        countrydata["covid_recovered"] = 0
        countrydata["covid_susceptible"] = int(round(population))
        countrydata["active_epidemic"] = "None"
        return

    if currentdate >= first_date and not countrydata.get("_covid_seeded"):
        infectious = max(float(imported_cases), safefloat(countrydata.get("covid_cases", 0), 0.0))
        countrydata["covid_infectious"] = int(round(infectious))
        countrydata["covid_cases"] = int(round(infectious))
        countrydata["covid_recovered"] = max(0, safeint(countrydata.get("covid_recovered", 0), 0))
        countrydata["covid_susceptible"] = int(round(max(0.0, population - infectious - countrydata["covid_recovered"])))
        countrydata["_covid_seeded"] = True
        countrydata["covid_momentum_note"] = f"First imported cases recorded on {first_date.isoformat()}."


def _estimate_covid_population(countryid, countrydata, is_player=False, player_metrics=None, npc_economies=None):
    population = 0
    if is_player and isinstance(player_metrics, dict):
        population = safeint(player_metrics.get("population", 0), 0)
    if population <= 0:
        economyentry = _lookup_economy_entry(npc_economies, countryid, countrydata)
        if economyentry:
            population = safeint(economyentry.get("population", 0), 0)
    if population <= 0:
        population = safeint(countrydata.get("covid_population", countrydata.get("population", COVID_MIN_POPULATION)), COVID_MIN_POPULATION)

    if countrydata.get("covid_susceptible") is not None:
        susceptible = max(0.0, safefloat(countrydata.get("covid_susceptible", 0), 0.0))
        current_cases = max(0.0, safefloat(countrydata.get("covid_infectious", countrydata.get("covid_cases", 0)), 0.0))
        recovered = max(0.0, safefloat(countrydata.get("covid_recovered", 0), 0.0))
        minimum_population = susceptible + current_cases + recovered
    else:
        current_cases = max(0.0, safefloat(countrydata.get("covid_infectious", countrydata.get("covid_cases", 0)), 0.0))
        recovered = max(0.0, safefloat(countrydata.get("covid_recovered", 0), 0.0))
        minimum_population = current_cases + recovered + 100.0

    return max(float(population), minimum_population, float(COVID_MIN_POPULATION))


def _normalise_covid_compartments(countrydata, population):
    infectious = max(0.0, safefloat(countrydata.get("covid_infectious", countrydata.get("covid_cases", 0)), 0.0))
    infectious = min(infectious, population)
    recovered = max(0.0, safefloat(countrydata.get("covid_recovered", 0), 0.0))
    recovered = min(recovered, max(0.0, population - infectious))

    if countrydata.get("covid_susceptible") is None:
        susceptible = max(0.0, population - infectious - recovered)
    else:
        susceptible = max(0.0, safefloat(countrydata.get("covid_susceptible", 0), 0.0))
        total = susceptible + infectious + recovered
        if total < population:
            susceptible += population - total
        elif total > population:
            overflow = total - population
            susceptible = max(0.0, susceptible - overflow)
            total = susceptible + infectious + recovered
            if total > population and total > 0:
                scale = population / total
                susceptible *= scale
                infectious *= scale
                recovered *= scale

    return susceptible, infectious, recovered


def _covid_calendar_beta_modifier(currentdate):
    if currentdate is None:
        return 1.0
    if currentdate < datetime.date(2020, 3, 1):
        return 0.35
    if currentdate < COVID_SRI_PETALING_CLUSTER_START:
        return 0.70
    if currentdate <= COVID_SRI_PETALING_CLUSTER_END:
        return 1.15
    return 1.0


def _covid_transmission_rates(countrydata, currentdate=None):
    beta = max(0.0, safefloat(countrydata.get("covid_beta", COVID_DEFAULT_TRANSMISSION_RATE), COVID_DEFAULT_TRANSMISSION_RATE))
    infection_days = max(1.0, safefloat(countrydata.get("covid_infection_duration_days", COVID_DEFAULT_INFECTION_DAYS), COVID_DEFAULT_INFECTION_DAYS))
    gamma = 1.0 / infection_days
    beta *= _covid_calendar_beta_modifier(currentdate)

    state_capacity = clamp(countrydata.get("state_capacity", 50)) / 100.0
    unrest = clamp(countrydata.get("public_unrest", 25)) / 100.0
    compliance_modifier = 1.0 + max(0.0, unrest - 0.35) * 0.20 - max(0.0, state_capacity - 0.50) * 0.10

    if countrydata.get("mco_enabled", False):
        mco_modifier = safefloat(countrydata.get("mco_beta_modifier", COVID_MCO_TRANSMISSION_MODIFIER), COVID_MCO_TRANSMISSION_MODIFIER)
        beta *= max(0.05, mco_modifier)
        beta *= max(0.75, 1.0 - state_capacity * 0.18)
    else:
        beta *= max(0.65, compliance_modifier)
        if currentdate is not None and currentdate >= datetime.date(2020, 3, 1) and _active_covid_response_count(countrydata) == 0:
            beta *= COVID_UNCONTROLLED_BETA_BOOST
        if currentdate is not None and currentdate >= datetime.date(2020, 4, 1):
            pressure_boost = max(0.0, clamp(countrydata.get("economic_pressure", 45)) - 55.0) * 0.004
            unrest_boost = max(0.0, clamp(countrydata.get("public_unrest", 25)) - 45.0) * 0.003
            beta *= 1.0 + min(0.25, pressure_boost + unrest_boost)

    for policy in COVID_RESPONSE_POLICIES.values():
        if countrydata.get(policy["enabled_key"], False):
            beta *= max(0.05, safefloat(policy.get("beta_modifier", 1.0), 1.0))
            gamma *= max(0.05, safefloat(policy.get("gamma_modifier", 1.0), 1.0))

    population = max(1.0, safefloat(countrydata.get("covid_population", COVID_MIN_POPULATION), COVID_MIN_POPULATION))
    vaccinated_share = max(0.0, min(1.0, safefloat(countrydata.get("covid_vaccinated", 0), 0.0) / population))
    if vaccinated_share > 0:
        beta *= max(0.45, 1.0 - vaccinated_share * 0.52)

    beta = max(0.0, beta)
    return beta, gamma, beta / gamma if gamma > 0 else 0.0


def _covid_daily_import_pressure(countryid, countrydata, currentdate):
    if currentdate is None or not countrydata.get("_covid_seeded"):
        return 0.0
    imports = 0.0
    if COVID_SRI_PETALING_CLUSTER_START <= currentdate <= COVID_SRI_PETALING_CLUSTER_END:
        imports += float(COVID_SRI_PETALING_DAILY_IMPORTS.get(_covid_country_key(countryid, countrydata), 0))
        if imports > 0:
            countrydata["covid_momentum_note"] = "Sri Petaling-linked regional seeding is increasing imported infections."

    if currentdate >= datetime.date(2020, 4, 1):
        population = max(1.0, safefloat(countrydata.get("covid_population", COVID_MIN_POPULATION), COVID_MIN_POPULATION))
        active_cases = max(0.0, safefloat(countrydata.get("covid_infectious", countrydata.get("covid_cases", 0)), 0.0))
        response_count = _active_covid_response_count(countrydata)
        background = population / 100000.0 * COVID_BACKGROUND_IMPORTS_PER_100K
        if response_count == 0:
            background *= 1.9
        elif response_count == 1:
            background *= 0.85
        else:
            background *= 0.35
        if active_cases < population * COVID_LOW_CASE_RESEED_SHARE:
            background += max(0.0, population * COVID_LOW_CASE_RESEED_SHARE - active_cases) * 0.08
        imports += background

    if imports <= 0:
        return 0.0
    border_policy = COVID_RESPONSE_POLICIES["border_controls"]
    if countrydata.get(border_policy["enabled_key"], False):
        imports *= safefloat(border_policy.get("import_modifier", 1.0), 1.0)
    elif currentdate >= datetime.date(2020, 4, 1):
        countrydata["covid_momentum_note"] = "Uncontrolled community spread is reseeding new chains of transmission."
    return imports


def _advance_country_covid(countryid, countrydata, currentdate=None, is_player=False, player_metrics=None, npc_economies=None):
    population = _estimate_covid_population(countryid, countrydata, is_player, player_metrics, npc_economies)
    _seed_covid_if_needed(countryid, countrydata, currentdate or GAME_START_DATE, population)
    susceptible, infectious, recovered = _normalise_covid_compartments(countrydata, population)
    beta, gamma, r0 = _covid_transmission_rates(countrydata, currentdate)

    total_new_infections = 0.0
    total_recoveries = 0.0
    waned_immunity = min(recovered, recovered * COVID_IMMUNITY_WANING_RATE * max(1, DAYS_PER_TURN))
    if waned_immunity > 0:
        recovered = max(0.0, recovered - waned_immunity)
        susceptible = min(population, susceptible + waned_immunity)
    susceptible, recovered = _apply_covid_vaccinations(countrydata, population, susceptible, recovered, currentdate)
    imported_infections = min(susceptible, _covid_daily_import_pressure(countryid, countrydata, currentdate))
    if imported_infections > 0:
        susceptible = max(0.0, susceptible - imported_infections)
        infectious += imported_infections
        total_new_infections += imported_infections

    for _ in range(max(1, safeint(DAYS_PER_TURN, 1))):
        if population <= 0 or infectious <= 0:
            break
        new_infections = min(susceptible, beta * susceptible * infectious / population)
        recoveries = min(infectious, gamma * infectious)
        susceptible = max(0.0, susceptible - new_infections)
        infectious = max(0.0, infectious + new_infections - recoveries)
        recovered = min(population, recovered + recoveries)
        total_new_infections += new_infections
        total_recoveries += recoveries

    vaccinated_share = max(0.0, min(1.0, safefloat(countrydata.get("covid_vaccinated", 0), 0.0) / max(1.0, population)))
    severe_protection = max(0.0, min(1.0, safefloat(
        countrydata.get("covid_vaccine_severe_protection", COVID_DEFAULT_VACCINE_SEVERE_PROTECTION),
        COVID_DEFAULT_VACCINE_SEVERE_PROTECTION,
    )))
    adjusted_hospitalisation_rate = COVID_HOSPITALISATION_RATE * max(0.30, 1.0 - vaccinated_share * severe_protection)
    hospitalisation = int(round(infectious * adjusted_hospitalisation_rate))
    healthcare_capacity_score = clamp(
        clamp(countrydata.get("state_capacity", 50)) * 0.75
        + clamp(countrydata.get("government_stability", 50)) * 0.25
    )
    hospital_capacity = max(20.0, population * 0.004 * max(0.40, healthcare_capacity_score / 50.0))
    healthcare_load_pct = hospitalisation / hospital_capacity * 100.0
    mortality_rate = min(6.0, COVID_BASE_MORTALITY_RATE * max(0.35, 1.0 - vaccinated_share * severe_protection) + max(0.0, healthcare_load_pct - 100.0) * 0.02)
    daily_deaths = total_recoveries * mortality_rate / 100.0

    countrydata["covid_population"] = int(round(population))
    countrydata["covid_susceptible"] = int(round(susceptible))
    countrydata["covid_infectious"] = int(round(infectious))
    countrydata["covid_recovered"] = int(round(recovered))
    countrydata["covid_cases"] = int(round(infectious))
    countrydata["covid_new_cases"] = int(round(total_new_infections))
    countrydata["covid_daily_recoveries"] = int(round(total_recoveries))
    countrydata["covid_waning_immunity"] = int(round(waned_immunity))
    countrydata["covid_deaths"] = round(safefloat(countrydata.get("covid_deaths", 0), 0.0) + daily_deaths, 2)
    countrydata["covid_effective_beta"] = round(beta, 4)
    countrydata["covid_gamma"] = round(gamma, 4)
    countrydata["covid_r0"] = round(r0, 2)
    countrydata["hospitalisation"] = hospitalisation
    countrydata["mortality"] = round(mortality_rate, 2)
    countrydata["covid_healthcare_load_pct"] = round(healthcare_load_pct, 1)

    if infectious < 1:
        countrydata["active_epidemic"] = "None"
    elif r0 < 1 and infectious < 200:
        countrydata["active_epidemic"] = "Contained"
    elif infectious > 500 or healthcare_load_pct >= 100:
        countrydata["active_epidemic"] = "Ongoing Outbreak"
    elif infectious > 200:
        countrydata["active_epidemic"] = "Localized Cases"
    else:
        countrydata["active_epidemic"] = "Imported Cases"

    _apply_covid_domestic_debuffs(countrydata, population, infectious, healthcare_load_pct)
    _apply_mco_domestic_debuffs(countrydata)


def _apply_covid_domestic_debuffs(countrydata, population, infectious, healthcare_load_pct):
    infection_share = infectious / max(1.0, population)
    if infectious <= 0:
        return

    load_pressure = max(0.0, healthcare_load_pct - 60.0) / 100.0
    epidemic_pressure = min(1.25, infection_share * 22.0 + load_pressure * 0.28)
    if infectious > 120 or healthcare_load_pct > 55:
        countrydata["economic_pressure"] = clamp(countrydata.get("economic_pressure", 45) + epidemic_pressure)
        countrydata["public_approval"] = clamp(countrydata.get("public_approval", 50) - min(0.48, infection_share * 8.0 + load_pressure * 0.13))
        countrydata["investor_confidence"] = clamp(countrydata.get("investor_confidence", 50) - min(0.42, infection_share * 9.0 + load_pressure * 0.11))
        countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) + min(0.42, infection_share * 7.0 + load_pressure * 0.12))
    if infectious > 300 or healthcare_load_pct >= 85:
        stability_loss = min(0.24, infection_share * 2.8 + max(0.0, healthcare_load_pct - 85.0) * 0.0008)
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 50) - stability_loss)
        countrydata["covid_economy_drag"] = int(min(25, max(4, infectious / 95.0 + max(0.0, healthcare_load_pct - 75.0) / 18.0)))
    else:
        countrydata["covid_economy_drag"] = 0


def _apply_mco_domestic_debuffs(countrydata):
    if not countrydata.get("mco_enabled", False):
        countrydata["mco_turns_active"] = 0
    else:
        countrydata["mco_turns_active"] = safeint(countrydata.get("mco_turns_active", 0), 0) + DAYS_PER_TURN
        countrydata["economic_pressure"] = clamp(countrydata.get("economic_pressure", 45) + 0.25 * DAYS_PER_TURN)
        countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) + 0.08 * DAYS_PER_TURN)
        countrydata["public_approval"] = clamp(countrydata.get("public_approval", 50) - 0.06 * DAYS_PER_TURN)
        countrydata["investor_confidence"] = clamp(countrydata.get("investor_confidence", 50) - 0.08 * DAYS_PER_TURN)

    for policy in COVID_RESPONSE_POLICIES.values():
        if not countrydata.get(policy["enabled_key"], False):
            continue
        countrydata["economic_pressure"] = clamp(
            countrydata.get("economic_pressure", 45) + safefloat(policy.get("economic_pressure", 0), 0.0) * DAYS_PER_TURN
        )
        countrydata["public_unrest"] = clamp(
            countrydata.get("public_unrest", 25) + safefloat(policy.get("public_unrest", 0), 0.0) * DAYS_PER_TURN
        )
        countrydata["public_approval"] = clamp(
            countrydata.get("public_approval", 50) + safefloat(policy.get("public_approval", 0), 0.0) * DAYS_PER_TURN
        )
        countrydata["investor_confidence"] = clamp(
            countrydata.get("investor_confidence", 50) + safefloat(policy.get("investor_confidence", 0), 0.0) * DAYS_PER_TURN
        )


def toggle_mco(countrydata):
    if not isinstance(countrydata, dict):
        return False

    enabled = not bool(countrydata.get("mco_enabled", False))
    countrydata["mco_enabled"] = enabled
    countrydata["mco_status"] = "Active" if enabled else "Lifted"
    countrydata["mco_toggle_count"] = safeint(countrydata.get("mco_toggle_count", 0), 0) + 1
    if enabled:
        countrydata["economic_pressure"] = clamp(countrydata.get("economic_pressure", 45) + 1.0)
        countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) + 0.4)
        countrydata["public_approval"] = clamp(countrydata.get("public_approval", 50) - 0.5)
    else:
        countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) - 0.4)
    return enabled


def get_covid_policy_definition(policykey):
    return COVID_RESPONSE_POLICIES.get(countrykey(policykey))


def toggle_covid_policy(countrydata, policykey):
    if not isinstance(countrydata, dict):
        return False
    policy = get_covid_policy_definition(policykey)
    if not policy:
        return False

    enabled_key = policy["enabled_key"]
    enabled = not bool(countrydata.get(enabled_key, False))
    countrydata[enabled_key] = enabled
    countrydata["covid_policy_toggle_count"] = safeint(countrydata.get("covid_policy_toggle_count", 0), 0) + 1
    if enabled:
        countrydata["economic_pressure"] = clamp(countrydata.get("economic_pressure", 45) + 0.4)
        if policykey == "testing_program":
            countrydata["public_approval"] = clamp(countrydata.get("public_approval", 50) + 0.3)
        elif policykey == "border_controls":
            countrydata["investor_confidence"] = clamp(countrydata.get("investor_confidence", 50) - 0.5)
        elif policykey == "mask_mandate":
            countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) + 0.2)
    return enabled


def party_seats(party):
    return max(0, safeint(party.get("seat_count", 0), 0))


def party_side(party):
    side = str(party.get("side") or "").strip().lower()
    if side in LEGISLATURE_SIDE_ORDER:
        return side
    if party.get("is_government"):
        return "government"
    if party.get("is_opposition"):
        return "opposition"
    if party.get("is_reserved"):
        return "military"
    if party_seats(party) <= 0:
        return "vacant"
    return "neutral"


def is_malaysia_country(countrydata):
    return countrykey((countrydata or {}).get("country_id") or (countrydata or {}).get("country_name")) == MALAYSIA_COUNTRY_KEY


def _sync_party_side_flags(countrydata):
    for party in countrydata.get("parties", ()):
        if not isinstance(party, dict):
            continue
        side = party_side(party)
        party["side"] = side
        party["is_government"] = side == "government"
        party["is_opposition"] = side == "opposition"


def _party_display_name(party):
    return str(party.get("short_name") or party.get("party_name") or party.get("party_id") or "").strip()


def _party_by_id(countrydata, partyid):
    wanted = countrykey(partyid)
    for party in countrydata.get("parties", ()):
        if isinstance(party, dict) and countrykey(party.get("party_id")) == wanted:
            return party
    return None


def _set_party_values(countrydata, partyid, seats=None, side=None, coalition=None, loyalty=None):
    party = _party_by_id(countrydata, partyid)
    if party is None:
        return None
    if seats is not None:
        party["seat_count"] = max(0, safeint(seats, 0))
    if side is not None:
        party["side"] = str(side).strip().lower()
    if coalition is not None:
        party["coalition"] = str(coalition)
    if loyalty is not None:
        party["loyalty_to_government"] = clamp(loyalty)
    sidevalue = party_side(party)
    party["side"] = sidevalue
    party["is_government"] = sidevalue == "government"
    party["is_opposition"] = sidevalue == "opposition"
    return party


def _ensure_party(countrydata, partydata):
    partyid = partydata.get("party_id")
    existing = _party_by_id(countrydata, partyid)
    if existing is not None:
        existing.update(copy.deepcopy(partydata))
        _set_party_values(countrydata, partyid)
        return existing
    countrydata.setdefault("parties", []).append(copy.deepcopy(partydata))
    _set_party_values(countrydata, partyid)
    return _party_by_id(countrydata, partyid)


def legislature_totals(countrydata):
    total_seats = max(0, safeint(countrydata.get("total_seats", 0), 0))
    parties = [party for party in countrydata.get("parties", ()) if isinstance(party, dict)]
    counted_seats = sum(party_seats(party) for party in parties)
    if total_seats <= 0:
        total_seats = counted_seats

    government_seats = sum(party_seats(party) for party in parties if party_side(party) == "government")
    opposition_seats = sum(party_seats(party) for party in parties if party_side(party) == "opposition")
    neutral_seats = max(0, total_seats - government_seats - opposition_seats)
    majority_needed = max(1, safeint(countrydata.get("majority_needed", (total_seats // 2) + 1), 1))

    return {
        "total_seats": total_seats,
        "counted_seats": counted_seats,
        "government_seats": government_seats,
        "opposition_seats": opposition_seats,
        "neutral_seats": neutral_seats,
        "majority_needed": majority_needed,
    }


def refresh_government_state(countrydata):
    if not isinstance(countrydata, dict):
        return {}

    _sync_party_side_flags(countrydata)
    totals = legislature_totals(countrydata)
    state = countrydata.get("government_state")
    if not isinstance(state, dict):
        state = {}
        countrydata["government_state"] = state

    current_pm = (
        countrydata.get("current_prime_minister")
        or state.get("current_prime_minister")
        or countrydata.get("head_of_government")
        or "Unknown"
    )
    ruling_coalition = (
        countrydata.get("ruling_coalition")
        or state.get("ruling_coalition")
        or countrydata.get("current_ruling_bloc")
        or "Unknown"
    )
    caretaker = bool(countrydata.get("caretaker_government", state.get("caretaker_government", False)))
    interim = bool(countrydata.get("interim_prime_minister", state.get("interim_prime_minister", False)))
    active_crisis = countrydata.get("active_political_crisis", state.get("active_political_crisis", False))

    government_parties = [
        _party_display_name(party)
        for party in countrydata.get("parties", ())
        if isinstance(party, dict) and party_side(party) == "government" and party_seats(party) > 0
    ]
    opposition_parties = [
        _party_display_name(party)
        for party in countrydata.get("parties", ())
        if isinstance(party, dict) and party_side(party) == "opposition" and party_seats(party) > 0
    ]

    parliament_status = countrydata.get("parliament_status") or state.get("parliament_status")
    if not parliament_status:
        parliament_status = _legislature_status_label(totals)

    state.update({
        "current_prime_minister": current_pm,
        "current_head_of_state": (
            countrydata.get("current_head_of_state")
            or state.get("current_head_of_state")
            or countrydata.get("head_of_state")
            or "Unknown"
        ),
        "ruling_coalition": ruling_coalition,
        "government_parties": government_parties,
        "opposition_parties": opposition_parties,
        "caretaker_government": caretaker,
        "interim_prime_minister": interim,
        "parliament_status": parliament_status,
        "government_seats": totals["government_seats"],
        "opposition_seats": totals["opposition_seats"],
        "majority_needed": totals["majority_needed"],
        "active_political_crisis": active_crisis,
    })

    countrydata["current_prime_minister"] = current_pm
    countrydata["head_of_government"] = current_pm
    countrydata["current_head_of_state"] = state["current_head_of_state"]
    countrydata["current_ruling_bloc"] = ruling_coalition
    countrydata["ruling_coalition"] = ruling_coalition
    countrydata["caretaker_government"] = caretaker
    countrydata["interim_prime_minister"] = interim
    countrydata["parliament_status"] = parliament_status
    countrydata["active_political_crisis"] = active_crisis
    return state


def current_leader_name(countrydata):
    if not isinstance(countrydata, dict):
        return ""
    state = refresh_government_state(countrydata)
    return str(state.get("current_prime_minister") or countrydata.get("head_of_government") or "").strip()


def build_focus_context(countrydata, currentturnnumber, player_metrics=None):
    if not isinstance(countrydata, dict):
        return {}
    government_state = refresh_government_state(countrydata)
    totals = legislature_totals(countrydata)
    currentdate = turn_to_date(currentturnnumber)
    context = {}
    for key, value in countrydata.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            context[key] = value
    context.update(government_state)
    context.update(totals)
    context["country_id"] = countrydata.get("country_id")
    context["country_name"] = countrydata.get("country_name")
    context["current_date"] = currentdate.isoformat()
    context["current_year"] = currentdate.year
    context["turn"] = safeint(currentturnnumber, 1)
    context["policy_passing_disabled"] = bool(countrydata.get("policy_passing_disabled", False))
    if player_metrics:
        context.update({f"player_{key}": value for key, value in player_metrics.items()})
    return context


def calculate_focus_speed_modifier(countrydata, focus_type="administrative_focus"):
    if not isinstance(countrydata, dict):
        return 1.0
    totals = legislature_totals(countrydata)
    modifier = 1.0
    stability = clamp(countrydata.get("government_stability", 50))
    if stability >= 70:
        modifier += 0.10
    elif stability < 40:
        modifier -= 0.25
    if countrydata.get("caretaker_government"):
        modifier *= 0.25
    margin = totals["government_seats"] - totals["majority_needed"]
    if margin >= 35:
        modifier += 0.10
    elif 0 <= margin <= 8:
        modifier -= 0.10
    if clamp(countrydata.get("public_unrest", 25)) > 50:
        modifier -= 0.10
    focus_type_text = str(focus_type or "").lower()
    if clamp(countrydata.get("covid_crisis_level", 0)) > 10 and "covid" not in focus_type_text and "emergency" not in focus_type_text:
        modifier -= 0.10
    return clamp(modifier, 0.20, 1.40)


def coalition_seats(countrydata):
    totals = {}
    for party in countrydata.get("parties", ()):
        if not isinstance(party, dict):
            continue
        coalition = str(party.get("coalition") or "Unaffiliated")
        totals[coalition] = totals.get(coalition, 0) + party_seats(party)
    return totals


def _highest_remainder(scores, seats):
    seats = max(0, safeint(seats, 0))
    entries = []
    total_score = sum(max(0.0, float(score)) for _, score in scores)
    if seats <= 0 or total_score <= 0:
        return {party_id: 0 for party_id, _ in scores}

    allocated = {}
    used = 0
    for party_id, score in scores:
        quota = max(0.0, float(score)) / total_score * seats
        whole = int(math.floor(quota))
        allocated[party_id] = whole
        used += whole
        entries.append((quota - whole, score, party_id))

    entries.sort(reverse=True)
    remaining = max(0, seats - used)
    for _, _, party_id in entries[:remaining]:
        allocated[party_id] = allocated.get(party_id, 0) + 1
    return allocated


def _dhondt(scores, seats):
    seats = max(0, safeint(seats, 0))
    allocation = {party_id: 0 for party_id, _ in scores}
    positive_scores = [(party_id, max(0.01, float(score))) for party_id, score in scores]
    if seats <= 0 or not positive_scores:
        return allocation

    for _ in range(seats):
        winner = max(
            positive_scores,
            key=lambda item: item[1] / (allocation.get(item[0], 0) + 1),
        )[0]
        allocation[winner] = allocation.get(winner, 0) + 1
    return allocation


def _party_score(party, mood):
    vote_share = max(0.2, float(party.get("vote_share", 0.0) or 0.0))
    popularity = clamp(party.get("popularity", 45.0)) / 100.0
    score = vote_share * (0.75 + popularity * 0.65)

    public_approval = clamp(mood.get("public_approval", 50.0))
    corruption = clamp(mood.get("corruption_level", 45.0))
    unrest = clamp(mood.get("public_unrest", 25.0))
    stability = clamp(mood.get("government_stability", 50.0))
    war_success = clamp(mood.get("war_success", 50.0))

    if party.get("is_government"):
        score *= 1.0 + (public_approval - 50.0) / 180.0
        score *= 1.0 + (stability - 50.0) / 220.0
        score *= 1.0 + (war_success - 50.0) / 250.0
        score *= 1.0 - max(0.0, corruption - 45.0) / 210.0
        score *= 1.0 - max(0.0, unrest - 40.0) / 260.0
    elif party.get("is_opposition"):
        score *= 1.0 + max(0.0, 50.0 - public_approval) / 150.0
        score *= 1.0 + max(0.0, corruption - 45.0) / 180.0
        score *= 1.0 + max(0.0, unrest - 40.0) / 180.0
        score *= 1.0 + max(0.0, 50.0 - stability) / 170.0
    else:
        score *= 1.0 + max(0.0, 45.0 - stability) / 240.0

    return max(0.01, score)


def _allocation_for_country(countrydata, mood):
    system = str(countrydata.get("seat_allocation_system") or "").strip().lower()
    parties = [party for party in countrydata.get("parties", ()) if isinstance(party, dict)]
    total_seats = max(0, safeint(countrydata.get("total_seats", 0), 0))
    reserved_parties = [party for party in parties if party.get("is_reserved")]
    reserved_seats = sum(party_seats(party) for party in reserved_parties)
    elected_total = max(0, safeint(countrydata.get("elected_seats", total_seats - reserved_seats), total_seats - reserved_seats))

    if system == "appointed":
        return {str(party.get("party_id")): party_seats(party) for party in parties}

    if system == "one_party":
        allocation = {str(party.get("party_id")): party_seats(party) for party in parties}
        legitimacy = clamp(countrydata.get("party_legitimacy", countrydata.get("public_approval", 60)))
        independent_parties = [party for party in parties if not party.get("is_government") and party_seats(party) > 0]
        governing_parties = [party for party in parties if party.get("is_government")]
        if governing_parties and independent_parties:
            swing = 1 if legitimacy < 55 else (-1 if legitimacy > 78 else 0)
            gov_id = str(governing_parties[0].get("party_id"))
            ind_id = str(independent_parties[0].get("party_id"))
            allocation[gov_id] = max(0, allocation.get(gov_id, 0) - swing)
            allocation[ind_id] = max(0, allocation.get(ind_id, 0) + swing)
        return allocation

    mutable_parties = [party for party in parties if not party.get("is_reserved")]
    scores = [(str(party.get("party_id")), _party_score(party, mood)) for party in mutable_parties]

    if system in ("fptp", "military_reserved"):
        boosted = [(party_id, score ** 1.18) for party_id, score in scores]
        allocation = _highest_remainder(boosted, elected_total)
    elif system == "mixed":
        constituency_seats = int(round(elected_total * 0.72))
        list_seats = max(0, elected_total - constituency_seats)
        fptp_alloc = _highest_remainder([(party_id, score ** 1.16) for party_id, score in scores], constituency_seats)
        pr_alloc = _dhondt(scores, list_seats)
        allocation = {
            party_id: fptp_alloc.get(party_id, 0) + pr_alloc.get(party_id, 0)
            for party_id, _ in scores
        }
    else:
        allocation = _dhondt(scores, elected_total)

    for party in reserved_parties:
        allocation[str(party.get("party_id"))] = party_seats(party)
    return allocation


def _apply_government_from_coalitions(countrydata):
    totals = coalition_seats(countrydata)
    if not totals:
        return None

    majority_needed = legislature_totals(countrydata)["majority_needed"]
    largest = max(totals.items(), key=lambda item: item[1])
    current_ruling = str(countrydata.get("current_ruling_bloc") or "")
    current_system = str(countrydata.get("government_system") or "").lower()
    presidential = "presidential" in current_system and "parliamentary" not in current_system

    if presidential and current_ruling:
        winner = current_ruling
    elif largest[1] >= majority_needed:
        winner = largest[0]
    else:
        winner = current_ruling or largest[0]

    countrydata["current_ruling_bloc"] = winner
    for party in countrydata.get("parties", ()):
        if not isinstance(party, dict):
            continue
        is_government = str(party.get("coalition") or "") == winner
        if party.get("is_reserved") and countrydata.get("seat_allocation_system") == "military_reserved":
            is_government = False
        party["side"] = "government" if is_government else ("opposition" if party_seats(party) > 0 and not party.get("is_reserved") else party_side(party))
        party["is_government"] = bool(is_government)
        party["is_opposition"] = bool(not is_government and party_seats(party) > 0 and not party.get("is_reserved"))

    opposition_names = [
        coalition for coalition, seats in totals.items()
        if coalition != winner and seats > 0
    ]
    if opposition_names:
        countrydata["current_opposition_bloc"] = ", ".join(opposition_names[:2])
    refresh_government_state(countrydata)
    return winner


def _run_election(countrydata, currentyear, mood, eventtype):
    allocation = _allocation_for_country(countrydata, mood)
    old_totals = legislature_totals(countrydata)
    old_government_seats = old_totals["government_seats"]

    for party in countrydata.get("parties", ()):
        if not isinstance(party, dict):
            continue
        partyid = str(party.get("party_id"))
        if partyid in allocation:
            party["seat_count"] = max(0, int(allocation[partyid]))

    _apply_government_from_coalitions(countrydata)
    totals = legislature_totals(countrydata)
    government_delta = totals["government_seats"] - old_government_seats

    if eventtype == "Controlled One-Party Election":
        legitimacy = clamp(countrydata.get("party_legitimacy", countrydata.get("public_approval", 60)))
        legitimacy += (clamp(countrydata.get("public_approval", 50)) - 50.0) / 12.0
        legitimacy -= max(0.0, clamp(countrydata.get("corruption_level", 45)) - 45.0) / 15.0
        countrydata["party_legitimacy"] = clamp(legitimacy)
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 60) + (legitimacy - 60.0) / 12.0)
    elif eventtype == "Appointed Legislature Refresh":
        countrydata["elite_loyalty"] = clamp(countrydata.get("elite_loyalty", 70) + 4)
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 70) + 2)
    else:
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 50) + government_delta / max(1, totals["total_seats"]) * 75.0)
        countrydata["public_approval"] = clamp(countrydata.get("public_approval", 50) + government_delta / max(1, totals["total_seats"]) * 35.0)
        if totals["government_seats"] >= totals["majority_needed"]:
            countrydata["coalition_loyalty"] = clamp(countrydata.get("coalition_loyalty", 50) + 6)
            countrydata["investor_confidence"] = clamp(countrydata.get("investor_confidence", 50) + 5)
        else:
            countrydata["coalition_loyalty"] = clamp(countrydata.get("coalition_loyalty", 50) - 10)
            countrydata["investor_confidence"] = clamp(countrydata.get("investor_confidence", 50) - 8)

    countrydata["next_election_year"] = currentyear + max(1, safeint(countrydata.get("election_cycle_years", 5), 5))
    countrydata["_last_election_year"] = currentyear

    return {
        "type": eventtype,
        "severity": "info",
        "country": countrydata.get("country_id"),
        "title": eventtype.upper(),
        "description": (
            f"{countrydata.get('country_name', countrydata.get('country_id'))} completed a {eventtype.lower()}. "
            f"Government seats: {totals['government_seats']}/{totals['total_seats']}."
        ),
        "government_seats": totals["government_seats"],
        "majority_needed": totals["majority_needed"],
    }


def _event_type_for_country(countrydata, regular=True):
    if countrydata.get("can_have_appointed_legislature"):
        return "Appointed Legislature Refresh"
    if countrydata.get("can_have_single_party_election"):
        return "Controlled One-Party Election"
    if countrydata.get("seat_allocation_system") == "military_reserved":
        return "Military-Managed Election"
    if regular:
        return "Regular Election"
    if countrydata.get("can_call_snap_election"):
        return "Snap Election"
    return "Post-Collapse Election"


def build_political_mood(countrydata, player_metrics=None, atwar=False):
    mood = {
        "public_approval": clamp(countrydata.get("public_approval", 50)),
        "government_stability": clamp(countrydata.get("government_stability", 50)),
        "coalition_loyalty": clamp(countrydata.get("coalition_loyalty", 50)),
        "corruption_level": clamp(countrydata.get("corruption_level", 45)),
        "public_unrest": clamp(countrydata.get("public_unrest", 25)),
        "economic_growth": 50.0,
        "inflation": 40.0,
        "unemployment": 35.0,
        "war_success": 50.0,
        "war_exhaustion": clamp(countrydata.get("war_exhaustion", 0)),
        "leader_popularity": clamp(countrydata.get("public_approval", 50)),
    }
    if player_metrics:
        if "stability" in player_metrics:
            mood["government_stability"] = (mood["government_stability"] * 0.55) + (clamp(player_metrics["stability"]) * 0.45)
        if "public_approval" in player_metrics:
            mood["public_approval"] = clamp(player_metrics["public_approval"])
    if atwar:
        mood["war_exhaustion"] = clamp(mood["war_exhaustion"] + 2)
        mood["public_unrest"] = clamp(mood["public_unrest"] + 3)
    return mood


def calculate_policy_passing_chance(countrydata, policy_type="major_policy"):
    refresh_government_state(countrydata)
    totals = legislature_totals(countrydata)
    government_seats = totals["government_seats"]
    majority_needed = totals["majority_needed"]
    total_seats = max(1, totals["total_seats"])
    coalition_loyalty = clamp(countrydata.get("coalition_loyalty", countrydata.get("coalition_unity", 50)))
    public_approval = clamp(countrydata.get("public_approval", 50))
    corruption = clamp(countrydata.get("corruption_level", 45))
    protest = clamp(countrydata.get("public_unrest", 25))
    stability = clamp(countrydata.get("government_stability", 50))
    opposition_resistance = clamp(countrydata.get("opposition_pressure", countrydata.get("opposition_confidence", 35)))
    fiscal_cost = clamp(countrydata.get("economic_pressure", 35))
    policy_type_text = str(policy_type or "").lower()

    if countrydata.get("policy_passing_disabled") and policy_type_text not in {"emergency", "crisis", "caretaker"}:
        return 2

    system = str(countrydata.get("seat_allocation_system") or "").lower()
    if system == "appointed":
        base = 62 + (clamp(countrydata.get("elite_loyalty", 70)) - 50) * 0.35
        return int(clamp(base + (stability - 50) * 0.2 - protest * 0.1, 5, 98))
    if system == "one_party":
        legitimacy = clamp(countrydata.get("party_legitimacy", public_approval))
        base = 70 + (legitimacy - 60) * 0.35 + (coalition_loyalty - 60) * 0.25
        return int(clamp(base - corruption * 0.08 - protest * 0.12, 5, 98))

    seat_margin = government_seats - majority_needed
    if government_seats < majority_needed:
        seat_bonus = -40
    elif seat_margin <= 5:
        seat_bonus = 5
    elif seat_margin <= 25:
        seat_bonus = 15
    elif seat_margin <= 60:
        seat_bonus = 25
    elif government_seats >= int(total_seats * 0.66):
        seat_bonus = 40
    else:
        seat_bonus = 30

    if coalition_loyalty >= 80:
        loyalty_modifier = 20
    elif coalition_loyalty >= 60:
        loyalty_modifier = 10
    elif coalition_loyalty >= 40:
        loyalty_modifier = 0
    elif coalition_loyalty >= 20:
        loyalty_modifier = -15
    else:
        loyalty_modifier = -35

    policy_penalty = 0
    if policy_type_text in {"controversial", "identity"}:
        policy_penalty = 10
    elif policy_type_text in {"budget", "economic_focus"}:
        policy_penalty = max(0, (fiscal_cost - 45.0) * 0.16)
    elif policy_type_text in {"emergency", "emergency_focus"}:
        policy_penalty = 4

    chance = (
        42
        + seat_bonus
        + loyalty_modifier
        + (public_approval - 50.0) * 0.32
        + (stability - 50.0) * 0.18
        - max(0.0, corruption - 45.0) * 0.22
        - max(0.0, protest - 35.0) * 0.24
        - max(0.0, opposition_resistance - 45.0) * 0.15
        - policy_penalty
    )
    if countrydata.get("active_political_crisis"):
        chance -= 10
    return int(clamp(chance, 3, 97))


def resolve_policy_vote(countrydata, turnnumber, policy_id, policy_type="major_policy"):
    chance = calculate_policy_passing_chance(countrydata, policy_type=policy_type)
    seed = f"{countrydata.get('country_id')}:{safeint(turnnumber, 1)}:{policy_id}:{policy_type}"
    roll = random.Random(seed).randint(1, 100)
    return {
        "chance": chance,
        "roll": roll,
        "passed": roll <= chance,
    }


def _emit_domestic_event_once(countrydata, events, eventid, title, description, severity="info"):
    emitted = set(countrydata.get("_emitted_events", ()))
    if eventid in emitted:
        return False
    emitted.add(eventid)
    countrydata["_emitted_events"] = sorted(emitted)
    events.append({
        "type": eventid,
        "severity": severity,
        "country": countrydata.get("country_id"),
        "title": title,
        "description": description,
    })
    return True


def _set_malaysia_caretaker(countrydata):
    countrydata["current_prime_minister"] = "Mahathir Mohamad"
    countrydata["head_of_government"] = "Mahathir Mohamad"
    countrydata["ruling_coalition"] = "Caretaker Government"
    countrydata["current_ruling_bloc"] = "Caretaker Government"
    countrydata["current_opposition_bloc"] = "No clear parliamentary majority"
    countrydata["caretaker_government"] = True
    countrydata["interim_prime_minister"] = True
    countrydata["policy_passing_disabled"] = True
    countrydata["active_political_crisis"] = "Sheraton Move"
    countrydata["parliament_status"] = "Hung / Unclear Majority"
    countrydata["government_stability"] = clamp(countrydata.get("government_stability", 50) - 28, 15, 100)
    countrydata["palace_confidence"] = clamp(countrydata.get("palace_confidence", 60) + 20)
    refresh_government_state(countrydata)


def _apply_malaysia_sheraton_breakdown(countrydata, events, currentdate):
    if countrydata.get("_sheraton_breakdown_done"):
        return
    countrydata["_sheraton_breakdown_done"] = True
    _set_party_values(countrydata, "bersatu", side="neutral", coalition="Realignment bloc", loyalty=12)
    pkr = _party_by_id(countrydata, "pkr")
    if pkr is not None and party_seats(pkr) >= 50:
        pkr["seat_count"] = 39
    _ensure_party(countrydata, {
        "party_id": "azmin_faction",
        "party_name": "Azmin-aligned PKR defectors",
        "short_name": "Azmin faction",
        "leader_name": "Azmin Ali",
        "ideology": "Pragmatic realignment",
        "coalition": "Realignment bloc",
        "seat_count": 11,
        "vote_share": 0.0,
        "side": "neutral",
        "is_government": False,
        "is_opposition": False,
        "loyalty_to_government": 8,
        "corruption_risk": 38,
        "defection_risk": 65,
        "popularity": 30,
        "color": "#64748B"
    })
    countrydata["coalition_unity"] = clamp(countrydata.get("coalition_unity", 46) - 24)
    countrydata["bersatu_loyalty"] = clamp(countrydata.get("bersatu_loyalty", 42) - 24)
    countrydata["pkr_internal_split"] = clamp(countrydata.get("pkr_internal_split", 65) + 12)
    _set_malaysia_caretaker(countrydata)
    _emit_domestic_event_once(
        countrydata,
        events,
        "malaysia_mahathir_resigns",
        "MAHATHIR RESIGNS",
        (
            "Mahathir Mohamad remains interim Prime Minister while the Yang di-Pertuan Agong "
            "interviews MPs to determine who commands the Dewan Rakyat majority."
        ),
        severity="critical",
    )


def _reset_malaysia_ph_layout(countrydata):
    ph_updates = (
        ("pkr", 50, "government", "Pakatan Harapan", 62),
        ("dap", 42, "government", "Pakatan Harapan", 70),
        ("bersatu", 26, "government", "Pakatan Harapan", countrydata.get("bersatu_loyalty", 45)),
        ("amanah", 11, "government", "Pakatan Harapan", 68),
        ("warisan", 9, "government", "Pakatan Harapan aligned", 60),
        ("upko", 1, "government", "Pakatan Harapan aligned", 55),
        ("independent_aligned", 1, "government", "Pakatan Harapan aligned", 48),
        ("umno_bn", 41, "opposition", "Barisan Nasional", 10),
        ("pas", 18, "opposition", "Gagasan Sejahtera", 8),
        ("gps", 18, "opposition", "GPS", 24),
        ("mca", 2, "opposition", "Barisan Nasional", 12),
        ("mic", 1, "opposition", "Barisan Nasional", 12),
        ("pbs", 1, "opposition", "Opposition regional bloc", 16),
        ("star", 1, "opposition", "Opposition regional bloc", 16),
        ("pbrs", 0, "opposition", "Opposition regional bloc", 16),
        ("azmin_faction", 0, "vacant", "Realignment bloc", 0),
    )
    for partyid, seats, side, coalition, loyalty in ph_updates:
        _set_party_values(countrydata, partyid, seats=seats, side=side, coalition=coalition, loyalty=loyalty)


def apply_malaysia_political_outcome(countrydata, outcome):
    if not is_malaysia_country(countrydata):
        return
    result = countrykey(outcome)
    if result in {"prevented", "block_sheraton", "ph_survives"}:
        _reset_malaysia_ph_layout(countrydata)
        countrydata["current_prime_minister"] = "Mahathir Mohamad"
        countrydata["head_of_government"] = "Mahathir Mohamad"
        countrydata["ruling_coalition"] = "Pakatan Harapan"
        countrydata["current_ruling_bloc"] = "Pakatan Harapan"
        countrydata["current_opposition_bloc"] = "BN / PAS / GPS / others"
        countrydata["caretaker_government"] = False
        countrydata["interim_prime_minister"] = False
        countrydata["policy_passing_disabled"] = False
        countrydata["active_political_crisis"] = False
        countrydata["parliament_status"] = "Pakatan Harapan survives"
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 45) + 8)
        countrydata["coalition_unity"] = clamp(countrydata.get("coalition_unity", 35) + 14)
        countrydata["sheraton_move_risk"] = clamp(countrydata.get("sheraton_move_risk", 70) - 35)
        countrydata["sheraton_move_prevented"] = True
    elif result in {"anwar", "anwar_transition", "anwar_ibrahim"}:
        _reset_malaysia_ph_layout(countrydata)
        _set_party_values(countrydata, "bersatu", side="opposition", coalition="Bersatu opposition", loyalty=12)
        countrydata["current_prime_minister"] = "Anwar Ibrahim"
        countrydata["head_of_government"] = "Anwar Ibrahim"
        countrydata["ruling_coalition"] = "Pakatan Harapan"
        countrydata["current_ruling_bloc"] = "Pakatan Harapan"
        countrydata["current_opposition_bloc"] = "Bersatu, BN, PAS, GPS, and others"
        countrydata["caretaker_government"] = False
        countrydata["interim_prime_minister"] = False
        countrydata["policy_passing_disabled"] = False
        countrydata["active_political_crisis"] = False
        countrydata["parliament_status"] = "Anwar transition majority"
        countrydata["government_stability"] = clamp(50)
        countrydata["public_approval"] = clamp(countrydata.get("public_approval", 54) + 5)
        countrydata["sheraton_move_risk"] = clamp(countrydata.get("sheraton_move_risk", 70) - 25)
    elif result in {"mahathir_consensus", "consensus"}:
        _reset_malaysia_ph_layout(countrydata)
        _set_party_values(countrydata, "gps", side="government", coalition="National Unity Government", loyalty=52)
        countrydata["current_prime_minister"] = "Mahathir Mohamad"
        countrydata["head_of_government"] = "Mahathir Mohamad"
        countrydata["ruling_coalition"] = "National Unity Government"
        countrydata["current_ruling_bloc"] = "National Unity Government"
        countrydata["current_opposition_bloc"] = "Organized opposition"
        countrydata["caretaker_government"] = False
        countrydata["interim_prime_minister"] = False
        countrydata["policy_passing_disabled"] = False
        countrydata["active_political_crisis"] = False
        countrydata["parliament_status"] = "Consensus majority"
        countrydata["government_stability"] = clamp(46)
        countrydata["sheraton_move_risk"] = clamp(38)
    elif result in {"hung", "hung_parliament"}:
        _set_malaysia_caretaker(countrydata)
        countrydata["parliament_status"] = "Hung parliament"
        countrydata["government_stability"] = clamp(20)
    else:
        pn_updates = (
            ("bersatu", 31, "government", "Perikatan Nasional-aligned government", 70),
            ("umno_bn", 39, "government", "Perikatan Nasional-aligned government", 50),
            ("pas", 18, "government", "Perikatan Nasional-aligned government", 76),
            ("gps", 18, "government", "Perikatan Nasional-aligned government", 58),
            ("mca", 2, "government", "Perikatan Nasional-aligned government", 70),
            ("mic", 1, "government", "Perikatan Nasional-aligned government", 70),
            ("pbs", 1, "government", "Perikatan Nasional-aligned government", 60),
            ("star", 1, "government", "Perikatan Nasional-aligned government", 59),
            ("pbrs", 1, "government", "Perikatan Nasional-aligned government", 62),
            ("pkr", 39, "opposition", "Pakatan Harapan", 10),
            ("dap", 42, "opposition", "Pakatan Harapan", 8),
            ("amanah", 11, "opposition", "Pakatan Harapan", 10),
            ("warisan", 9, "opposition", "Pakatan Harapan aligned", 14),
            ("upko", 1, "opposition", "Pakatan Harapan aligned", 14),
            ("independent_aligned", 8, "opposition", "Pakatan Harapan aligned", 24),
            ("azmin_faction", 0, "vacant", "Realignment bloc", 0),
        )
        for partyid, seats, side, coalition, loyalty in pn_updates:
            _set_party_values(countrydata, partyid, seats=seats, side=side, coalition=coalition, loyalty=loyalty)
        countrydata["current_prime_minister"] = "Muhyiddin Yassin"
        countrydata["head_of_government"] = "Muhyiddin Yassin"
        countrydata["ruling_coalition"] = "Perikatan Nasional-aligned government"
        countrydata["current_ruling_bloc"] = "Perikatan Nasional-aligned government"
        countrydata["current_opposition_bloc"] = "Pakatan Harapan and remaining anti-PN parties"
        countrydata["caretaker_government"] = False
        countrydata["interim_prime_minister"] = False
        countrydata["policy_passing_disabled"] = False
        countrydata["active_political_crisis"] = False
        countrydata["parliament_status"] = "Wafer-thin Majority"
        countrydata["government_status"] = "Wafer-thin Majority"
        countrydata["government_stability"] = 35
        countrydata["coalition_unity"] = 45
        countrydata["public_approval"] = 45
        countrydata["succession_tension"] = 35
        countrydata["pkr_internal_split"] = 30
        countrydata["sheraton_move_risk"] = 0
        countrydata["sheraton_move_succeeded"] = True
        countrydata["budget_confidence_test_unlocked"] = True
        countrydata["policy_tree_branch"] = "PN Consolidation"
    refresh_government_state(countrydata)


def _update_malaysia_sheraton_risk(countrydata):
    if countrydata.get("sheraton_move_succeeded") or countrydata.get("sheraton_move_prevented"):
        return
    monthly_delta = 0.0
    monthly_delta += clamp(countrydata.get("succession_tension", 0)) * 0.10
    monthly_delta += clamp(countrydata.get("pkr_internal_split", 0)) * 0.08
    monthly_delta += max(0.0, 60.0 - clamp(countrydata.get("bersatu_loyalty", 0))) * 0.12
    monthly_delta += clamp(countrydata.get("umno_recovery_strength", 0)) * 0.05
    monthly_delta -= clamp(countrydata.get("coalition_unity", 0)) * 0.05
    monthly_delta -= clamp(countrydata.get("mahathir_authority", 0)) * 0.04
    monthly_delta -= clamp(countrydata.get("reform_compromise", 0)) * 0.06
    countrydata["sheraton_move_risk"] = clamp(
        countrydata.get("sheraton_move_risk", 50) + monthly_delta * (DAYS_PER_TURN / 30.0)
    )


def _resolve_malaysia_sheraton(countrydata, events):
    if countrydata.get("_sheraton_resolved"):
        return
    countrydata["_sheraton_resolved"] = True
    route = countrykey(countrydata.get("sheraton_route"))
    if route in {"prevented", "block_sheraton", "ph_survives"}:
        outcome = "prevented"
        title = "SHERATON MOVE BLOCKED"
        description = "Mahathir keeps Pakatan Harapan together, but the succession question remains dangerous."
    elif route in {"anwar", "anwar_transition"}:
        outcome = "anwar_transition"
        title = "ANWAR COMMANDS A MAJORITY"
        description = "Anwar Ibrahim becomes Prime Minister after Pakatan Harapan survives the crisis."
    elif route in {"mahathir_consensus", "consensus"}:
        outcome = "mahathir_consensus"
        title = "MAHATHIR RETURNS AS CONSENSUS PM"
        description = "Mahathir Mohamad forms a consensus government above the original coalition lines."
    elif route in {"hung", "hung_parliament"}:
        outcome = "hung"
        title = "HUNG PARLIAMENT"
        description = "No bloc reaches 112 seats, leaving the country in a caretaker crisis."
    else:
        outcome = "pn"
        title = "MUHYIDDIN APPOINTED PRIME MINISTER"
        description = "Muhyiddin Yassin is appointed Prime Minister and a Perikatan Nasional-aligned government takes office."
    apply_malaysia_political_outcome(countrydata, outcome)
    _emit_domestic_event_once(countrydata, events, f"malaysia_sheraton_outcome_{outcome}", title, description, severity="critical")


def _advance_malaysia_covid(countrydata, currentdate):
    if currentdate < datetime.date(2020, 3, 15):
        return
    countrydata["covid_crisis_level"] = clamp(countrydata.get("covid_crisis_level", 0) + 1.1 * DAYS_PER_TURN)
    countrydata["economic_pressure"] = clamp(countrydata.get("economic_pressure", 45) + 0.36 * DAYS_PER_TURN)
    if clamp(countrydata.get("covid_crisis_level", 0)) > 35:
        countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) + 0.1 * DAYS_PER_TURN)


def _maybe_malaysia_budget_test(countrydata, events, currentdate, currentturnnumber):
    if not countrydata.get("budget_confidence_test_unlocked"):
        return
    if countrydata.get("_budget_2021_test_done"):
        return
    if currentdate < datetime.date(2020, 11, 1):
        return
    totals = legislature_totals(countrydata)
    if countrydata.get("current_prime_minister") != "Muhyiddin Yassin" or totals["government_seats"] > 120:
        return
    countrydata["_budget_2021_test_done"] = True
    chance = calculate_policy_passing_chance(countrydata, policy_type="budget")
    roll = random.Random(f"malaysia_budget_2021:{currentturnnumber}").randint(1, 100)
    if roll <= chance:
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 35) + 12)
        countrydata["muhyiddin_legitimacy"] = clamp(countrydata.get("muhyiddin_legitimacy", 0) + 10)
        countrydata["coalition_loyalty"] = clamp(countrydata.get("coalition_loyalty", 45) + 5)
        countrydata["opposition_pressure"] = clamp(countrydata.get("opposition_pressure", 68) - 5)
        description = f"Budget 2021 passed as a confidence test ({chance}% chance, roll {roll})."
    else:
        countrydata["government_stability"] = clamp(countrydata.get("government_stability", 35) - 25)
        countrydata["active_political_crisis"] = "No-confidence crisis"
        countrydata["parliament_status"] = "Budget confidence crisis"
        description = f"Budget 2021 failed as a confidence test ({chance}% chance, roll {roll})."
    _emit_domestic_event_once(
        countrydata,
        events,
        "malaysia_budget_2021_confidence_test",
        "BUDGET 2021 CONFIDENCE TEST",
        description,
        severity="critical",
    )


def _advance_malaysia_politics(countrydata, currentturnnumber, events):
    currentdate = turn_to_date(currentturnnumber)
    _update_malaysia_sheraton_risk(countrydata)
    _advance_malaysia_covid(countrydata, currentdate)

    risk = clamp(countrydata.get("sheraton_move_risk", 0))
    if (
        currentdate >= datetime.date(2020, 2, 15)
        and risk >= 60
        and not countrydata.get("sheraton_move_succeeded")
        and not countrydata.get("sheraton_move_prevented")
    ):
        _emit_domestic_event_once(
            countrydata,
            events,
            "malaysia_sheraton_warning",
            "RUMOURS OF REALIGNMENT",
            "Rumours of a major political realignment are spreading. Coalition partners are meeting outside official channels.",
            severity="warning",
        )

    if (
        currentdate >= datetime.date(2020, 2, 23)
        and risk >= 75
        and not countrydata.get("active_political_crisis")
        and not countrydata.get("sheraton_move_succeeded")
        and not countrydata.get("sheraton_move_prevented")
    ):
        countrydata["active_political_crisis"] = "Sheraton Move"
        countrydata["sheraton_crisis_stage"] = "Sheraton Meeting"
        _emit_domestic_event_once(
            countrydata,
            events,
            "malaysia_sheraton_meeting",
            "SHERATON MEETING",
            "Several MPs and party leaders gather to discuss a new political alignment. The ruling coalition is at risk of collapsing.",
            severity="critical",
        )

    if (
        countrydata.get("active_political_crisis") == "Sheraton Move"
        and countrykey(countrydata.get("sheraton_route")) in {"prevented", "block_sheraton", "ph_survives"}
        and currentdate >= datetime.date(2020, 2, 23)
    ):
        _resolve_malaysia_sheraton(countrydata, events)

    if (
        countrydata.get("active_political_crisis") == "Sheraton Move"
        and currentdate >= datetime.date(2020, 2, 24)
        and not countrydata.get("sheraton_move_prevented")
    ):
        _apply_malaysia_sheraton_breakdown(countrydata, events, currentdate)

    if (
        countrydata.get("active_political_crisis") == "Sheraton Move"
        and currentdate >= datetime.date(2020, 3, 1)
    ):
        _resolve_malaysia_sheraton(countrydata, events)

    _maybe_malaysia_budget_test(countrydata, events, currentdate, currentturnnumber)
    refresh_government_state(countrydata)


def _maybe_add_crisis(countrydata, events, currentyear):
    totals = legislature_totals(countrydata)
    countryname = countrydata.get("country_name") or countrydata.get("country_id")
    emitted = set(countrydata.get("_active_crises", ()))

    if totals["government_seats"] < totals["majority_needed"] and countrydata.get("can_have_no_confidence_vote"):
        crisisid = "loss_of_majority"
        if crisisid not in emitted:
            emitted.add(crisisid)
            countrydata["government_stability"] = clamp(countrydata.get("government_stability", 50) - 12)
            countrydata["investor_confidence"] = clamp(countrydata.get("investor_confidence", 50) - 8)
            events.append({
                "type": "Loss of Majority",
                "severity": "critical",
                "country": countrydata.get("country_id"),
                "title": "LOSS OF MAJORITY",
                "description": f"{countryname}'s government has fallen below the majority threshold.",
            })

    if (
        countrydata.get("can_have_coup_risk")
        and clamp(countrydata.get("military_influence", 0)) > 75
        and clamp(countrydata.get("government_stability", 50)) < 55
        and clamp(countrydata.get("public_unrest", 0)) > 50
    ):
        crisisid = "coup_risk"
        if crisisid not in emitted:
            emitted.add(crisisid)
            countrydata["international_legitimacy"] = clamp(countrydata.get("international_legitimacy", 50) - 8)
            events.append({
                "type": "Coup Risk",
                "severity": "critical",
                "country": countrydata.get("country_id"),
                "title": "MILITARY INTERVENTION RISK",
                "description": f"Military pressure is destabilizing {countryname}'s civilian government.",
            })

    if turn_to_months_until_year((currentyear - GAME_START_YEAR) * TURNS_PER_YEAR + 1, countrydata.get("next_election_year")) <= 12:
        crisisid = f"election_warning_{countrydata.get('next_election_year')}"
        if crisisid not in emitted:
            emitted.add(crisisid)
            events.append({
                "type": "Election Warning",
                "severity": "info",
                "country": countrydata.get("country_id"),
                "title": "ELECTION EXPECTED WITHIN 12 MONTHS",
                "description": f"{countryname} is approaching its next scheduled election.",
            })

    countrydata["_active_crises"] = sorted(emitted)


def advance_domestic_affairs_turn(
    state,
    currentturnnumber,
    playercountry=None,
    player_metrics=None,
    npc_economies=None,
    countriesatwarset=None,
):
    events = []
    effects = {"player_stability_delta": 0.0, "player_pp_delta": 0, "player_ap_delta": 0, "player_gold_delta": 0}
    currentyear = turn_to_year(currentturnnumber)
    countriesatwarset = set(countriesatwarset or ())
    playerkey = countrykey(playercountry)
    currentdate = turn_to_date(currentturnnumber)

    for countryid, countrydata in (state or {}).items():
        countrydata["_domestic_turns_seen"] = safeint(countrydata.get("_domestic_turns_seen", 0), 0) + 1
        is_player = playerkey and countrykey(countryid) == playerkey
        _advance_country_covid(
            countryid,
            countrydata,
            currentdate=currentdate,
            is_player=is_player,
            player_metrics=player_metrics if is_player else None,
            npc_economies=npc_economies,
        )

        atwar = countryid in countriesatwarset or countrydata.get("country_name") in countriesatwarset
        mood = build_political_mood(countrydata, player_metrics if is_player else None, atwar=atwar)

        if atwar:
            countrydata["war_exhaustion"] = clamp(countrydata.get("war_exhaustion", 0) + 0.8)
            countrydata["public_approval"] = clamp(countrydata.get("public_approval", 50) - 0.15)
            countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) + 0.2)
        else:
            countrydata["war_exhaustion"] = clamp(countrydata.get("war_exhaustion", 0) - 0.25)
            countrydata["public_unrest"] = clamp(countrydata.get("public_unrest", 25) - 0.05)

        if is_player and player_metrics and "stability" in player_metrics:
            countrydata["government_stability"] = clamp(
                countrydata.get("government_stability", 50) * 0.94 + clamp(player_metrics["stability"]) * 0.06
            )

        if is_malaysia_country(countrydata):
            _advance_malaysia_politics(countrydata, currentturnnumber, events)

        if currentyear >= safeint(countrydata.get("next_election_year", 9999), 9999):
            if countrydata.get("_last_election_year") != currentyear:
                eventtype = _event_type_for_country(countrydata, regular=True)
                events.append(_run_election(countrydata, currentyear, mood, eventtype))

        _maybe_add_crisis(countrydata, events, currentyear)

        if is_player:
            stability = clamp(countrydata.get("government_stability", 50))
            approval = clamp(countrydata.get("public_approval", 50))
            investor_confidence = clamp(countrydata.get("investor_confidence", 50))
            if stability < 35:
                effects["player_stability_delta"] -= 1.2
                effects["player_pp_delta"] -= 1
            elif stability > 75 and approval > 55:
                effects["player_stability_delta"] += 0.5
                effects["player_pp_delta"] += 1
            if investor_confidence > 70:
                effects["player_ap_delta"] += 1
            elif investor_confidence < 35:
                effects["player_ap_delta"] -= 1
            healthcare_load = safefloat(countrydata.get("covid_healthcare_load_pct", 0), 0.0)
            active_cases = safeint(countrydata.get("covid_cases", 0), 0)
            economy_drag = safeint(countrydata.get("covid_economy_drag", 0), 0)
            if healthcare_load >= 100 or active_cases > 500:
                effects["player_stability_delta"] -= 0.15
                effects["player_ap_delta"] -= 1
                effects["player_pp_delta"] -= 1
            elif active_cases > 200:
                effects["player_stability_delta"] -= 0.05
            if economy_drag > 0:
                effects["player_gold_delta"] -= economy_drag
            if countrydata.get("mco_enabled", False):
                effects["player_stability_delta"] -= 0.1
                effects["player_ap_delta"] -= 1
            if countrydata.get("testing_program_enabled", False):
                effects["player_ap_delta"] -= 1
            if countrydata.get("border_controls_enabled", False):
                effects["player_ap_delta"] -= 1

    return {"events": events, "effects": effects}


def build_domestic_affairs_view(state, country, currentturnnumber, player_metrics=None):
    countrydata = get_country_entry(state, country)
    if countrydata is None:
        return {}

    government_state = refresh_government_state(countrydata)
    totals = legislature_totals(countrydata)
    months_to_election = turn_to_months_until_year(currentturnnumber, countrydata.get("next_election_year"))
    chart_parties = []
    total_seats = max(1, totals["total_seats"])

    parties = [party for party in countrydata.get("parties", ()) if isinstance(party, dict)]
    parties.sort(key=lambda party: (
        LEGISLATURE_SIDE_ORDER.get(party_side(party), 9),
        str(party.get("coalition") or ""),
        -party_seats(party),
        str(party.get("short_name") or party.get("party_name") or ""),
    ))
    for party in parties:
        if not isinstance(party, dict):
            continue
        seats = party_seats(party)
        if seats <= 0:
            continue
        status = party_side(party)
        entry = dict(party)
        entry["status"] = status
        entry["side"] = status
        entry["seat_count"] = seats
        entry["seat_percent"] = round(seats / total_seats * 100.0, 1)
        chart_parties.append(entry)

    warnings = []
    if totals["government_seats"] < totals["majority_needed"] and countrydata.get("can_have_no_confidence_vote"):
        warnings.append("Government has lost its parliamentary majority.")
    if months_to_election <= 12:
        warnings.append("Election expected within 12 months.")
    if clamp(countrydata.get("public_approval", 50)) < 35:
        warnings.append("Government popularity is collapsing.")
    if countrydata.get("can_have_coup_risk") and clamp(countrydata.get("military_influence", 0)) > 70:
        warnings.append("Military intervention risk is increasing.")
    if countrydata.get("can_have_single_party_election") and clamp(countrydata.get("party_legitimacy", 70)) < 45:
        warnings.append("Party legitimacy is weakening.")
    if is_malaysia_country(countrydata):
        sheraton_unresolved = not countrydata.get("sheraton_move_succeeded") and not countrydata.get("sheraton_move_prevented")
        if sheraton_unresolved and clamp(countrydata.get("succession_tension", 0)) >= 60:
            warnings.append("Succession tensions are threatening Pakatan Harapan unity.")
        if sheraton_unresolved and clamp(countrydata.get("sheraton_move_risk", 0)) > 60:
            warnings.append("Rumours of political realignment are spreading.")
        if sheraton_unresolved and clamp(countrydata.get("bersatu_loyalty", 0)) < 40:
            warnings.append("Bersatu may withdraw from the ruling coalition.")
        if sheraton_unresolved and clamp(countrydata.get("pkr_internal_split", 0)) > 60:
            warnings.append("PKR factionalism may cause defections.")
        if countrydata.get("caretaker_government"):
            warnings.append("Caretaker government: normal policy work is limited.")
        if countrydata.get("current_prime_minister") == "Muhyiddin Yassin" and 112 <= totals["government_seats"] <= 120:
            warnings.append("Wafer-thin majority: budget votes and confidence motions are dangerous.")

    policy_chance = calculate_policy_passing_chance(countrydata)
    view = copy.deepcopy(countrydata)
    view.update(government_state)
    view.update(totals)
    currentdate = turn_to_date(currentturnnumber)
    view["current_date"] = currentdate.isoformat()
    view["current_year"] = turn_to_year(currentturnnumber)
    view["months_to_election"] = months_to_election
    view["election_timer"] = f"{months_to_election} months" if months_to_election else "Due now"
    view["chart_parties"] = chart_parties
    view["warnings"] = warnings
    view["policy_passing_chance"] = policy_chance
    view["legislature_status"] = _legislature_status_label(totals)
    view["economy_effects"] = _economy_effects(countrydata)
    view["health"] = _health_effects(countrydata)
    view["internal_policy_effects"] = _internal_policy_effects(countrydata)
    if player_metrics:
        view["player_metrics"] = dict(player_metrics)
    return view


def _legislature_status_label(totals):
    margin = totals["government_seats"] - totals["majority_needed"]
    if margin < 0:
        return "No majority"
    if margin <= 4:
        return "Wafer-thin Majority"
    if margin <= 28:
        return "Fragile Majority"
    if margin <= 35:
        return "Workable Majority"
    return "Strong Majority"


def _economy_effects(countrydata):
    stability = clamp(countrydata.get("government_stability", 50))
    investor = clamp(countrydata.get("investor_confidence", 50))
    corruption = clamp(countrydata.get("corruption_level", 45))
    if stability >= 70 and investor >= 60:
        budget = "Budget passing is easier and infrastructure projects move faster."
    elif stability < 40:
        budget = "Budget delays are likely and investor confidence is fragile."
    else:
        budget = "Budget passage depends on coalition discipline and public approval."
    return {
        "investor_confidence": investor,
        "currency_stability": clamp((investor + stability) / 2.0 - max(0.0, corruption - 50.0) * 0.2),
        "budget_passing": budget,
        "project_speed": "Faster" if stability > 70 else ("Slower" if stability < 40 else "Normal"),
    }
    
def _health_effects(countrydata):
    current_cases = safeint(
        countrydata.get("covid_cases", 0),
        0
    )
    susceptible = safeint(countrydata.get("covid_susceptible", 0), 0)
    recovered = safeint(countrydata.get("covid_recovered", 0), 0)
    new_cases = safeint(countrydata.get("covid_new_cases", 0), 0)
    r0 = safefloat(countrydata.get("covid_r0", 0), 0.0)
    beta = safefloat(countrydata.get("covid_effective_beta", countrydata.get("covid_beta", 0)), 0.0)
    gamma = safefloat(countrydata.get("covid_gamma", 0), 0.0)

    hospitalisation = safeint(
        countrydata.get("hospitalisation", 0),
        0
    )

    mortality = float(
        countrydata.get("mortality", 0)
    )

    active_epidemic = countrydata.get(
        "active_epidemic",
        "None"
    )

    healthcare_capacity = clamp(
        countrydata.get(
            "government_stability",
            50
        )
    )

    healthcare_load_pct = safefloat(countrydata.get("covid_healthcare_load_pct", 0), 0.0)
    vaccinated = safeint(countrydata.get("covid_vaccinated", 0), 0)
    population = max(1, safeint(countrydata.get("covid_population", 0), 0))

    if healthcare_load_pct >= 100 or current_cases > 500:
        risk_level = "High"
    elif healthcare_load_pct >= 70 or current_cases > 200:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "active_epidemic": active_epidemic,
        "current_cases": current_cases,
        "new_cases": new_cases,
        "susceptible": susceptible,
        "recovered": recovered,
        "r0": r0,
        "beta": beta,
        "gamma": gamma,
        "mortality": mortality,
        "hospitalisation": hospitalisation,
        "risk_level": risk_level,
        "healthcare_capacity": healthcare_capacity,
        "healthcare_load_pct": healthcare_load_pct,
        "economy_drag": safeint(countrydata.get("covid_economy_drag", 0), 0),
        "vaccinated": vaccinated,
        "vaccinated_share": vaccinated / population * 100.0,
        "daily_vaccinations": safeint(countrydata.get("covid_daily_vaccinations", 0), 0),
        "vaccine_rollout_active": bool(countrydata.get("covid_vaccine_rollout_active", False)),
        "vaccine_public_trust": clamp(countrydata.get("covid_vaccine_public_trust", 0)),
        "vaccine_procurement": clamp(countrydata.get("covid_vaccine_procurement", 0)),
        "momentum_note": countrydata.get("covid_momentum_note", ""),
        "first_case_date": countrydata.get("covid_first_case_date", ""),
        "mask_mandate_enabled": bool(countrydata.get("mask_mandate_enabled", False)),
        "testing_program_enabled": bool(countrydata.get("testing_program_enabled", False)),
        "border_controls_enabled": bool(countrydata.get("border_controls_enabled", False)),
        "healthcare_load": (
            "Overloaded"
            if healthcare_load_pct >= 100
            else ("Strained" if healthcare_load_pct >= 70 else "Normal")
        ),
    }
    
def _internal_policy_effects(countrydata):
    approval = clamp(countrydata.get("public_approval", 50))
    corruption = clamp(countrydata.get("corruption_level", 45))
    unrest = clamp(countrydata.get("public_unrest", 25))
    opposition = clamp(countrydata.get("opposition_pressure", 35))
    return {
        "protest_risk": clamp((unrest * 0.55) + (opposition * 0.25) + max(0.0, 45.0 - approval) * 0.35),
        "anti_corruption_swing": clamp(max(0.0, corruption - 35.0) * 1.15),
        "policy_passing_chance": calculate_policy_passing_chance(countrydata),
        "regime_survival_pressure": clamp(max(0.0, 50.0 - approval) + max(0.0, 50.0 - clamp(countrydata.get("government_stability", 50)))),
    }
