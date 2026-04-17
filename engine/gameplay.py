# THIS IS LEGACY CODE
# INSTEAD OF IMPORTING FROM HERE, USE engine.movement INSTEAD ! !!!

from .movement import (
    buildprovinceadjacencygraph,
    findprovincepath,
    getprovincecontroller,
    getprovinceowner,
    getterrainmovecost,
    prepareprovincemetadata,
    processmovementorders,
    setprovincecontroller,
)

__all__ = [
    "getprovincecontroller",
    "getprovinceowner",
    "setprovincecontroller",
    "prepareprovincemetadata",
    "buildprovinceadjacencygraph",
    "getterrainmovecost",
    "findprovincepath",
    "processmovementorders",
]


