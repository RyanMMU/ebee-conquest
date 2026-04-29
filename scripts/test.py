storedapi = None # do this to avoid circular import

# test script



def onload(api):
    global storedapi
    storedapi = api
    api.subscribe("nextturn", onturn)
    api.subscribe("wardeclared", onwar)
    api.subscribe("focuscompleted", onfocus)
    api.log("TEST script ready")


def onturn(payload):
    country = payload.get("playerCountry")
    turn = int(payload.get("turn", 0))
    if not country or turn % 5 != 0:
        return

    newgold = storedapi.addgold(country, 25)
    storedapi.log(f"{country} received 25 gold on turn {turn}, now {newgold}")
    storedapi.show_script_message(f"{country} received 25 gold on turn {turn}, now {newgold}")


def onwar(payload):
    attacker = payload.get("attacker")
    defender = payload.get("defender")
    storedapi.log(f"war declared: {attacker} v {defender}")
    storedapi.show_script_message(f"war declared: {attacker} v {defender}")


def onfocus(payload):
    country = payload.get("country")
    focus = payload.get("focusId")
    if country:
        storedapi.addpopulation(country, 50)
    storedapi.log(f"focus completed: {focus}")
    storedapi.show_script_message(f"focus completed: {focus}")
