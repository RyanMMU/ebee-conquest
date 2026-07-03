import os
import math
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
        return None, None #imortant, if psutil is not available memory will just say cannot find


def getprocessmemorystats():
    """Return portable process memory counters in MiB when psutil is available."""
    try:
        import psutil

        memoryinfo = psutil.Process(os.getpid()).memory_info()
        megabyte = 1024 * 1024
        peakrss = getattr(memoryinfo, "peak_wset", None)
        return {
            "rss_mb": memoryinfo.rss / megabyte,
            "vms_mb": memoryinfo.vms / megabyte,
            "private_mb": getattr(memoryinfo, "private", memoryinfo.vms) / megabyte,
            "peak_rss_mb": None if peakrss is None else peakrss / megabyte,
        }
    except Exception:
        return {
            "rss_mb": None,
            "vms_mb": None,
            "private_mb": None,
            "peak_rss_mb": None,
        }


def percentile(samples, quantile):
    """Use the nearest-rank percentile so p99 includes the max for small samples."""
    if not samples:
        return None
    ordered = sorted(float(sample) for sample in samples)
    boundedquantile = max(0.0, min(1.0, float(quantile)))
    rank = max(1, math.ceil(boundedquantile * len(ordered)))
    return ordered[rank - 1]


def summarizeframetimes(samples):
    if not samples:
        return {
            "count": 0,
            "average_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
            "fps": None,
        }

    floatsamples = [float(sample) for sample in samples]
    averagemilliseconds = sum(floatsamples) / len(floatsamples)
    return {
        "count": len(floatsamples),
        "average_ms": averagemilliseconds,
        "p95_ms": percentile(floatsamples, 0.95),
        "p99_ms": percentile(floatsamples, 0.99),
        "max_ms": max(floatsamples),
        "fps": 1000.0 / max(0.001, averagemilliseconds),
    }




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




def createloadingprogresscallback(
    drawprogresscallback,
    startuptimestamp,
    stage,
    logintervalseconds=1.5,
    onlog=None,
):
    callbackstate = {"lastlogtimestamp": 0.0}


    def loadingprogresscallback(completedcount, totalcount):
        currenttimestamp = time.perf_counter()
        elapsedseconds = currenttimestamp - startuptimestamp
        progressratio = 0.0 if totalcount <= 0 else completedcount / totalcount
        progresspercent = max(0.0, min(100.0, progressratio * 100.0))
        statusline = f"{stage} | {completedcount}/{totalcount} ({progresspercent:.1f}%) | {elapsedseconds:.1f}s"
        shouldcontinue = drawprogresscallback(completedcount, totalcount, stage, statusline)

        shouldlog = (
            completedcount == 0
            or (totalcount > 0 and completedcount >= totalcount)
            or (currenttimestamp - callbackstate["lastlogtimestamp"]) >= logintervalseconds
        )
        if shouldlog:
            details = f"progress={completedcount}/{totalcount} ({progresspercent:.1f}%) elapsed={elapsedseconds:.1f}s"
            logstartupdiagnostics(startuptimestamp, stage, details)
            if onlog:
                onlog(f"{stage}: {details}")
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


