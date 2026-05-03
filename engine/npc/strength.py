import math

from ..movement import entrenchmentdefensemultiplier, entrenchmentturnrequired


class NpcStrengthEvaluator:
    def __init__(self, provincemap, economyconfig, countryindex, minimumgarrison):
        self.provincemap = provincemap if provincemap is not None else {}
        self.economyconfig = economyconfig
        self.countryindex = countryindex
        self.minimumgarrison = minimumgarrison
        self.currentturnnumber = 1
        self.provincetroopsintel = {}
        self.countrystrengthcache = {}

    def setturnnumber(self, turnnumber):
        self.currentturnnumber = int(turnnumber)

    def clearcache(self):
        self.countrystrengthcache = {}

    def refreshintel(self):
        self.provincetroopsintel = {
            provinceid: int(province.get("troops", 0))
            for provinceid, province in self.provincemap.items()
        }

    def estimateddefenders(self, provinceid):
        if provinceid in self.provincetroopsintel:
            basecount = int(self.provincetroopsintel[provinceid])
        else:
            province = self.provincemap.get(provinceid)
            if not province:
                return 0
            basecount = int(province.get("troops", 0))

        province = self.provincemap.get(provinceid)
        if not province:
            return basecount

        lastactivityturn = int(province.get("lasttroopactivityturn", 0))
        entrenchedturns = max(0, int(self.currentturnnumber) - lastactivityturn)
        if basecount > 0 and entrenchedturns >= entrenchmentturnrequired:
            return int(math.ceil(basecount * entrenchmentdefensemultiplier))

        return basecount

    def targetentrenched(self, provinceid):
        province = self.provincemap.get(provinceid)
        if not province:
            return False
        if int(province.get("troops", 0)) <= 0:
            return False

        lastactivityturn = int(province.get("lasttroopactivityturn", 0))
        entrenchedturns = max(0, int(self.currentturnnumber) - lastactivityturn)
        return entrenchedturns >= entrenchmentturnrequired

    def countrystrengthscore(self, countryname):
        if countryname in self.countrystrengthcache:
            return int(self.countrystrengthcache[countryname])

        controlledprovincecount = int(self.countryindex.countryprovincecountindex.get(countryname, 0))
        if controlledprovincecount <= 0:
            return 0

        provinceweight = max(2, self.minimumgarrison // 2)
        stateweight = max(6, self.minimumgarrison)
        return (
            int(self.countryindex.countrytroopcountindex.get(countryname, 0))
            + (controlledprovincecount * provinceweight)
            + (int(self.countryindex.countrystatecountindex.get(countryname, 0)) * stateweight)
        )



    # TODO: add more complex strength evaluation logic here, such as adjusting strength based on the strategic value of controlled provinces or states, or based on personality traits or current war status. Also consider adding logic for estimating the strength of enemy countries based on observed troop movements or other intel, and adjusting aggression or defensive priorities accordingly.
    # THIS IS FOR CALCULATING A COUNTRY'S OVERALL STRENGTH SCORE, NOT FOR PLANNING MOVEMENT OR RECRUITMENT PRIORITIES!! MOVEMENT PLANNING SHOULD GO IN NPCDEFENSEPLANNER OR NPCINVASIONPLANNER AND RECRUITMENT PLANNING SHOULD GO IN NPCECONOMYPLANNER
    def rebuild(self):
        # eso: derive strength from cached country totals.
        provinceweight = max(2, self.minimumgarrison // 2)
        stateweight = max(6, self.minimumgarrison)
        strengthcache = {}

        for countryname in self.countryindex.allcountries():
            controlledprovincecount = int(self.countryindex.countryprovincecountindex.get(countryname, 0))
            if controlledprovincecount <= 0:
                strengthcache[countryname] = 0
                continue

            controlledtroops = int(self.countryindex.countrytroopcountindex.get(countryname, 0))
            controlledstatecount = int(self.countryindex.countrystatecountindex.get(countryname, 0))
            strengthcache[countryname] = (
                controlledtroops
                + (controlledprovincecount * provinceweight)
                + (controlledstatecount * stateweight)
            )

        self.countrystrengthcache = strengthcache

    def enemyaggression(self, countryname, enemycountry, personality=None):
        attackerstrength = float(self.countrystrengthscore(countryname))
        enemystrength = float(self.countrystrengthscore(enemycountry))
        strengthratio = (attackerstrength + 1.0) / (enemystrength + 1.0)
        personalityaggression = getattr(personality, "aggression", 1.0) if personality else 1.0
        return max(1.0, min(2.2, strengthratio * personalityaggression))
