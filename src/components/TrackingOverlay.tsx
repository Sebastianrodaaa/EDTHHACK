import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, radius, space, type } from "../theme";
import { GlassCard } from "./GlassCard";
import { useAppStore } from "../store";

const DIAL = 104;

/**
 * Compact tracking overlay — a bearing compass + live track stats. Renders only
 * while a target track is open (fed by server `track_update` events).
 */
export function TrackingOverlay() {
  const tracking = useAppStore((s) => s.tracking);

  if (!tracking || !tracking.track_id) return null;

  const bearing = tracking.bearing_deg ?? 0;
  const stateColor =
    tracking.state === "tracking"
      ? colors.red
      : tracking.state === "acquiring"
      ? colors.orange
      : colors.tertiary;

  return (
    <GlassCard style={styles.panel}>
      <View style={styles.dial}>
        {(["N", "E", "S", "W"] as const).map((c, i) => (
          <Text
            key={c}
            style={[
              styles.tick,
              i === 0 && styles.tickN,
              i === 1 && styles.tickE,
              i === 2 && styles.tickS,
              i === 3 && styles.tickW,
            ]}
          >
            {c}
          </Text>
        ))}
        <View style={[styles.needleWrap, { transform: [{ rotate: `${bearing}deg` }] }]}>
          <View style={[styles.needle, { backgroundColor: stateColor }]} />
        </View>
        <View style={[styles.hub, { backgroundColor: stateColor }]} />
      </View>

      <View style={styles.stats}>
        <Text style={styles.trackId}>{tracking.track_id}</Text>
        <Stat label="Bearing" value={`${Math.round(bearing)}°`} />
        <Stat
          label="Range"
          value={tracking.range_m != null ? `${Math.round(tracking.range_m)} m` : "—"}
        />
        <Stat
          label="Speed"
          value={tracking.speed_mps != null ? `${Math.round(tracking.speed_mps)} m/s` : "—"}
        />
        <View style={styles.stateRow}>
          <View style={[styles.stateDot, { backgroundColor: stateColor }]} />
          <Text style={[styles.stateText, { color: stateColor }]}>
            {tracking.state.toUpperCase()}
          </Text>
          <Text style={styles.conf}>{Math.round((tracking.confidence ?? 0) * 100)}%</Text>
        </View>
      </View>
    </GlassCard>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.statRow}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
  },
  dial: {
    width: DIAL,
    height: DIAL,
    borderRadius: DIAL / 2,
    borderWidth: 1,
    borderColor: colors.hairlineStrong,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.02)",
  },
  tick: { ...type.caption2, color: colors.secondary, position: "absolute" },
  tickN: { top: 4 },
  tickE: { right: 6 },
  tickS: { bottom: 4 },
  tickW: { left: 6 },
  needleWrap: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
  },
  needle: {
    width: 3,
    height: DIAL / 2 - 10,
    borderRadius: 2,
    marginTop: 10,
  },
  hub: { width: 8, height: 8, borderRadius: 999, position: "absolute" },

  stats: { flex: 1, gap: 3 },
  trackId: { ...type.footnote, color: colors.secondary, marginBottom: 2 },
  statRow: { flexDirection: "row", justifyContent: "space-between" },
  statLabel: { ...type.footnote, color: colors.secondary },
  statValue: { ...type.footnote, color: colors.label, fontWeight: "600" },
  stateRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4 },
  stateDot: { width: 7, height: 7, borderRadius: 999 },
  stateText: { ...type.caption2, fontWeight: "700" },
  conf: { ...type.caption2, color: colors.secondary, marginLeft: "auto" },
});
