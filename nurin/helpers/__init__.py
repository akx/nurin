import random
import time


def jittered_sleep(base_duration: float, jitter: float = 0) -> None:
    time.sleep(base_duration * random.uniform(1.0 - jitter, 1.0 + jitter))
