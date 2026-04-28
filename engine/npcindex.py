from collections import defaultdict

from .movement import getprovincecontroller, getprovinceowner

# NPC INDEX

class NpcCountryIndex:
    def __init__(self, provincemap, provincegraph):
        self.provincemap = provincemap if provincemap is not None else {}
        self.provincegraph = provincegraph if provincegraph is not None else {}
        self.clear()

    def clear(self):
        self.countryprovinceindex = {}
        self.countrycoreprovinceindex = {}
        self.countryinvadedprovinceindex = {}
        self.countryprovincecountindex = {}
        self.countrytroopcountindex = {}
        self.countrystatecountindex = {}
        self.countryfrontlineallindex = {}
        self.countryfrontlineenemyindex = {}
        self.countryenemybordertargetindex = {}
        self.allcountrycache = ()
        self.countryaliaslookup = {}


    # THISIS FOR BUILDING INDEXES OF COUNTRY CONTROL AND BORDERS, NOT FOR CALCULATING STRENGTH OR PLANNING MOVEMENT
    # STRENGTH CALCULATION SHOULD GO IN NPCSTRENGTHPLANNER AND MOVEMENT PLANNING SHOULD GO IN NPCDEFENSEPLANNER OR NPCINVASIONPLANNER
    def rebuild(self):
        # eso: build country and frontline indexes once per turn.
        countryset = set()
        controlledindex = defaultdict(list)
        coreindex = defaultdict(list)
        invadedindex = defaultdict(list)
        stateindex = defaultdict(set)
        provincecountindex = defaultdict(int)
        troopcountindex = defaultdict(int)
        frontlineallindex = defaultdict(set)
        frontlineenemyindex = defaultdict(lambda: defaultdict(set))
        enemybordertargetindex = defaultdict(lambda: defaultdict(set))

        for provinceid, province in self.provincemap.items():
            controllercountry = getprovincecontroller(province)
            ownercountry = getprovinceowner(province)
            stateid = province.get("parentstateid") or province.get("parentid")

            if controllercountry:
                countryset.add(controllercountry)
                controlledindex[controllercountry].append(provinceid)
                provincecountindex[controllercountry] += 1
                troopcountindex[controllercountry] += max(0, int(province.get("troops", 0)))
                if stateid is not None:
                    stateindex[controllercountry].add(stateid)
            if ownercountry:
                countryset.add(ownercountry)
            if controllercountry and ownercountry and controllercountry == ownercountry:
                coreindex[controllercountry].append(provinceid)
            elif ownercountry and controllercountry != ownercountry:
                invadedindex[ownercountry].append(provinceid)

            if not controllercountry:
                continue

            for neighborprovinceid in self.provincegraph.get(provinceid, ()):
                neighborprovince = self.provincemap.get(neighborprovinceid)
                if not neighborprovince:
                    continue

                neighborcountry = getprovincecontroller(neighborprovince)
                if not neighborcountry or neighborcountry == controllercountry:
                    continue

                frontlineallindex[controllercountry].add(provinceid)
                frontlineenemyindex[controllercountry][neighborcountry].add(provinceid)
                enemybordertargetindex[controllercountry][neighborcountry].add(neighborprovinceid)

        self.allcountrycache = tuple(sorted(countryset))
        self.countryprovinceindex = {country: tuple(sorted(ids)) for country, ids in controlledindex.items()}
        self.countrycoreprovinceindex = {country: tuple(sorted(ids)) for country, ids in coreindex.items()}
        self.countryinvadedprovinceindex = {country: tuple(sorted(ids)) for country, ids in invadedindex.items()}
        self.countryprovincecountindex = dict(provincecountindex)
        self.countrytroopcountindex = dict(troopcountindex)
        self.countrystatecountindex = {country: len(stateids) for country, stateids in stateindex.items()}
        self.countryfrontlineallindex = {
            country: tuple(sorted(provinceids))
            for country, provinceids in frontlineallindex.items()
        }
        self.countryfrontlineenemyindex = {
            country: {enemy: tuple(sorted(provinceids)) for enemy, provinceids in byenemy.items()}
            for country, byenemy in frontlineenemyindex.items()
        }
        self.countryenemybordertargetindex = {
            country: {enemy: tuple(sorted(provinceids)) for enemy, provinceids in byenemy.items()}
            for country, byenemy in enemybordertargetindex.items()
        }
        self.countryaliaslookup = {
            str(country).strip().lower(): str(country).strip()
            for country in self.allcountrycache
            if str(country).strip()
        }

    def allcountries(self):
        if not self.allcountrycache and self.provincemap:
            self.rebuild()
        return self.allcountrycache

    def controlledprovinceids(self, countryname):
        if not self.countryprovinceindex and self.provincemap:
            self.rebuild()
        return self.countryprovinceindex.get(countryname, ())

    def corecontrolledprovinceids(self, countryname):
        if not self.countrycoreprovinceindex and self.provincemap:
            self.rebuild()
        return self.countrycoreprovinceindex.get(countryname, ())

    def invadedprovinceids(self, countryname):
        if not self.countryinvadedprovinceindex and self.provincemap:
            self.rebuild()
        return self.countryinvadedprovinceindex.get(countryname, ())

    def countcontrolledstates(self, controlledprovinceids):
        if controlledprovinceids:
            sampleprovinceid = controlledprovinceids[0]
            sampleprovince = self.provincemap.get(sampleprovinceid)
            if sampleprovince:
                controllercountry = getprovincecontroller(sampleprovince)
                if controllercountry in self.countrystatecountindex:
                    return int(self.countrystatecountindex.get(controllercountry, 0))

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

    def frontlineprovinceids(self, countryname, enemycountryset=None):
        if enemycountryset is None:
            return self.countryfrontlineallindex.get(countryname, ())

        byenemy = self.countryfrontlineenemyindex.get(countryname, {})
        frontlineids = set()
        for enemycountry in enemycountryset:
            frontlineids.update(byenemy.get(enemycountry, ()))
        if frontlineids:
            return frontlineids

        frontlineids = set()
        for provinceid in self.controlledprovinceids(countryname):
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

    def enemybordertargetids(self, countryname, enemycountry):
        cachedtargets = self.countryenemybordertargetindex.get(countryname, {}).get(enemycountry)
        if cachedtargets is not None:
            return cachedtargets

        targetids = set()
        for provinceid in self.controlledprovinceids(countryname):
            for neighborprovinceid in self.provincegraph.get(provinceid, ()):
                neighborprovince = self.provincemap.get(neighborprovinceid)
                if not neighborprovince:
                    continue
                if getprovincecontroller(neighborprovince) == enemycountry:
                    targetids.add(neighborprovinceid)

        return sorted(targetids)

    def canonicalizecountry(self, countryname):
        if countryname is None:
            return None

        countrytext = str(countryname).strip()
        if not countrytext:
            return None

        if not self.countryaliaslookup:
            self.rebuild()
        return self.countryaliaslookup.get(countrytext.lower(), countrytext)

    def normalizewarpair(self, firstcountry, secondcountry):
        if not firstcountry or not secondcountry:
            return None

        first = self.canonicalizecountry(firstcountry)
        second = self.canonicalizecountry(secondcountry)
        if not first or not second:
            return None
        if first == second:
            return None
        if first <= second:
            return (first, second)
        return (second, first)

    def adjusttroopcount(self, countryname, amount):
        currentcount = int(self.countrytroopcountindex.get(countryname, 0))
        nextcount = currentcount + int(amount)
        self.countrytroopcountindex[countryname] = max(0, nextcount)


class NpcWorldIndex(NpcCountryIndex):
    pass
