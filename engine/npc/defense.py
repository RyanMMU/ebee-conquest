from ..movement import findprovincepath, getprovincecontroller

# NPC DEFENSE PLANNER
# defensive troop movement and garrison management for npc countries
class NpcDefensePlanner:
    def __init__(
        self,
        provincemap,
        provincegraph,
        economyconfig,
        countryindex,
        strengthevaluator,
        actionwriter,
        minimumgarrison,
        maxdefenseordersperturn,
        frontlineoffensivereservefraction,
    ):
        self.provincemap = provincemap if provincemap is not None else {}
        self.provincegraph = provincegraph if provincegraph is not None else {}
        self.economyconfig = economyconfig
        self.countryindex = countryindex
        self.strengthevaluator = strengthevaluator
        self.actionwriter = actionwriter
        self.minimumgarrison = minimumgarrison
        self.maxdefenseordersperturn = maxdefenseordersperturn
        self.frontlineoffensivereservefraction = frontlineoffensivereservefraction

    def estimateadjacentenemythreat(self, countryname, provinceid, enemycountryset=None):
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

            threatvalue += self.strengthevaluator.estimateddefenders(neighborprovinceid)

        return threatvalue

    def frontlinedesiredtroops(self, countryname, provinceid, enemycountryset=None):
        enemythreat = self.estimateadjacentenemythreat(
            countryname,
            provinceid,
            enemycountryset=enemycountryset,
        )
        recruitamount = int(self.economyconfig.get("recruitamount", 100))
        pressurebuffer = max(2, recruitamount // 10)
        return max(self.minimumgarrison, enemythreat + pressurebuffer)

    def frontlineoffensivebaseline(self, countryname, frontlineprovincecount):
        if frontlineprovincecount <= 0:
            return self.minimumgarrison

        totalcountrytroops = int(self.countryindex.countrytroopcountindex.get(countryname, 0))
        offensivereservetroops = int(totalcountrytroops * self.frontlineoffensivereservefraction)
        return max(self.minimumgarrison, offensivereservetroops // frontlineprovincecount)

    def findshortestpathtotarget(self, sourceprovinceid, targetprovinceids, allowedprovinceidset):
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

    def movereservestotargets(
        self,
        countryname,
        targetprovinceids,
        warlookup,
        movementorderlist,
        turnnumber,
        maxorders,
        personality=None,
    ):
        if not targetprovinceids:
            return 0

        controlledprovinceidset = set(self.countryindex.controlledprovinceids(countryname))
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

        enemycountryset = set(warlookup.get(countryname, set()))
        offensivebaseline = self.frontlineoffensivebaseline(countryname, len(targetprovinceidset))
        defensepriority = getattr(personality, "defensepriority", 1.0) if personality else 1.0
        targetdesiredlookup = {
            provinceid: max(
                self.minimumgarrison,
                int(
                    max(
                        self.frontlinedesiredtroops(
                            countryname,
                            provinceid,
                            enemycountryset=enemycountryset,
                        ),
                        offensivebaseline,
                    )
                    * defensepriority
                ),
            )
            for provinceid in targetprovinceidset
        }
        incominglookup = {provinceid: 0 for provinceid in targetprovinceidset}

        # eso: cache source-target paths inside one reserve pass.
        sortedtargetids = sorted(targetprovinceidset)
        pathcache = {}

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

                for targetprovinceid in sortedtargetids:
                    if targetprovinceid == sourceprovinceid:
                        continue

                    projectedtroops = (
                        int(self.provincemap[targetprovinceid].get("troops", 0))
                        + incominglookup[targetprovinceid]
                    )
                    targetdeficit = targetdesiredlookup[targetprovinceid] - projectedtroops
                    if targetdeficit <= 0:
                        continue

                    pathkey = (sourceprovinceid, targetprovinceid)
                    path = pathcache.get(pathkey)
                    if path is None:
                        path = findprovincepath(
                            sourceprovinceid,
                            targetprovinceid,
                            self.provincemap,
                            self.provincegraph,
                            allowedprovinceidset=controlledprovinceidset,
                        )
                        pathcache[pathkey] = path
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

                self.actionwriter.movetrooporder(
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

    def buildupborderforceswhenidle(self, countryname, warlookup, movementorderlist, turnnumber, personality=None):
        borderprovinceids = sorted(self.countryindex.frontlineprovinceids(countryname))
        if not borderprovinceids:
            return 0

        maxidleorders = max(2, min(10, len(borderprovinceids) * 2))
        return self.movereservestotargets(
            countryname,
            borderprovinceids,
            warlookup,
            movementorderlist,
            turnnumber,
            maxorders=maxidleorders,
            personality=personality,
        )


    # TODO: this is a very basic implementation that just moves reserves to the frontline when invaded, but it could be expanded with more complex logic, such as prioritizing certain provinces based on their strategic value or the strength of the invading forces, or adjusting the response based on personality traits or current war status.
    # ALSO TODO: add logic for deciding when to pull forces from the frontline to reinforce reserves or other provinces, or when to counterattack invading forces instead of just reinforcing the frontline.
    # THIS IS FOR DEFENSIVE MOVEMENT IN RESPONSE TO AN INVASION, NOT FOR PLANNING OFFENSIVE MOVEMENT!! OFFENSIVE MOVEMENT LOGIC SHOULD GO IN NPCINVASIONPLANNER
    def reacttoinvasion(self, countryname, warlookup, movementorderlist, turnnumber, personality=None):
        warenemyset = set(warlookup.get(countryname, set()))
        if not warenemyset:
            return 0

        invadedprovinceids = self.countryindex.invadedprovinceids(countryname)
        if invadedprovinceids:
            invadercountryset = set()
            for provinceid in invadedprovinceids:
                province = self.provincemap.get(provinceid)
                if not province:
                    continue
                controllercountry = getprovincecontroller(province)
                if controllercountry and controllercountry != countryname:
                    invadercountryset.add(controllercountry)

            targetfrontlineids = self.countryindex.frontlineprovinceids(countryname, invadercountryset)
            if not targetfrontlineids:
                targetfrontlineids = self.countryindex.frontlineprovinceids(countryname, warenemyset)
        else:
            targetfrontlineids = self.countryindex.frontlineprovinceids(countryname, warenemyset)

        if not targetfrontlineids:
            return 0

        return self.movereservestotargets(
            countryname,
            targetfrontlineids,
            warlookup,
            movementorderlist,
            turnnumber,
            maxorders=self.maxdefenseordersperturn,
            personality=personality,
        )
