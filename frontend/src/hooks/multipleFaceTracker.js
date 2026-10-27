// Only uninterrupted, valid camera samples contribute to an occurrence.
export function createMultipleFaceTracker({ confirmationMs = 1000, recoveryMs = 2000, minSamples = 3, repeatMs = 10000 } = {}) {
  let multipleSince = null;
  let healthySince = null;
  let reported = false;
  let repeatSince = null;
  let multipleSamples = 0;
  return {
    acknowledge(now) {
      repeatSince = now;
    },
    reset() {
      multipleSince = healthySince = repeatSince = null;
      multipleSamples = 0;
    },
    sample(count, now) {
      if (count <= 1) {
        multipleSince = repeatSince = null;
        multipleSamples = 0;
        if (count === 1) {
          healthySince ??= now;
          if (now - healthySince >= recoveryMs) reported = false;
        } else healthySince = null;
        return false;
      }
      healthySince = null;
      multipleSince ??= now;
      multipleSamples += 1;
      if (reported) repeatSince ??= now;
      if (multipleSamples < minSamples || now - multipleSince < confirmationMs) return false;
      if (reported && now - repeatSince < repeatMs) return false;
      reported = true;
      repeatSince = now;
      return true;
    },
  };
}
