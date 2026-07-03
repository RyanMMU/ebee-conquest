import os
import sys
import traceback


if getattr(sys, "frozen", False):
    _localappdata = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"),
        "AppData",
        "Local",
    )
    _crashlogdirectory = os.path.join(_localappdata, "Ebee Conquest")

    def _logpackagedexception(exceptiontype, exceptionvalue, exceptiontraceback):
        try:
            os.makedirs(_crashlogdirectory, exist_ok=True)
            crashlogpath = os.path.join(_crashlogdirectory, "crash.log")
            with open(crashlogpath, "w", encoding="utf-8") as crashlog:
                traceback.print_exception(
                    exceptiontype,
                    exceptionvalue,
                    exceptiontraceback,
                    file=crashlog,
                )
        finally:
            sys.__excepthook__(exceptiontype, exceptionvalue, exceptiontraceback)

    sys.excepthook = _logpackagedexception
    os.chdir(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))

import game.menu_gui as menu
# NOTE!!
# This is a DIRECT engine launcher, not meant for normal gameplay. 
# This is only used for testing and debugging only. 
# pls use menu_gui.py (name will be changed later), it is more preferable. 
# This file might be modified so please be advised.
menu.main()
