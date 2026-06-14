import { useEffect } from "react";
import {
  Easing,
  useFrameCallback,
  useSharedValue,
  withTiming,
  type SharedValue,
} from "react-native-reanimated";

export interface AcousticDrive {
  /** Monotonic time in seconds (UI thread). */
  time: SharedValue<number>;
  /** Overall energy / RMS proxy, smoothed 0..1. */
  level: SharedValue<number>;
  /** Low-band energy (slow body warps) 0..1. */
  low: SharedValue<number>;
  /** Mid-band energy (ripples) 0..1. */
  mid: SharedValue<number>;
  /** High-band energy (rotor shimmer) 0..1. */
  high: SharedValue<number>;
  /** Morph toward the red/detection palette 0..1. */
  red: SharedValue<number>;
}

/**
 * Generates a smooth, organic acoustic signal that the orb shader consumes.
 *
 * Idle (active=false): a calm, slow "breathing" with low energy.
 * Active (active=true): higher energy with a rotor-tone shimmer in the high band,
 * mimicking a multirotor UAS acoustic signature.
 *
 * This is synthetic for the simulation. To drive it from a real microphone,
 * replace the body of the frame callback with RMS/FFT-band values from
 * expo-audio's useAudioSampleListener (low/mid/high) and keep the same lerp
 * smoothing so the visuals stay stable.
 */
export function useAcousticDrive(active: boolean): AcousticDrive {
  const time = useSharedValue(0);
  const level = useSharedValue(0.12);
  const low = useSharedValue(0.1);
  const mid = useSharedValue(0.1);
  const high = useSharedValue(0.05);
  const red = useSharedValue(0);
  const energy = useSharedValue(0);

  useEffect(() => {
    red.value = withTiming(active ? 1 : 0, {
      duration: 650,
      easing: Easing.inOut(Easing.cubic),
    });
    energy.value = withTiming(active ? 1 : 0, {
      duration: 800,
      easing: Easing.inOut(Easing.cubic),
    });
  }, [active, red, energy]);

  useFrameCallback((frame) => {
    "worklet";
    const dt = Math.min((frame.timeSincePreviousFrame ?? 16) / 1000, 0.05);
    time.value += dt;
    const t = time.value;
    const e = energy.value; // 0 idle .. 1 active

    // Organic, non-repeating modulation from layered sines.
    const breath = 0.5 + 0.5 * Math.sin(t * (1.0 + 2.0 * e));
    const swirl = 0.5 + 0.5 * Math.sin(t * 6.7 + Math.sin(t * 2.1) * 1.7);
    const rotor = 0.5 + 0.5 * Math.sin(t * (16.0 + 6.0 * e)); // prop tone

    const base = 0.1 + 0.42 * e;
    const span = 0.06 + 0.42 * e;

    const rawLevel = base + span * (0.55 * breath + 0.3 * swirl + 0.15 * rotor);
    const rawLow = base + span * breath;
    const rawMid = base * 0.85 + span * swirl;
    const rawHigh = 0.04 + (0.05 + 0.55 * e) * rotor;

    // Critically-damped-ish lerp smoothing toward targets.
    const k = (rate: number) => Math.min(1, dt * rate);
    level.value += (rawLevel - level.value) * k(8);
    low.value += (rawLow - low.value) * k(6);
    mid.value += (rawMid - mid.value) * k(9);
    high.value += (rawHigh - high.value) * k(14);
  });

  return { time, level, low, mid, high, red };
}
