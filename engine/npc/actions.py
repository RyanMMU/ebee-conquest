from ..events import EngineEventType
from ..movement import markprovincetroopactivity


# NPC ACTIONS
# actions that npc countries can take, such as recruiting troops and moving them between provinces
# currently just a wrapper for emitting events and updating province and country state, but could be expanded with more complex logic or additional actions in the future
class NpcTurnActions:
    def __init__(self, provincemap, countrytocolorlookup, countryindex, emit=None):
        self.provincemap = provincemap if provincemap is not None else {}
        self.countrytocolorlookup = countrytocolorlookup if countrytocolorlookup is not None else {}
        self.countryindex = countryindex
        self.emitfunction = emit

    def setemit(self, emit):
        self.emitfunction = emit

    def emit(self, eventname, payload):
        if callable(self.emitfunction):
            self.emitfunction(eventname, payload)

    def appendmovementorder(self, movementorderlist, countryname, sourceprovinceid, path, troopcount, turnnumber):
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

        self.emit(
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

    def movetrooporder(self, movementorderlist, countryname, sourceprovinceid, path, troopcount, turnnumber):
        sourceprovince = self.provincemap[sourceprovinceid]
        sourceprovince["troops"] -= troopcount
        self.countryindex.adjusttroopcount(countryname, -troopcount)
        markprovincetroopactivity(sourceprovince, turnnumber)
        self.appendmovementorder(
            movementorderlist,
            countryname,
            sourceprovinceid,
            path,
            troopcount,
            turnnumber,
        )

    def recruit(self, countryname, provinceid, troopcount, turnnumber):
        self.provincemap[provinceid]["troops"] += troopcount
        self.countryindex.adjusttroopcount(countryname, troopcount)
        markprovincetroopactivity(self.provincemap[provinceid], turnnumber)
        self.emit(
            EngineEventType.TROOPSRECRUITED,
            {
                "country": countryname,
                "provinceId": provinceid,
                "amount": troopcount,
                "turn": turnnumber,
                "isNpc": True,
            },
        )
