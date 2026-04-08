from collections import defaultdict
from . import core, gameplay

def outputtest():
        print(statefilepath, provincefilepath, countrydatafilepath)
        
class EbeeEngine:


    def __init__(
            
        self,
        statefilepath="states.svg",
        provincefilepath="provinces.svg",
        countrydatafilepath="countries.json",


    ):
        
        

        #filepaths
        self.statefilepath = statefilepath
        self.provincefilepath = provincefilepath
        self.countrydatafilepath = countrydatafilepath

        # game data
        self.events = defaultdict(list)
        self.stateshapelist = []
        self.provinceenrichedlist = []
        self.provincemap = {}
        self.provincegraph = {}
        self.statetocountrylookup = {}
        self.countrytocolorlookup = {}


        # current game state
        self.playercountry = None
        self.currentturnnumber = 1
        self.countriesatwarset = set()




    def on(self, eventname, callback):

        self.events[eventname].append(callback)
        return callback



    def emit(self, eventname, payload):
        for callback in self.events.get(eventname, ()):
            callback(payload)


    def onWarDeclaration(self, callback):
        return self.on("war_declaration", callback)



    def loadworld(self, onprogress=None):
        self.stateshapelist = core.loadsvgshapes(self.statefilepath, onprogress=onprogress)
        if not self.stateshapelist:
            return False

        self.statetocountrylookup, self.countrytocolorlookup = core.loadcountrydata(self.countrydatafilepath)

        for stateshape in self.stateshapelist:

            statecountry = self.statetocountrylookup.get(stateshape["id"])
            stateshape["ownercountry"] = statecountry
            stateshape["controllercountry"] = statecountry
            stateshape["country"] = statecountry
            stateshape["countrycolor"] = self.countrytocolorlookup.get(statecountry, (85, 85, 85))



        provinceshapelist = core.loadsvgshapes(self.provincefilepath, onprogress=onprogress)
        if not provinceshapelist:
            return False



        self.provinceenrichedlist = gameplay.prepareprovincemetadata(provinceshapelist)

        # assign initial country owner,. for starting
        for province in self.provinceenrichedlist:

            provincecountry = self.statetocountrylookup.get(province["parentstateid"])
            province["ownercountry"] = provincecountry
            province["controllercountry"] = provincecountry
            province["country"] = provincecountry
            province["countrycolor"] = self.countrytocolorlookup.get(provincecountry, (85, 85, 85))


        # make province id to province data map
        self.provincemap = {province["id"]: province for province in self.provinceenrichedlist}
        self.provincegraph = gameplay.buildprovinceadjacencygraph(self.provincemap, onprogress=onprogress)
        if self.provincegraph is None:
            return False

        groupedsubdivisionlookup = core.groupsubdivisionsbystate(self.provinceenrichedlist, self.stateshapelist)
        for stateshape in self.stateshapelist:

            subdivisionsforstate = groupedsubdivisionlookup.get(stateshape["id"], [])

            for province in subdivisionsforstate:
                ownercountry = stateshape.get("ownercountry", stateshape.get("country"))
                controllercountry = stateshape.get("controllercountry", stateshape.get("country"))
                province["ownercountry"] = ownercountry
                gameplay.setprovincecontroller(province, controllercountry, stateshape.get("countrycolor", (85, 85, 85)))


            stateshape["subdivisions"] = subdivisionsforstate

        return True

    def declarewar(self, attackercountry, defendercountry):
        if not attackercountry or not defendercountry or attackercountry == defendercountry:
            return None

        self.countriesatwarset.add(defendercountry)
        payload = {
            "attacker": attackercountry,
            "defender": defendercountry,
            "turn": self.currentturnnumber, #the current turn number
        }
        self.emit("war_declaration", payload)
        return payload

    def getcountrydata(self, countryname):
        if not countryname or not self.provincemap:
            return {}

        ownedprovinces = [province for province in self.provincemap.values() if gameplay.getprovinceowner(province) == countryname]
        controlledprovinces = [
            province for province in self.provincemap.values() if gameplay.getprovincecontroller(province) == countryname
        ]
        totaltroopscontrolled = sum(int(province.get("troops", 0)) for province in controlledprovinces)

        stateidsowned = sorted(
            {
                province.get("parentstateid")
                for province in ownedprovinces
                if province.get("parentstateid") is not None
            }
        )
        stateidscontrolled = sorted(
            {
                province.get("parentstateid")
                for province in controlledprovinces
                if province.get("parentstateid") is not None
            }
        )

        return {



            "country": countryname,
            "ownedProvinceCount": len(ownedprovinces),
            "controlledProvinceCount": len(controlledprovinces),
            "controlledTroops": totaltroopscontrolled,
            "ownedProvinceIds": sorted(province["id"] for province in ownedprovinces),
            "controlledProvinceIds": sorted(province["id"] for province in controlledprovinces),
            "ownedStateIds": stateidsowned,
            "controlledStateIds": stateidscontrolled,
            "atWarWith": sorted(self.countriesatwarset),
            "turn": self.currentturnnumber,

        }
