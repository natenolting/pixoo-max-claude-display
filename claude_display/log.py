"""One timestamped, unbuffered log line.

The daemon usually runs under launchd with stdout redirected to a file, so
lines must flush immediately. They carry a clock time because without one
there is no way to line an entry up against what the panel was showing at
a given moment.
"""

import time


def log(*parts) -> None:
    print(time.strftime("%H:%M:%S"), *parts, flush=True)
