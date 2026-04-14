from .gameplay import getprovincecontroller
#PLEASE PUT ANYTHING RLEATED TO ECONOMY IN HERE

#PLACEHOLDER, EACH COUNTRY WILL HAVE THEIR OWN ECONOMY CONFIG LATER
defaulteconomy = {
    "startinggold": 1200,
    "startingpopulation": 2500,
    "recruitamount": 100,
    "recruitgoldcostperunit": 1,
    "recruitpopulationcostperunit": 1,
    "mingoldincome": 5,
    "goldincomedivisor": 5,
    "minpopulationgrowth": 10,
    "populationgrowthdivisor": 3,
}


def getdefaulteconomyconfig():
    return dict(defaulteconomy)




def initializeplayereconomy(economyconfig=None):

    config = economyconfig or defaulteconomy

    return (
        config["startinggold"],
        config["startingpopulation"],
        config["recruitamount"],
        config["recruitgoldcostperunit"],
        config["recruitpopulationcostperunit"],
    )


def getendturneconomydelta(ownedprovincecount, economyconfig=None):

    config = economyconfig or defaulteconomy
    goldincome = max(config["mingoldincome"], ownedprovincecount // config["goldincomedivisor"])
    populationgrowth = max(config["minpopulationgrowth"], ownedprovincecount // config["populationgrowthdivisor"])
    # print("economy delta", goldincome, populationgrowth)
    return goldincome, populationgrowth


def getrecruitcosts(recruitamount, recruitgoldcostperunit, recruitpopulationcostperunit):

    
    requiredgold = recruitamount * recruitgoldcostperunit
    requiredpopulation = recruitamount * recruitpopulationcostperunit

    return requiredgold, requiredpopulation




def canrecruittroops(playergold, playerpopulation, requiredgold, requiredpopulation, developmentmode=False):
    if developmentmode:
        return True
    
    return playergold >= requiredgold and playerpopulation >= requiredpopulation


def applyendturneconomy(playercountry, provincemap, playergold, playerpopulation):
    if not playercountry:

        return playergold, playerpopulation

    ownedprovincecount = sum(
        1 for province in provincemap.values() if getprovincecontroller(province) == playercountry
    )


    goldincome, populationgrowth = getendturneconomydelta(ownedprovincecount)
    playergold += goldincome
    playerpopulation += populationgrowth

    return playergold, playerpopulation
