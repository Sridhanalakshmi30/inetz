import test from 'node:test';
import assert from 'node:assert/strict';
import { createMultipleFaceTracker } from './multipleFaceTracker.js';

test('rejects a flicker and requires three samples spanning at least one second', () => {
  const tracker = createMultipleFaceTracker();
  assert.equal(tracker.sample(2, 0), false);
  assert.equal(tracker.sample(1, 1000), false);
  assert.equal(tracker.sample(2, 2000), false);
  assert.equal(tracker.sample(2, 3999), false);
  assert.equal(tracker.sample(2, 4000), true);
});

test('persistent extra face repeats ten seconds after the first event', () => {
  const tracker = createMultipleFaceTracker();
  tracker.sample(2, 0);
  tracker.sample(2, 500);
  assert.equal(tracker.sample(2, 2000), true);
  for (let now = 4000; now < 12000; now += 2000) assert.equal(tracker.sample(2, now), false);
  assert.equal(tracker.sample(2, 12000), true);
});

test('network delay does not shorten the warning grace period', () => {
  const tracker = createMultipleFaceTracker();
  tracker.sample(2, 0);
  tracker.sample(2, 500);
  tracker.sample(2, 2000);
  tracker.acknowledge(5000);
  assert.equal(tracker.sample(2, 12000), false);
  assert.equal(tracker.sample(2, 15000), true);
});

test('healthy camera must recover before counting a separate occurrence', () => {
  const tracker = createMultipleFaceTracker();
  tracker.sample(2, 0);
  tracker.sample(2, 500);
  tracker.sample(2, 2000);
  tracker.sample(1, 4000);
  assert.equal(tracker.sample(2, 6000), false);
  assert.equal(tracker.sample(2, 8000), false);
  tracker.sample(1, 10000);
  tracker.sample(1, 12000);
  assert.equal(tracker.sample(2, 14000), false);
  assert.equal(tracker.sample(2, 14500), false);
  assert.equal(tracker.sample(2, 16000), true);
});

test('camera interruption clears confirmation and repeat timers', () => {
  const tracker = createMultipleFaceTracker();
  tracker.sample(2, 0);
  tracker.sample(2, 500);
  tracker.reset();
  assert.equal(tracker.sample(2, 20000), false);
  assert.equal(tracker.sample(2, 20500), false);
  assert.equal(tracker.sample(2, 22000), true);
  tracker.reset();
  assert.equal(tracker.sample(2, 40000), false);
  assert.equal(tracker.sample(2, 42000), false);
  assert.equal(tracker.sample(2, 50000), true);
});

test('confirms quickly without treating two isolated frames as an occurrence', () => {
  const tracker = createMultipleFaceTracker();
  assert.equal(tracker.sample(2, 0), false);
  assert.equal(tracker.sample(2, 500), false);
  assert.equal(tracker.sample(2, 1000), true);
  const sparse = createMultipleFaceTracker();
  assert.equal(sparse.sample(2, 0), false);
  assert.equal(sparse.sample(2, 3000), false);
});
