from collections import defaultdict

from .economy import getdefaulteconomyconfig
from .npcactions import NpcTurnActions
from .npcdefense import NpcDefensePlanner
from .npceconomy import NpcEconomyPlanner
from .npcindex import NpcCountryIndex, NpcWorldIndex
from .npcinvasion import NpcInvasionPlanner
from .npcpersonality import NpcPersonality
from .npcstrength import NpcStrengthEvaluator


class NpcDirector:
    def __init__(
        self,
        provincemap,
        provincegraph,
        countrytocolorlookup=None,
        emit=None,
        economyconfig=None,
    ):
        self.provincemap = provincemap if provincemap is not None else {}
        self.provincegraph = provincegraph if provincegraph is not None else {}
        self.countrytocolorlookup = countrytocolorlookup if countrytocolorlookup is not None else {}
        self.emit = emit

        self.economyconfig = dict(economyconfig or getdefaulteconomyconfig())
        self.playercountry = None
        self.countriesatwarset = set()
        self.warpairset = set()
        self.warlookup = defaultdict(set)
        self.countryeconomy = {}
        self.currentturnnumber = 1

        self.minimumgarrison = max(5, int(self.economyconfig.get("recruitamount", 100) // 4))
        self.maxdefenseordersperturn = 4
        self.maxinvasionordersperturn = 6
        self.maxinvasiontargetsperenemy = 2
        self.npcrecruitslotsperturn = max(
            1,
            int(self.economyconfig.get("npcrecruitslotsperturn", 2)),
        )
        self.invasiongarrison = max(3, self.minimumgarrison // 2)
        self.frontlineoffensivereservefraction = max(
            0.15,
            min(0.9, float(self.economyconfig.get("npcfrontlineoffensivereservefraction", 0.45))),
        )
        self.attritionattackthresholdratio = 0.8
        self.attritionattackcommitratio = 0.9
        self.npcrecruitgoldcostmultiplier = max(
            0.1,
            float(self.economyconfig.get("npcrecruitgoldcostmultiplier", 1.0)),
        )
        self.npcrecruitpopulationcostmultiplier = max(
            0.05,
            float(self.economyconfig.get("npcrecruitpopulationcostmultiplier", 0.25)),
        )
        self.npcstategoldbonusperextrastate = max(
            0,
            int(self.economyconfig.get("npcstategoldbonusperextrastate", 1)),
        )
        self.npcstatepopulationbonusperextrastate = max(
            0,
            int(self.economyconfig.get("npcstatepopulationbonusperextrastate", 2)),
        )

        self.defaultpersonality = NpcPersonality.default()
        self.countrypersonalitylookup = {}

        self.countryindex = NpcCountryIndex(self.provincemap, self.provincegraph)
        self.worldindex = self.countryindex
        self.actionwriter = NpcTurnActions(
            self.provincemap,
            self.countrytocolorlookup,
            self.countryindex,
            emit=self.emit,
        )
        self.strengthevaluator = NpcStrengthEvaluator(
            self.provincemap,
            self.economyconfig,
            self.countryindex,
            self.minimumgarrison,
        )
        self.economyplanner = NpcEconomyPlanner(
            self.provincemap,
            self.economyconfig,
            self.countryindex,
            self.actionwriter,
            self.npcrecruitslotsperturn,
            self.npcrecruitgoldcostmultiplier,
            self.npcrecruitpopulationcostmultiplier,
            self.npcstategoldbonusperextrastate,
            self.npcstatepopulationbonusperextrastate,
        )
        self.defenseplanner = NpcDefensePlanner(
            self.provincemap,
            self.provincegraph,
            self.economyconfig,
            self.countryindex,
            self.strengthevaluator,
            self.actionwriter,
            self.minimumgarrison,
            self.maxdefenseordersperturn,
            self.frontlineoffensivereservefraction,
        )
        self.invasionplanner = NpcInvasionPlanner(
            self.provincemap,
            self.provincegraph,
            self.economyconfig,
            self.countryindex,
            self.strengthevaluator,
            self.actionwriter,
            self.invasiongarrison,
            self.maxinvasionordersperturn,
            self.maxinvasiontargetsperenemy,
            self.attritionattackthresholdratio,
            self.attritionattackcommitratio,
        )

        self._syncindexaliases()
        self._syncstrengthaliases()
        self._initializecountryeconomy()
        self._refreshprovincetroopsintel()
        self.rebuildcountryindexes()

    def _syncindexaliases(self):
        self.countryprovinceindex = self.countryindex.countryprovinceindex
        self.countrycoreprovinceindex = self.countryindex.countrycoreprovinceindex
        self.countryinvadedprovinceindex = self.countryindex.countryinvadedprovinceindex
        self.countryprovincecountindex = self.countryindex.countryprovincecountindex
        self.countrytroopcountindex = self.countryindex.countrytroopcountindex
        self.countrystatecountindex = self.countryindex.countrystatecountindex
        self.countryfrontlineallindex = self.countryindex.countryfrontlineallindex
        self.countryfrontlineenemyindex = self.countryindex.countryfrontlineenemyindex
        self.countryenemybordertargetindex = self.countryindex.countryenemybordertargetindex
        self.allcountrycache = self.countryindex.allcountrycache
        self.countryaliaslookup = self.countryindex.countryaliaslookup

    def _syncstrengthaliases(self):
        self.provincetroopsintel = self.strengthevaluator.provincetroopsintel
        self.countrystrengthcache = self.strengthevaluator.countrystrengthcache

    def setplayercountry(self, playercountry):
        self.playercountry = playercountry
        self._initializecountryeconomy()

    def setcountrypersonality(self, countryname, personality):
        canonicalcountry = self._canonicalizecountry(countryname)
        if not canonicalcountry:
            return False
        if personality is None:
            self.countrypersonalitylookup.pop(canonicalcountry, None)
            return True
        if not isinstance(personality, NpcPersonality):
            return False
        self.countrypersonalitylookup[canonicalcountry] = personality
        return True

    def getpersonality(self, countryname):
        # todo: focus tree choices can override or adjust this personality later.
        canonicalcountry = self._canonicalizecountry(countryname)
        return self.countrypersonalitylookup.get(canonicalcountry, self.defaultpersonality)

    def sync_player_wars(self, playercountry, countriesatwarset, warpairset=None):
        self.playercountry = playercountry
        self.countriesatwarset = set(countriesatwarset or ())

        if warpairset is None:
            normalizedwarpairs = set()
            if playercountry:
                for enemycountry in self.countriesatwarset:
                    if not enemycountry or enemycountry == playercountry:
                        continue
                    normalizedwarpairs.add(self._normalizewarpair(playercountry, enemycountry))
            self.warpairset = normalizedwarpairs
        else:
            normalizedwarpairs = set()
            for warpair in warpairset:
                if not isinstance(warpair, (tuple, list)) or len(warpair) != 2:
                    continue
                firstcountry, secondcountry = warpair
                normalizedpair = self._normalizewarpair(firstcountry, secondcountry)
                if normalizedpair is None:
                    continue
                normalizedwarpairs.add(normalizedpair)

            if playercountry:
                for enemycountry in self.countriesatwarset:
                    normalizedpair = self._normalizewarpair(playercountry, enemycountry)
                    if normalizedpair is not None:
                        normalizedwarpairs.add(normalizedpair)

            self.warpairset = normalizedwarpairs

        self.warlookup = defaultdict(set)
        for firstcountry, secondcountry in self.warpairset:
            self.warlookup[firstcountry].add(secondcountry)
            self.warlookup[secondcountry].add(firstcountry)

    def rebuildcountryindexes(self):
        self.countryindex.rebuild()
        self._syncindexaliases()
        self.strengthevaluator.clearcache()
        self._syncstrengthaliases()

    def _normalizewarpair(self, firstcountry, secondcountry):
        normalizedpair = self.countryindex.normalizewarpair(firstcountry, secondcountry)
        self._syncindexaliases()
        return normalizedpair

    def _canonicalizecountry(self, countryname):
        canonicalcountry = self.countryindex.canonicalizecountry(countryname)
        self._syncindexaliases()
        return canonicalcountry

    def executeturn(self, movementorderlist, turnnumber, developmentmode=False):
        # keep signature compatibility; npc behavior ignores development mode.
        _ = developmentmode
        if movementorderlist is None:
            movementorderlist = []

        self.currentturnnumber = int(turnnumber)
        self.strengthevaluator.setturnnumber(turnnumber)
        self.actionwriter.setemit(self.emit)

        # eso: build indexes up front so planners reuse cached country data.
        self.rebuildcountryindexes()
        self._initializecountryeconomy()
        self._rebuildcountrystrengthcache()
        summary = {
            "countriesProcessed": 0,
            "recruits": 0,
            "defenseOrders": 0,
            "invasionOrders": 0,
            "idleBorderOrders": 0,
            "ordersCreated": 0,
        }

        for countryname in self._npcountries():
            controlledprovinceids = self._controlledprovinceids(countryname)
            if not controlledprovinceids:
                continue

            summary["countriesProcessed"] += 1
            personality = self.getpersonality(countryname)

            # todo: route npc focus tree decisions into these planner calls later.
            self.economyplanner.applycountryeconomy(
                self.countryeconomy,
                countryname,
                controlledprovinceids,
                personality=personality,
            )

            recruited = self.economyplanner.recruittroops(
                self.countryeconomy,
                countryname,
                self.warlookup,
                turnnumber,
                personality=personality,
            )
            if recruited:
                summary["recruits"] += 1

            defenseorders = self.defenseplanner.reacttoinvasion(
                countryname,
                self.warlookup,
                movementorderlist,
                turnnumber,
                personality=personality,
            )
            invasionorders = self.invasionplanner.invadecountry(
                countryname,
                self.warlookup,
                movementorderlist,
                turnnumber,
                personality=personality,
            )
            idleborderorders = 0
            if not set(self.warlookup.get(countryname, set())):
                idleborderorders = self.defenseplanner.buildupborderforceswhenidle(
                    countryname,
                    self.warlookup,
                    movementorderlist,
                    turnnumber,
                    personality=personality,
                )

            summary["defenseOrders"] += defenseorders
            summary["invasionOrders"] += invasionorders
            summary["idleBorderOrders"] += idleborderorders

        summary["ordersCreated"] = (
            summary["defenseOrders"]
            + summary["invasionOrders"]
            + summary["idleBorderOrders"]
        )
        self._refreshprovincetroopsintel()
        return summary

    def _allcountries(self):
        countries = self.countryindex.allcountries()
        self._syncindexaliases()
        return countries

    def _initializecountryeconomy(self):
        self.economyplanner.initializecountryeconomy(self.countryeconomy)

    def _npcountries(self):
        allcountries = self._allcountries()
        if not self.playercountry:
            return allcountries
        return [countryname for countryname in allcountries if countryname != self.playercountry]

    def _controlledprovinceids(self, countryname):
        provinceids = self.countryindex.controlledprovinceids(countryname)
        self._syncindexaliases()
        return provinceids

    def _corecontrolledprovinceids(self, countryname):
        provinceids = self.countryindex.corecontrolledprovinceids(countryname)
        self._syncindexaliases()
        return provinceids

    def _invadedprovinceids(self, countryname):
        provinceids = self.countryindex.invadedprovinceids(countryname)
        self._syncindexaliases()
        return provinceids

    def _countcontrolledstates(self, controlledprovinceids):
        return self.economyplanner.countcontrolledstates(controlledprovinceids)

    def _applycountryeconomy(self, countryname, controlledprovinceids):
        self.economyplanner.applycountryeconomy(
            self.countryeconomy,
            countryname,
            controlledprovinceids,
            personality=self.getpersonality(countryname),
        )

    def _refreshprovincetroopsintel(self):
        self.strengthevaluator.refreshintel()
        self._syncstrengthaliases()

    def _getestimateddefenders(self, provinceid):
        return self.strengthevaluator.estimateddefenders(provinceid)

    def _istargetprovinceentrenched(self, provinceid):
        return self.strengthevaluator.targetentrenched(provinceid)

    def _frontlineprovinceids(self, countryname, enemycountryset=None):
        return self.countryindex.frontlineprovinceids(countryname, enemycountryset=enemycountryset)

    def _estimateadjacentenemythreat(self, countryname, provinceid, enemycountryset=None):
        return self.defenseplanner.estimateadjacentenemythreat(
            countryname,
            provinceid,
            enemycountryset=enemycountryset,
        )

    def _getfrontlinedesiredtroops(self, countryname, provinceid, enemycountryset=None):
        return self.defenseplanner.frontlinedesiredtroops(
            countryname,
            provinceid,
            enemycountryset=enemycountryset,
        )

    def _getfrontlineoffensivebaseline(self, countryname, frontlineprovincecount):
        return self.defenseplanner.frontlineoffensivebaseline(countryname, frontlineprovincecount)

    def _pickrecruitprovinceids(self, countryname, maxcount=1):
        return self.economyplanner.pickrecruitprovinceids(
            countryname,
            self.warlookup,
            maxcount=maxcount,
            personality=self.getpersonality(countryname),
        )

    def _pickrecruitprovince(self, countryname):
        return self.economyplanner.pickrecruitprovince(
            countryname,
            self.warlookup,
            personality=self.getpersonality(countryname),
        )

    def _recruittroops(self, countryname, turnnumber):
        return self.economyplanner.recruittroops(
            self.countryeconomy,
            countryname,
            self.warlookup,
            turnnumber,
            personality=self.getpersonality(countryname),
        )

    def _findshortestpathtotarget(self, sourceprovinceid, targetprovinceids, allowedprovinceidset):
        return self.defenseplanner.findshortestpathtotarget(
            sourceprovinceid,
            targetprovinceids,
            allowedprovinceidset,
        )

    def _appendmovementorder(self, movementorderlist, countryname, sourceprovinceid, path, troopcount, turnnumber):
        self.actionwriter.appendmovementorder(
            movementorderlist,
            countryname,
            sourceprovinceid,
            path,
            troopcount,
            turnnumber,
        )

    def _movereservestotargets(self, countryname, targetprovinceids, movementorderlist, turnnumber, maxorders):
        return self.defenseplanner.movereservestotargets(
            countryname,
            targetprovinceids,
            self.warlookup,
            movementorderlist,
            turnnumber,
            maxorders,
            personality=self.getpersonality(countryname),
        )

    def _buildupborderforceswhenidle(self, countryname, movementorderlist, turnnumber):
        return self.defenseplanner.buildupborderforceswhenidle(
            countryname,
            self.warlookup,
            movementorderlist,
            turnnumber,
            personality=self.getpersonality(countryname),
        )

    def _reacttoinvasion(self, countryname, movementorderlist, turnnumber):
        return self.defenseplanner.reacttoinvasion(
            countryname,
            self.warlookup,
            movementorderlist,
            turnnumber,
            personality=self.getpersonality(countryname),
        )

    def _enemybordertargetids(self, countryname, enemycountry):
        return self.countryindex.enemybordertargetids(countryname, enemycountry)

    def _getcountrystrengthscore(self, countryname):
        return self.strengthevaluator.countrystrengthscore(countryname)

    def _rebuildcountrystrengthcache(self):
        self.strengthevaluator.rebuild()
        self._syncstrengthaliases()

    def _buildattackplans(self, countryname, sourceprovinceids, targetprovinceid, allowedprovinceidset, pathcache):
        return self.invasionplanner.buildattackplans(
            countryname,
            sourceprovinceids,
            targetprovinceid,
            allowedprovinceidset,
            pathcache,
        )

    def getenemyaggression(self, countryname, enemycountry):
        return self.strengthevaluator.enemyaggression(
            countryname,
            enemycountry,
            personality=self.getpersonality(countryname),
        )

    def getenemyinvasionlimits(self, warenemycount, enemyaggression):
        return self.invasionplanner.enemyinvasionlimits(warenemycount, enemyaggression)

    def gettargetcountlimit(self, targetprovinceids, enemyaggression):
        return self.invasionplanner.targetcountlimit(targetprovinceids, enemyaggression)

    def shouldskipattritionattack(
        self,
        totalattackers,
        defendercount,
        enemyaggression,
        targetisentrenched,
    ):
        return self.invasionplanner.shouldskipattritionattack(
            totalattackers,
            defendercount,
            enemyaggression,
            targetisentrenched,
        )

    def getassaulttroopgoal(
        self,
        totalattackers,
        defendercount,
        enemyaggression,
        targetisentrenched,
        hasfreshdefenderdrop,
    ):
        return self.invasionplanner.assaulttroopgoal(
            totalattackers,
            defendercount,
            enemyaggression,
            targetisentrenched,
            hasfreshdefenderdrop,
        )

    def getattackwavesize(self, defendercount, enemyaggression):
        return self.invasionplanner.attackwavesize(defendercount, enemyaggression)

    def issueattackwaves(
        self,
        countryname,
        attackplanlist,
        troopssendneeded,
        defendercount,
        enemyaggression,
        movementorderlist,
        turnnumber,
        orderscreated,
        enemyorderscreated,
        invasionorderlimit,
        enemyorderlimit,
    ):
        return self.invasionplanner.issueattackwaves(
            countryname,
            attackplanlist,
            troopssendneeded,
            defendercount,
            enemyaggression,
            movementorderlist,
            turnnumber,
            orderscreated,
            enemyorderscreated,
            invasionorderlimit,
            enemyorderlimit,
        )

    def _invadecountry(self, countryname, movementorderlist, turnnumber):
        return self.invasionplanner.invadecountry(
            countryname,
            self.warlookup,
            movementorderlist,
            turnnumber,
            personality=self.getpersonality(countryname),
        )

    def _emit(self, eventname, payload):
        self.actionwriter.setemit(self.emit)
        self.actionwriter.emit(eventname, payload)
