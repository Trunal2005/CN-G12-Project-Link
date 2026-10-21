import math

PROFILES = {
    'stable': 'Constant delivery capacity',
    'step': 'High → drop at 12 s → recovery at 28 s',
    'gradual': 'Smooth decline and recovery over 40 s',
    'fluctuate': 'Seeded correlated fluctuations',
    'unfamiliar': 'Held-out double transition at 9, 19, 31 s',
}

def capacity(profile: str, seed: int, scale: float, elapsed: float) -> float:
    if profile == 'stable': value = 3_500_000
    elif profile == 'step': value = 3_500_000 if elapsed < 12 or elapsed >= 28 else 480_000
    elif profile == 'gradual': value = 600_000 + 2_900_000 * (1 + math.cos(elapsed * math.pi / 20)) / 2
    elif profile == 'unfamiliar': value = 2_700_000 if elapsed < 9 else 420_000 if elapsed < 19 else 4_000_000 if elapsed < 31 else 850_000
    else:
        # Continuous correlated deterministic signal; no global RNG or wall clock.
        value = 1_900_000 + 1_150_000 * math.sin(elapsed / 4.7 + seed * .71) + 350_000 * math.sin(elapsed / 1.9 + seed)
    return max(100_000, min(20_000_000, value * scale))
