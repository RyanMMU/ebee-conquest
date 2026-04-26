from engine.console import rundevcommand
from engine.events import EngineEventType, EventBus


def testgetpmap(troops1=0, troops2=0):
    return {
        "P1": {"id": "P1", "ownercountry": "Malaysia", "controllercountry": "Malaysia", "country": "Malaysia", "troops": troops1},
        "P2": {"id": "P2", "ownercountry": "Thailand", "controllercountry": "Thailand", "country": "Thailand", "troops": troops2},
    }



class fakenpc:
    def __init__(self):
        self.playercountry = "Malaysia"
        self.countryeconomy = {"Malaysia": {"gold": 1200, "population": 2500}, "Thailand": {"gold": 900, "population": 1800}}
        self.executedturns = []

    def setplayercountry(self, c): 
        self.playercountry = c
        
    def executeturn(self, orders, turn, dev=False):
        self.executedturns.append((len(orders or []), int(turn), bool(dev)))
        return {"ordersCreated": 0}
        
    def testcanonicalizecountry(self, c): 
        return {"malaysia": "Malaysia", "thailand": "Thailand"}.get(str(c).strip().lower())
        
    def testsyncplayerwars(self, *args): pass
    def testinitializecountryeconomy(self): pass
    def rebuildcountryindexes(self): pass



def testruncmd(cmd, pmap=None, ctx=None, bus=None, turn=1):
    ctx = ctx if ctx is not None else {"playercountry": "Malaysia", "countriesatwarset": set(), "warpairset": set(), "npcdirector": fakenpc()}
    return rundevcommand(
        cmd,
        provincemap=pmap or testgetpmap(),
        playercountry="Malaysia",
        countrytocolor={"Malaysia": (20, 30, 40)},
        fallbackcolor=(0, 0, 0),
        troopbadgelist=[],
        eventbus=bus or EventBus(),
        currentturnnumber=turn,
        commandcontext=ctx,
    )




# //////////////

def testconsolewarcommandemitswarevent():
    bus, captured = EventBus(), []
    bus.subscribe(EngineEventType.WARDECLARED, captured.append)
    
    assert testruncmd("war malaysia thailand", bus=bus, turn=7) == "ok war declared: Malaysia -> Thailand"
    assert len(captured) == 1
    assert captured == {"attacker": "Malaysia", "defender": "Thailand", "turn": 7}



def testconsolewarcommandrejectssamecountry():
    assert testruncmd("war Malaysia malaysia") == "countries must differ"




def testconsolewarcommandrejectsunknowncountry():
    assert testruncmd("war Malaysia Atlantis") == "unknown country: Atlantis"



def testcountrystatswithoutarglistsnpctroops():
    result = testruncmd("country_stats", pmap=testgetpmap(troops1=12, troops2=40))
    assert "Malaysia" in result and "Thailand" in result
    assert "controlled_troops=40" in result



def testconsoleobservecommandreleasesplayercountrytoai():

    ctx = {"playercountry": "Malaysia", "countriesatwarset": {"Thailand"}, "warpairset": {("Malaysia", "Thailand")}, "npcdirector": fakenpc()}
    assert testruncmd("observe", ctx=ctx) == "ok observe mode enabled (player control released to AI)"
    assert ctx["playercountry"] is None
    assert ctx["countriesatwarset"] == set()
    assert ctx["npcdirector"].playercountry is None



def testconsolesetplayercountrycommandupdatesruntimecontext():


    ctx = {"playercountry": None, "countriesatwarset": set(), "warpairset": set(), "npcdirector": fakenpc()}
    assert testruncmd("setplayercountry thailand", ctx=ctx) == "ok playercountry=Thailand"
    assert ctx["playercountry"] == ctx["npcdirector"].playercountry == "Thailand"
    assert ctx["gamephase"] == "play"


def testconsoleeconomyplayercommandscansetandaddvalues():

    ctx = {"playergold": 100, "playerpopulation": 40}
    assert testruncmd("economy set gold 250", ctx=ctx) == "ok player gold=250"
    assert testruncmd("economy add population -15", ctx=ctx) == "ok player population=25"
    assert ctx["playergold"] == 250
    assert ctx["playerpopulation"] == 25



def testconsoleeconomycountrycommandupdatesnpccountryeconomy():

    ctx = {"npcdirector": fakenpc()}
    assert testruncmd("economy country thailand add gold 125", ctx=ctx) == "ok economy Thailand gold=1025"
    assert ctx["npcdirector"].countryeconomy["Thailand"]["gold"] == 1025



def testconsoleevalcommandcanexecuteandmutatecontext():


    ctx = {"playergold": 100, "playerpopulation": 50}
    assert testruncmd("eval context['playergold'] += 25; context['playerpopulation'] = 5", ctx=ctx) == "exec ok"
    assert ctx["playergold"] == 125
    assert ctx["playerpopulation"] == 5



def testconsoleendturnadvancesturnandrunsnpcdirector():

    ctx = {"playercountry": "Malaysia", "currentturnnumber": 3, "countriesatwarset": set(), "warpairset": set(), "movementorderlist": [], "npcdirector": fakenpc()}
    assert testruncmd("endturn 2", ctx=ctx) == "ok advanced turn to 5"
    assert ctx["currentturnnumber"] == 5
    assert ctx["npcdirector"].executedturns == [(0, 3, False), (0, 4, False)]


def testconsoledeclarepeaceremovesexistingwarpair():


    ctx = {"playercountry": "Malaysia", "countriesatwarset": {"Thailand"}, "warpairset": {("Malaysia", "Thailand")}, "npcdirector": fakenpc()}
    assert testruncmd("declarepeace malaysia thailand", ctx=ctx) == "ok peace declared: Malaysia & Thailand"
    assert ctx["warpairset"] == ctx["countriesatwarset"] == set()



def testconsoletakeovercountrytransfersallcontroltotargetcountry():

    pmap = testgetpmap()

    assert testruncmd("takeovercountry thailand malaysia", pmap=pmap) == "ok takeover Thailand -> Malaysia (owner=1 controller=1)"
    assert pmap["P2"]["ownercountry"] == pmap["P2"]["controllercountry"] == pmap["P2"]["country"] == "Malaysia"




def testconsolespawnwarcreateswarsforneighboringcountries():
    ctx = {"playercountry": "Malaysia", "countriesatwarset": set(), "warpairset": set(), "npcdirector": fakenpc(), "provincegraph": {"P1": {"P2"}, "P2": {"P1"}}}
   
    assert testruncmd("spawnwar malaysia", ctx=ctx) == "ok spawned wars: Malaysia vs Thailand"
    assert ctx["warpairset"] == {("Malaysia", "Thailand")}
    assert ctx["countriesatwarset"] == {"Thailand"}