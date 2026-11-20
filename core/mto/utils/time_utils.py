import math
import random

# ---------------------------------------------------------------------
# Optional stochastic durations (disabled by default -> deterministic)
# ---------------------------------------------------------------------
_DURATION_CV = 0.0
_DURATION_RNG = random.Random(0)


def set_duration_noise(cv: float = 0.0, seed: int | None = None) -> None:
    """Enable (cv > 0) or disable (cv = 0) multiplicative noise on durations."""
    global _DURATION_CV, _DURATION_RNG
    _DURATION_CV = float(cv)
    _DURATION_RNG = random.Random(seed)


def noisy(duration: float) -> float:
    """Duration x lognormal factor with mean 1 and coefficient of variation cv."""
    if _DURATION_CV <= 0 or duration <= 0:
        return duration

    sigma = math.sqrt(math.log(1.0 + _DURATION_CV ** 2))
    mu = -0.5 * sigma ** 2

    return duration * _DURATION_RNG.lognormvariate(mu, sigma)

def working_time(env, duration):

    HOURS_PER_DAY = 8

    remaining = duration

    while remaining > 0:

        day = int(env.now // 24) % 7  # 0 = lunes

        current_hour = env.now % 24

        # sábado o domingo
        if day >= 5:
            yield env.timeout(24 * (7 - day))
            continue

        if current_hour < HOURS_PER_DAY:
            work_time = min(HOURS_PER_DAY - current_hour, remaining)
            yield env.timeout(work_time)
            remaining -= work_time
        else:
            yield env.timeout(24 - current_hour)
