import math
from collections import defaultdict

from .economy import (
    canrecruittroops,
    getdefaulteconomyconfig,
    getendturneconomydelta,
    getrecruitcosts,
)
from .events import EngineEventType
from .movement import (
    entrenchmentdefensemultiplier,
    entrenchmentturnrequired,
    findprovincepath,
    getprovincecontroller,
    getprovinceowner,
    markprovincetroopactivity,
)


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
        self.provincetroopsintel = {}
        self.currentturnnumber = 1
        self.countryprovinceindex = {}
        self.countrycoreprovinceindex = {}
        self.countryinvadedprovinceindex = {}
        self.allcountrycache = []
        self.countryaliaslookup = {}

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

        self._initializecountryeconomy()
        self._refreshprovincetroopsintel()
        self.rebuildcountryindexes()

    def setplayercountry(self, playercountry):
        self.playercountry = playercountry
        self._initializecountryeconomy()

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
        countryset = set()
        controlledindex = defaultdict(list)
        coreindex = defaultdict(list)
        invadedindex = defaultdict(list)

        for provinceid, province in self.provincemap.items():
            controllercountry = getprovincecontroller(province)
            ownercountry = getprovinceowner(province)

            if controllercountry:
                countryset.add(controllercountry)
                controlledindex[controllercountry].append(provinceid)
            if ownercountry:
                countryset.add(ownercountry)
            if controllercountry and ownercountry and controllercountry == ownercountry:
                coreindex[controllercountry].append(provinceid)
            elif ownercountry and controllercountry != ownercountry:
                invadedindex[ownercountry].append(provinceid)

        self.allcountrycache = sorted(countryset)
        self.countryprovinceindex = {country: sorted(ids) for country, ids in controlledindex.items()}
        self.countrycoreprovinceindex = {country: sorted(ids) for country, ids in coreindex.items()}
        self.countryinvadedprovinceindex = {country: sorted(ids) for country, ids in invadedindex.items()}
        self.countryaliaslookup = {
            str(country).strip().lower(): str(country).strip()
            for country in self.allcountrycache
            if str(country).strip()
        }

    def _normalizewarpair(self, firstcountry, secondcountry):
        if not firstcountry or not secondcountry:
            return None

        first = self._canonicalizecountry(firstcountry)
        second = self._canonicalizecountry(secondcountry)
        if not first or not second:
            return None
        if first == second:
            return None
        if first <= second:
            return (first, second)
        return (second, first)

    def _canonicalizecountry(self, countryname):
        if countryname is None:
            return None

        countrytext = str(countryname).strip()
        if not countrytext:
            return None

        if not self.countryaliaslookup:
            self.rebuildcountryindexes()
        return self.countryaliaslookup.get(countrytext.lower(), countrytext)

    def executeturn(self, movementorderlist, turnnumber, developmentmode=False):
        # Keep signature compatibility; NPC behavior ignores development mode.
        _ = developmentmode
        if movementorderlist is None:
            movementorderlist = []

        self.currentturnnumber = int(turnnumber)

        self.rebuildcountryindexes()
        self._initializecountryeconomy()
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

            self._applycountryeconomy(countryname, controlledprovinceids)

            recruited = self._recruittroops(countryname, turnnumber)
            if recruited:
                summary["recruits"] += 1

            defenseorders = self._reacttoinvasion(countryname, movementorderlist, turnnumber)
            invasionorders = self._invadecountry(countryname, movementorderlist, turnnumber)
            idleborderorders = 0
            if not set(self.warlookup.get(countryname, set())):
                idleborderorders = self._buildupborderforceswhenidle(
                    countryname,
                    movementorderlist,
                    turnnumber,
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
        if not self.allcountrycache:
            self.rebuildcountryindexes()
        return list(self.allcountrycache)

    def _initializecountryeconomy(self):
        startinggold = int(self.economyconfig.get("startinggold", 0))
        startingpopulation = int(self.economyconfig.get("startingpopulation", 0))

        for countryname in self._allcountries():
            if countryname not in self.countryeconomy:
                self.countryeconomy[countryname] = {
                    "gold": startinggold,
                    "population": startingpopulation,
                }

    def _npcountries(self):
        allcountries = self._allcountries()
        if not self.playercountry:
            return allcountries
        return [countryname for countryname in allcountries if countryname != self.playercountry]

    def _controlledprovinceids(self, countryname):
        if not self.countryprovinceindex and self.provincemap:
            self.rebuildcountryindexes()
        return list(self.countryprovinceindex.get(countryname, ()))

    def _corecontrolledprovinceids(self, countryname):
        if not self.countrycoreprovinceindex and self.provincemap:
            self.rebuildcountryindexes()
        return list(self.countrycoreprovinceindex.get(countryname, ()))

    def _invadedprovinceids(self, countryname):
        if not self.countryinvadedprovinceindex and self.provincemap:
            self.rebuildcountryindexes()
        return list(self.countryinvadedprovinceindex.get(countryname, ()))

    def _countcontrolledstates(self, controlledprovinceids):
        stateidset = set()
        for provinceid in controlledprovinceids:
            province = self.provincemap.get(provinceid)
            if not province:
                continue

            stateid = province.get("parentstateid") or province.get("parentid")
            if stateid is None:
                continue
            stateidset.add(stateid)

        return len(stateidset)

    def _applycountryeconomy(self, countryname, controlledprovinceids):
        economystate = self.countryeconomy.get(countryname)
        if not economystate:
            return

        controlledprovincecount = len(controlledprovinceids)

        goldincome, populationgrowth = getendturneconomydelta(controlledprovincecount, economyconfig=self.economyconfig)

        controlledstatecount = self._countcontrolledstates(controlledprovinceids)
        extracontrolledstates = max(0, controlledstatecount - 1)
        goldincome += extracontrolledstates * self.npcstategoldbonusperextrastate
        populationgrowth += extracontrolledstates * self.npcstatepopulationbonusperextrastate

        economystate["gold"] += goldincome
        economystate["population"] += populationgrowth

    def _refreshprovincetroopsintel(self):
        self.provincetroopsintel = {
            provinceid: int(province.get("troops", 0))
            for provinceid, province in self.provincemap.items()
        }

    def _getestimateddefenders(self, provinceid):
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

    def _istargetprovinceentrenched(self, provinceid):
        province = self.provincemap.get(provinceid)
        if not province:
            return False
        if int(province.get("troops", 0)) <= 0:
            return False

        lastactivityturn = int(province.get("lasttroopactivityturn", 0))
        entrenchedturns = max(0, int(self.currentturnnumber) - lastactivityturn)
        return entrenchedturns >= entrenchmentturnrequired

    def _frontlineprovinceids(self, countryname, enemycountryset=None):
        frontlineids = set()
        for provinceid in self._controlledprovinceids(countryname):
            for neighborprovinceid in self.provincegraph.get(provinceid, ()): 
                neighborprovince = self.provincemap.get(neighborprovinceid)
                if not neighborprovince:
                    continue

                neighborcountry = getprovincecontroller(neighborprovince)
                if not neighborcountry or neighborcountry == countryname:
                    continue
                if enemycountryset is not None and neighborcountry not in enemycountryset:
                    continue

                frontlineids.add(provinceid)
                break

        return frontlineids

    def _estimateadjacentenemythreat(self, countryname, provinceid, enemycountryset=None):
        threatvalue = 0
        for neighborprovinceid in self.provincegraph.get(provinceid, ()): 
            neighborprovince = self.provincemap.get(neighborprovinceid)
            if not neighborprovince:
                continue

            neighborcountry = getprovincecontroller(neighborprovince)
            if not neighborcountry or neighborcountry == countryname:
                continue
            if enemycountryset is not None and neighborcountry not in enemycountryset:
                continue

            threatvalue += self._getestimateddefenders(neighborprovinceid)

        return threatvalue

    def _getfrontlinedesiredtroops(self, countryname, provinceid, enemycountryset=None):
        enemythreat = self._estimateadjacentenemythreat(
            countryname,
            provinceid,
            enemycountryset=enemycountryset,
        )
        recruitamount = int(self.economyconfig.get("recruitamount", 100))
        pressurebuffer = max(2, recruitamount // 10)
        return max(self.minimumgarrison, enemythreat + pressurebuffer)

    def _getfrontlineoffensivebaseline(self, countryname, frontlineprovincecount):
        if frontlineprovincecount <= 0:
            return self.minimumgarrison

        totalcountrytroops = 0
        for provinceid in self._controlledprovinceids(countryname):
            totalcountrytroops += int(self.provincemap[provinceid].get("troops", 0))

        offensivereservetroops = int(totalcountrytroops * self.frontlineoffensivereservefraction)
        return max(self.minimumgarrison, offensivereservetroops // frontlineprovincecount)

    def _pickrecruitprovinceids(self, countryname, maxcount=1):
        if maxcount <= 0:
            return []

        coreprovinceids = self._corecontrolledprovinceids(countryname)
        if not coreprovinceids:
            return []
        coreprovinceidset = set(coreprovinceids)

        warenemyset = set(self.warlookup.get(countryname, set()))
        if warenemyset:
            frontlinecoreprovinceids = [
                provinceid
                for provinceid in sorted(self._frontlineprovinceids(countryname, warenemyset))
                if provinceid in coreprovinceidset
            ]
            candidateprovinceids = frontlinecoreprovinceids if frontlinecoreprovinceids else coreprovinceids
        else:
            peacebordercoreprovinceids = [
                provinceid
                for provinceid in sorted(self._frontlineprovinceids(countryname))
                if provinceid in coreprovinceidset
            ]
            candidateprovinceids = peacebordercoreprovinceids if peacebordercoreprovinceids else coreprovinceids

        candidateprovinceids = sorted(
            candidateprovinceids,
            key=lambda provinceid: (
                int(self.provincemap[provinceid].get("troops", 0)),
                provinceid,
            ),
        )
        return candidateprovinceids[:maxcount]

    def _pickrecruitprovince(self, countryname):
        targetprovinceids = self._pickrecruitprovinceids(countryname, maxcount=1)
        if not targetprovinceids:
            return None

        return targetprovinceids[0]

    def _recruittroops(self, countryname, turnnumber):
        targetprovinceids = self._pickrecruitprovinceids(countryname, maxcount=self.npcrecruitslotsperturn)
        if not targetprovinceids:
            return False

        economystate = self.countryeconomy.get(countryname)
        if not economystate:
            return False

        recruitamount = int(self.economyconfig.get("recruitamount", 100))
        recruitgoldcostperunit = int(self.economyconfig.get("recruitgoldcostperunit", 1))
        recruitpopulationcostperunit = int(self.economyconfig.get("recruitpopulationcostperunit", 1))
        recruitslotcount = max(1, min(len(targetprovinceids), int(self.npcrecruitslotsperturn)))
        perprovincebase = recruitamount // recruitslotcount
        remainder = recruitamount % recruitslotcount

        recruitedany = False
        for recruitindex, targetprovinceid in enumerate(targetprovinceids[:recruitslotcount]):
            provinceamount = perprovincebase + (1 if recruitindex < remainder else 0)
            if provinceamount <= 0:
                continue

            basegoldcost, basepopulationcost = getrecruitcosts(
                provinceamount,
                recruitgoldcostperunit,
                recruitpopulationcostperunit,
            )
            requiredgold = max(1, int(round(basegoldcost * self.npcrecruitgoldcostmultiplier)))
            requiredpopulation = max(1, int(round(basepopulationcost * self.npcrecruitpopulationcostmultiplier)))

            if not canrecruittroops(
                economystate.get("gold", 0),
                economystate.get("population", 0),
                requiredgold,
                requiredpopulation,
            ):
                continue

            self.provincemap[targetprovinceid]["troops"] += provinceamount
            markprovincetroopactivity(self.provincemap[targetprovinceid], turnnumber)
            economystate["gold"] -= requiredgold
            economystate["population"] -= requiredpopulation

            self._emit(
                EngineEventType.TROOPSRECRUITED,
                {
                    "country": countryname,
                    "provinceId": targetprovinceid,
                    "amount": provinceamount,
                    "turn": turnnumber,
                    "isNpc": True,
                },
            )
            recruitedany = True

        return recruitedany

    def _findshortestpathtotarget(self, sourceprovinceid, targetprovinceids, allowedprovinceidset):
        bestpath = []
        bestpathlength = None
        besttargetid = None

        for targetprovinceid in sorted(targetprovinceids):
            path = findprovincepath(
                sourceprovinceid,
                targetprovinceid,
                self.provincemap,
                self.provincegraph,
                allowedprovinceidset=allowedprovinceidset,
            )
            if len(path) < 2:
                continue

            pathlength = len(path)
            if bestpathlength is None or pathlength < bestpathlength:
                bestpath = path
                bestpathlength = pathlength
                besttargetid = targetprovinceid

        return besttargetid, bestpath

    def _appendmovementorder(self, movementorderlist, countryname, sourceprovinceid, path, troopcount, turnnumber):
        sourceprovince = self.provincemap[sourceprovinceid]
        movementorderlist.append(
            {
                "amount": troopcount,
                "path": path,
                "index": 0,
                "current": path[0],
                "speedmodifier": 1.0,
                "controllercountry": countryname,
                "country": countryname,
                "countrycolor": sourceprovince.get("countrycolor", self.countrytocolorlookup.get(countryname)),
                "ordercreatedturn": turnnumber,
            }
        )

        self._emit(
            EngineEventType.MOVEORDERCREATED,
            {
                "sourceProvinceId": sourceprovinceid,
                "destinationProvinceId": path[-1],
                "path": list(path),
                "troops": troopcount,
                "country": countryname,
                "turn": turnnumber,
                "isNpc": True,
            },
        )

    def _movereservestotargets(self, countryname, targetprovinceids, movementorderlist, turnnumber, maxorders):
        if not targetprovinceids:
            return 0

        controlledprovinceidset = set(self._controlledprovinceids(countryname))
        if not controlledprovinceidset:
            return 0

        targetprovinceidset = set(targetprovinceids)
        sourceprovinceids = sorted(
            controlledprovinceidset,
            key=lambda provinceid: int(self.provincemap[provinceid].get("troops", 0)),
            reverse=True,
        )
        if not sourceprovinceids:
            return 0

        enemycountryset = set(self.warlookup.get(countryname, set()))
        offensivebaseline = self._getfrontlineoffensivebaseline(countryname, len(targetprovinceidset))
        targetdesiredlookup = {
            provinceid: max(
                self._getfrontlinedesiredtroops(
                    countryname,
                    provinceid,
                    enemycountryset=enemycountryset,
                ),
                offensivebaseline,
            )
            for provinceid in targetprovinceidset
        }
        incominglookup = {provinceid: 0 for provinceid in targetprovinceidset}

        dynamicmaxorders = max(maxorders, len(targetprovinceidset) * 3)
        orderscreated = 0
        for sourceprovinceid in sourceprovinceids:
            if orderscreated >= dynamicmaxorders:
                break

            sourceprovince = self.provincemap[sourceprovinceid]
            while orderscreated < dynamicmaxorders:
                sourcetroops = int(sourceprovince.get("troops", 0))
                if sourceprovinceid in targetdesiredlookup:
                    minholdingtroops = max(self.minimumgarrison, targetdesiredlookup[sourceprovinceid])
                else:
                    minholdingtroops = self.minimumgarrison

                movabletroops = sourcetroops - minholdingtroops
                if movabletroops <= 0:
                    break

                besttargetid = None
                besttargetpath = []
                besttargetscore = None

                for targetprovinceid in sorted(targetprovinceidset):
                    if targetprovinceid == sourceprovinceid:
                        continue

                    projectedtroops = int(self.provincemap[targetprovinceid].get("troops", 0)) + incominglookup[targetprovinceid]
                    targetdeficit = targetdesiredlookup[targetprovinceid] - projectedtroops
                    if targetdeficit <= 0:
                        continue

                    path = findprovincepath(
                        sourceprovinceid,
                        targetprovinceid,
                        self.provincemap,
                        self.provincegraph,
                        allowedprovinceidset=controlledprovinceidset,
                    )
                    if len(path) < 2:
                        continue

                    targetscore = (targetdeficit * 100) - len(path)
                    if besttargetscore is None or targetscore > besttargetscore:
                        besttargetid = targetprovinceid
                        besttargetpath = path
                        besttargetscore = targetscore

                if besttargetid is None or len(besttargetpath) < 2:
                    break

                projectedtroops = int(self.provincemap[besttargetid].get("troops", 0)) + incominglookup[besttargetid]
                targetdeficit = targetdesiredlookup[besttargetid] - projectedtroops
                movecount = min(movabletroops, max(1, targetdeficit))
                if movecount <= 0:
                    break

                sourceprovince["troops"] -= movecount
                markprovincetroopactivity(sourceprovince, turnnumber)
                self._appendmovementorder(
                    movementorderlist,
                    countryname,
                    sourceprovinceid,
                    besttargetpath,
                    movecount,
                    turnnumber,
                )
                incominglookup[besttargetid] += movecount
                orderscreated += 1

        return orderscreated

    def _buildupborderforceswhenidle(self, countryname, movementorderlist, turnnumber):
        borderprovinceids = sorted(self._frontlineprovinceids(countryname))
        if not borderprovinceids:
            return 0

        maxidleorders = max(2, min(10, len(borderprovinceids) * 2))
        return self._movereservestotargets(
            countryname,
            borderprovinceids,
            movementorderlist,
            turnnumber,
            maxorders=maxidleorders,
        )

    def _reacttoinvasion(self, countryname, movementorderlist, turnnumber):
        warenemyset = set(self.warlookup.get(countryname, set()))
        if not warenemyset:
            return 0

        invadedprovinceids = self._invadedprovinceids(countryname)
        if invadedprovinceids:
            invadercountryset = set()
            for provinceid in invadedprovinceids:
                province = self.provincemap.get(provinceid)
                if not province:
                    continue
                controllercountry = getprovincecontroller(province)
                if controllercountry and controllercountry != countryname:
                    invadercountryset.add(controllercountry)

            targetfrontlineids = self._frontlineprovinceids(countryname, invadercountryset)
            if not targetfrontlineids:
                targetfrontlineids = self._frontlineprovinceids(countryname, warenemyset)
        else:
            targetfrontlineids = self._frontlineprovinceids(countryname, warenemyset)

        if not targetfrontlineids:
            return 0

        return self._movereservestotargets(
            countryname,
            targetfrontlineids,
            movementorderlist,
            turnnumber,
            maxorders=self.maxdefenseordersperturn,
        )

    def _enemybordertargetids(self, countryname, enemycountry):
        targetids = set()
        for provinceid in self._controlledprovinceids(countryname):
            for neighborprovinceid in self.provincegraph.get(provinceid, ()): 
                neighborprovince = self.provincemap.get(neighborprovinceid)
                if not neighborprovince:
                    continue
                if getprovincecontroller(neighborprovince) == enemycountry:
                    targetids.add(neighborprovinceid)

        return sorted(targetids)

    def _getcountrystrengthscore(self, countryname):
        controlledprovinceids = self._controlledprovinceids(countryname)
        if not controlledprovinceids:
            return 0

        controlledtroops = sum(
            int(self.provincemap[provinceid].get("troops", 0))
            for provinceid in controlledprovinceids
        )
        controlledstatecount = self._countcontrolledstates(controlledprovinceids)

        provinceweight = max(2, self.minimumgarrison // 2)
        stateweight = max(6, self.minimumgarrison)
        return (
            controlledtroops
            + (len(controlledprovinceids) * provinceweight)
            + (controlledstatecount * stateweight)
        )

    def _buildattackplans(self, countryname, enemycountry, targetprovinceid):
        allowedprovinceidset = {
            provinceid
            for provinceid, province in self.provincemap.items()
            if getprovincecontroller(province) in {countryname, enemycountry}
        }

        attackplanlist = []
        for sourceprovinceid in self._controlledprovinceids(countryname):
            sourceprovince = self.provincemap[sourceprovinceid]
            sourcetroops = int(sourceprovince.get("troops", 0))
            movabletroops = sourcetroops - self.invasiongarrison
            if movabletroops <= 0:
                continue

            path = findprovincepath(
                sourceprovinceid,
                targetprovinceid,
                self.provincemap,
                self.provincegraph,
                allowedprovinceidset=allowedprovinceidset,
            )
            if len(path) < 2:
                continue

            attackplanlist.append(
                {
                    "sourceProvinceId": sourceprovinceid,
                    "path": path,
                    "troops": movabletroops,
                }
            )

        attackplanlist.sort(
            key=lambda entry: (
                len(entry["path"]),
                -entry["troops"],
                entry["sourceProvinceId"],
            )
        )
        return attackplanlist

    def getenemyaggression(self, countryname, enemycountry):
        attackerstrength = float(self._getcountrystrengthscore(countryname))
        enemystrength = float(self._getcountrystrengthscore(enemycountry))
        strengthratio = (attackerstrength + 1.0) / (enemystrength + 1.0)
        return max(1.0, min(2.2, strengthratio))

    def getenemyinvasionlimits(self, warenemycount, enemyaggression):
        totalorderlimit = max(
            self.maxinvasionordersperturn * max(1, warenemycount),
            warenemycount * max(2, self.maxinvasiontargetsperenemy) * 3,
        )
        enemyorderlimit = max(2, int(self.maxinvasionordersperturn * enemyaggression))
        return totalorderlimit, enemyorderlimit

    def gettargetcountlimit(self, targetprovinceids, enemyaggression):
        return max(
            self.maxinvasiontargetsperenemy,
            min(
                len(targetprovinceids),
                max(2, int(len(targetprovinceids) * (0.55 + 0.35 * enemyaggression))),
            ),
        )

    def shouldskipattritionattack(
        self,
        totalattackers,
        defendercount,
        enemyaggression,
        targetisentrenched,
    ):
        effectiveattritionthreshold = max(
            0.45,
            self.attritionattackthresholdratio - ((enemyaggression - 1.0) * 0.25),
        )
        if targetisentrenched:
            # entrenched defenders are harder to dislodge; allow attrition attacks to start earlier
            effectiveattritionthreshold = max(0.35, effectiveattritionthreshold - 0.12)
        minimumattritionforce = max(1, int(defendercount * effectiveattritionthreshold))
        return totalattackers < minimumattritionforce

    def getassaulttroopgoal(
        self,
        totalattackers,
        defendercount,
        enemyaggression,
        targetisentrenched,
        hasfreshdefenderdrop,
    ):
        cancapture = totalattackers > defendercount
        bonuscapturecommitratio = 1.0 + max(0.0, min(0.65, (enemyaggression - 1.0) * 0.4))
        if cancapture:
            troopssendneeded = max(
                defendercount + 1,
                int(defendercount * bonuscapturecommitratio) + 1,
            )
            return min(totalattackers, max(1, troopssendneeded))

        # If current defenders dropped far below previous intel this turn,
        # avoid instant opportunistic attrition attacks; require capture-level force.
        if hasfreshdefenderdrop:
            return None
        if self.shouldskipattritionattack(totalattackers, defendercount, enemyaggression, targetisentrenched):
            return None

        effectivecommitratio = min(
            1.35,
            self.attritionattackcommitratio + ((enemyaggression - 1.0) * 0.2),
        )
        if targetisentrenched:
            effectivecommitratio = min(1.5, effectivecommitratio + 0.12)
        targetassaultforce = max(1, int(defendercount * effectivecommitratio))
        troopssendneeded = min(totalattackers, targetassaultforce)
        return min(totalattackers, max(1, troopssendneeded))

    def getattackwavesize(self, defendercount, enemyaggression):
        recruitamount = int(self.economyconfig.get("recruitamount", 100))
        return max(
            1,
            int(max(recruitamount // 2, defendercount * (0.35 + (enemyaggression - 1.0) * 0.15))),
        )

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
        wavesizebase = self.getattackwavesize(defendercount, enemyaggression)
        for attackplan in attackplanlist:
            if (
                orderscreated >= invasionorderlimit
                or enemyorderscreated >= enemyorderlimit
                or troopssendneeded <= 0
            ):
                break

            sourceprovinceid = attackplan["sourceProvinceId"]
            sourceprovince = self.provincemap[sourceprovinceid]
            sourcetroops = int(sourceprovince.get("troops", 0))
            movabletroops = sourcetroops - self.invasiongarrison
            if movabletroops <= 0:
                continue

            movingtroops = min(movabletroops, max(1, min(troopssendneeded, wavesizebase)))
            sourceprovince["troops"] -= movingtroops
            markprovincetroopactivity(sourceprovince, turnnumber)
            self._appendmovementorder(
                movementorderlist,
                countryname,
                sourceprovinceid,
                attackplan["path"],
                movingtroops,
                turnnumber,
            )
            orderscreated += 1
            enemyorderscreated += 1
            troopssendneeded -= movingtroops

        return orderscreated, enemyorderscreated

    def _invadecountry(self, countryname, movementorderlist, turnnumber):
        warenemyset = sorted(set(self.warlookup.get(countryname, set())))
        if not warenemyset:
            return 0

        orderscreated = 0
        for enemycountry in warenemyset:
            enemyaggression = self.getenemyaggression(countryname, enemycountry)
            invasionorderlimit, enemyorderlimit = self.getenemyinvasionlimits(len(warenemyset), enemyaggression)
            if orderscreated >= invasionorderlimit:
                break
            enemyorderscreated = 0

            targetprovinceids = self._enemybordertargetids(countryname, enemycountry)
            if not targetprovinceids:
                continue

            targetcountlimit = self.gettargetcountlimit(targetprovinceids, enemyaggression)

            prioritizedtargetids = sorted(
                targetprovinceids,
                key=lambda provinceid: (
                    self._getestimateddefenders(provinceid),
                    provinceid,
                ),
            )[:targetcountlimit]

            for targetprovinceid in prioritizedtargetids:
                if orderscreated >= invasionorderlimit or enemyorderscreated >= enemyorderlimit:
                    break

                attackplanlist = self._buildattackplans(countryname, enemycountry, targetprovinceid)
                if not attackplanlist:
                    continue

                defendercount = self._getestimateddefenders(targetprovinceid)
                targetisentrenched = self._istargetprovinceentrenched(targetprovinceid)
                currentdefendercount = int(self.provincemap[targetprovinceid].get("troops", 0))
                previousrawdefendercount = int(self.provincetroopsintel.get(targetprovinceid, currentdefendercount))
                hasfreshdefenderdrop = currentdefendercount < previousrawdefendercount
                totalattackers = sum(plan["troops"] for plan in attackplanlist)

                troopssendneeded = self.getassaulttroopgoal(
                    totalattackers,
                    defendercount,
                    enemyaggression,
                    targetisentrenched,
                    hasfreshdefenderdrop,
                )
                if troopssendneeded is None:
                    continue
                orderscreated, enemyorderscreated = self.issueattackwaves(
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

        return orderscreated

    def _emit(self, eventname, payload):
        if callable(self.emit):
            self.emit(eventname, payload)
