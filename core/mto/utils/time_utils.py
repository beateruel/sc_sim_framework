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
