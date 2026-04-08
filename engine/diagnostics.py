import os
import time

# i separated diagnostics into its own module because its getting too complicated



def getprocessmemoryusage():
    try:
        import psutil # hardware info

        memoryinfo = psutil.Process(os.getpid()).memory_info()
        megabyte = 1024 * 1024
        workingsetmb = memoryinfo.rss / megabyte
        privatememorymb = getattr(memoryinfo, "private", memoryinfo.vms) / megabyte
        return workingsetmb, privatememorymb
    except Exception:
        return None, None




def logstartupdiagnostics(startuptimestamp, stage, details=""):
    secondspassed = time.perf_counter() - startuptimestamp
    wmemorymb, pmemorymb = getprocessmemoryusage()


    if wmemorymb is None:
        memorysegment = "memory=CANNOT FIND!"
    else:
        memorysegment = f"working={wmemorymb:.1f}MB private={pmemorymb:.1f}MB"

    detailsegment = f" | {details}" if details else ""
    print(
        f"local@EbeeEngine:~${secondspassed:7.2f}s | {stage} | {memorysegment}{detailsegment}",
        flush=True,
    )




def createloadingprogresscallback(drawprogresscallback, startuptimestamp, stage, logintervalseconds=1.5):
    callbackstate = {"lastlogtimestamp": 0.0}


    def loadingprogresscallback(completedcount, totalcount):
        shouldcontinue = drawprogresscallback(completedcount, totalcount)
        currenttimestamp = time.perf_counter()
        shouldlog = (
            completedcount == 0
            or (totalcount > 0 and completedcount >= totalcount)
            or (currenttimestamp - callbackstate["lastlogtimestamp"]) >= logintervalseconds
        )
        if shouldlog:
            logstartupdiagnostics(startuptimestamp, stage, f"progress={completedcount}/{totalcount}")
            callbackstate["lastlogtimestamp"] = currenttimestamp
        return shouldcontinue

    return loadingprogresscallback




def logslowpath(filepath, currentprog, totalcount, shapeid, secondspassed, allowedmaxseconds=1.5):
    if secondspassed < allowedmaxseconds:
        return
    print(
        f"local@EbeeEngine:~$ slow path!!!!! | file={os.path.basename(filepath)} was at={currentprog}/{totalcount} id={shapeid} took={secondspassed:.2f}s",
        flush=True,
    )


