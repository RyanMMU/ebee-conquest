from . import core, movement, camera
from .events import EngineEventType, EventBus


def getprovinceatmouse(mouseposition, provincelist, zoomvalue, camerax, cameray, screenrectangle=None):
    # return the province table under mouse position

    
    for province in provincelist:
        provincerectscreen = camera.getscreenrectangle(province["rectangle"], zoomvalue, camerax, cameray)
        if screenrectangle is not None and not provincerectscreen.colliderect(screenrectangle):
            continue
        if not provincerectscreen.collidepoint(mouseposition):
            continue

        for polygon in province["polygons"]:
            polygonrectscreen = camera.getscreenrectangle(polygon["rectangle"], zoomvalue, camerax, cameray)
            if not polygonrectscreen.collidepoint(mouseposition):
                continue

            polygonpointsscreen = camera.getscreenpoints(polygon["points"], zoomvalue, camerax, cameray)
            if len(polygonpointsscreen) >= 3 and core.ispointinsidepolygon(mouseposition, polygonpointsscreen):
                return province

    return None




# please put your functions here
# DO NOT import anything from runtime.py here

class EbeeEngine:

    def __init__(
        self,
        statefilepath="states.svg",
        provincefilepath="provinces.svg",
        countrydatafilepath="countries.json",
    ):
        

        self.statefilepath = statefilepath
        self.provincefilepath = provincefilepath
        self.countrydatafilepath = countrydatafilepath

        self.eventbus = EventBus()

        self.stateshapelist = []
        self.provinceenrichedlist = []
        self.provincemap = {}
        self.provincegraph = {}
        self.statetocountrylookup = {}
        self.countrytocolorlookup = {}

        self.playercountry = None
        self.currentturnnumber = 1
        self.countriesatwarset = set()


    def on(self, eventname, callback):
        
        return self.eventbus.subscribe(eventname, callback) #susbcribe



    def subscribe(self, eventname, callback):
        return self.eventbus.subscribe(eventname, callback) #same 



    def off(self, eventname, callback):
        return self.eventbus.unsubscribe(eventname, callback) # unsubscribe from event



    def unsubscribe(self, eventname, callback):
        return self.eventbus.unsubscribe(eventname, callback) # same thing







    def emit(self, eventname, payload):

        self.eventbus.emit(eventname, payload)







    def onWarDeclaration(self, callback):

        return self.on(EngineEventType.WARDECLARED, callback) # war declaration event





    def loadworld(self, onprogress=None):


        self.stateshapelist = core.loadsvgshapes(self.statefilepath, onprogress=onprogress)

        if not self.stateshapelist:
            return False



        self.statetocountrylookup, self.countrytocolorlookup = core.loadcountrydata(self.countrydatafilepath)
        allowedstateidset = set(self.statetocountrylookup.keys())
        self.stateshapelist = [stateshape for stateshape in self.stateshapelist if stateshape["id"] in allowedstateidset]
        if not self.stateshapelist:
            return False

        for stateshape in self.stateshapelist:


            statecountry = self.statetocountrylookup.get(stateshape["id"])
            stateshape["ownercountry"] = statecountry
            stateshape["controllercountry"] = statecountry
            stateshape["country"] = statecountry
            stateshape["countrycolor"] = self.countrytocolorlookup.get(statecountry, (85, 85, 85))


        provinceshapelist = core.loadsvgshapes(self.provincefilepath, onprogress=onprogress)
        if not provinceshapelist:
            return False

        provinceshapelist = [
            province
            for province in provinceshapelist
            if core.getparentstateidfromprovinceid(province["id"]) in allowedstateidset
        ]
        if not provinceshapelist:
            return False


        self.provinceenrichedlist = movement.prepareprovincemetadata(provinceshapelist)


        for province in self.provinceenrichedlist:

            provincecountry = self.statetocountrylookup.get(province["parentstateid"])
            province["ownercountry"] = provincecountry
            province["controllercountry"] = provincecountry
            province["country"] = provincecountry
            province["countrycolor"] = self.countrytocolorlookup.get(provincecountry, (85, 85, 85))



        self.provincemap = {province["id"]: province for province in self.provinceenrichedlist}
        self.provincegraph = core.eso_loadprovincegraphcache(self.provincefilepath, allowedstateidset)
        if self.provincegraph is not None:
            cachedprovinceidset = set(self.provincegraph.keys())
            expectedprovinceidset = set(self.provincemap.keys())
            if cachedprovinceidset != expectedprovinceidset:
                self.provincegraph = None
            else:
                for provinceid, neighborids in self.provincegraph.items():
                    if not neighborids.issubset(expectedprovinceidset):
                        self.provincegraph = None
                        break

        if self.provincegraph is None:
            self.provincegraph = movement.buildprovinceadjacencygraph(self.provincemap, onprogress=onprogress)
            if self.provincegraph is not None:
                core.eso_storeprovincegraphcache(self.provincefilepath, self.provincegraph, allowedstateidset)
        
        
        if self.provincegraph is None:
            return False

        groupedsubdivisionlookup = core.groupsubdivisionsbystate(self.provinceenrichedlist, self.stateshapelist)




        for stateshape in self.stateshapelist:


            subdivisionsforstate = groupedsubdivisionlookup.get(stateshape["id"], []);

            for province in subdivisionsforstate:
                
                ownercountry = stateshape.get("ownercountry", stateshape.get("country"));
                controllercountry = stateshape.get("controllercountry", stateshape.get("country"))
                province["ownercountry"] = ownercountry;
                movement.setprovincecontroller(province, controllercountry, stateshape.get("countrycolor", (85, 85, 85)))


            stateshape["subdivisions"] = subdivisionsforstate


        self.emit(
            EngineEventType.WORLDLOADED, # summary
            {
                "stateCount": len(self.stateshapelist),
                "provinceCount": len(self.provincemap),
                "edgeCount": sum(len(neighborset) for neighborset in self.provincegraph.values()) // 2,
            },
        )


        return True





    def declarewar(self, attackercountry, defendercountry):
        if not attackercountry or not defendercountry or attackercountry == defendercountry:
            return None

        self.countriesatwarset.add(defendercountry)
        payload = {
            "attacker": attackercountry,
            "defender": defendercountry,
            "turn": self.currentturnnumber,
        }
        self.emit(EngineEventType.WARDECLARED, payload)
        return payload






    def getcountrydata(self, countryname):
        if not countryname or not self.provincemap:
            return {}

        ownedprovinces = [province for province in self.provincemap.values() if movement.getprovinceowner(province) == countryname]
        controlledprovinces = [province for province in self.provincemap.values() if movement.getprovincecontroller(province) == countryname]
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


    def getprovincedetails(self, provinceid):
        if not provinceid:
            return {}

        province = self.provincemap.get(provinceid)
        if not province:
            return {}

        controllercountry = movement.getprovincecontroller(province)
        ownercountry = movement.getprovinceowner(province)
        parentstateid = province.get("parentid", province.get("parentstateid"))

        return {
            "id": province.get("id"),
            "stateId": parentstateid,
            "terrain": province.get("terrain"),
            "troops": int(province.get("troops", 0)),
            "ownerCountry": ownercountry,
            "controllerCountry": controllercountry,
            "countryColor": province.get("countrycolor"),
            "center": province.get("center"),
        }


    def getstatedetails(self, stateid):
        if not stateid:
            return {}

        state = next((entry for entry in self.stateshapelist if entry.get("id") == stateid), None)
        if not state:
            return {}

        subdivisions = state.get("subdivisions", [])
        provinceids = [province.get("id") for province in subdivisions if province.get("id")]

        totalstatetroops = sum(int(province.get("troops", 0)) for province in subdivisions)
        controllercountries = sorted(
            {
                movement.getprovincecontroller(province)
                for province in subdivisions
                if movement.getprovincecontroller(province) is not None
            }
        )

        return {
            "id": state.get("id"),
            "ownerCountry": state.get("ownercountry", state.get("country")),
            "controllerCountry": state.get("controllercountry", state.get("country")),
            "countryColor": state.get("countrycolor"),
            "provinceCount": len(provinceids),
            "provinceIds": sorted(provinceids),
            "controllerCountries": controllercountries,
            "totalTroops": totalstatetroops,
            "center": (state["rectangle"].centerx, state["rectangle"].centery),
        }


    def getdetailsatmouse(self, mouseposition, zoomvalue, camerax, cameray, screenrectangle=None, provincelist=None):
        province = self.getprovinceatmouse(
            mouseposition,
            zoomvalue,
            camerax,
            cameray,
            screenrectangle=screenrectangle,
            provincelist=provincelist,
        )

        worldx = (mouseposition[0] - camerax) / zoomvalue
        worldy = (mouseposition[1] - cameray) / zoomvalue

        if not province:
            return {
                "mouseScreen": {"x": mouseposition[0], "y": mouseposition[1]},
                "mouseWorld": {"x": worldx, "y": worldy},
                "province": {},
                "state": {},
                "country": {},
            }

        provinceid = province.get("id")
        parentstateid = province.get("parentid", province.get("parentstateid"))
        controllercountry = movement.getprovincecontroller(province)

        return {
            "mouseScreen": {"x": mouseposition[0], "y": mouseposition[1]},
            "mouseWorld": {"x": worldx, "y": worldy},
            "province": self.getprovincedetails(provinceid),
            "state": self.getstatedetails(parentstateid),
            "country": self.getcountrydata(controllercountry) if controllercountry else {},
        }




    def getprovinceatmouse(self, mouseposition, zoomvalue, camerax, cameray, screenrectangle=None, provincelist=None):
        # api for province at mouse location

        activeprovincelist = self.provinceenrichedlist if provincelist is None else provincelist
        return getprovinceatmouse(
            mouseposition,
            activeprovincelist,
            zoomvalue,
            camerax,
            cameray,
            screenrectangle,
        )
