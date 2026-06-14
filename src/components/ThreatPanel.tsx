import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, radius, space, type } from "../theme";
import { GlassCard } from "./GlassCard";
import {
  useAppStore,
  type OperatorActionType,
  type ThreatLevel,
} from "../store";
import { sendOperatorAction } from "../transport/api";

const THREAT_COLOR: Record<ThreatLevel, string> = {
  low: colors.green,
  medium: colors.yellow,
  high: colors.orange,
  critical: colors.red,
};

const ACTION_LABEL: Record<string, string> = {
  monitor: "Monitor",
  request_visual: "Request visual confirmation",
  alert_squad: "Alert squad",
  prepare_countermeasures: "Prepare countermeasures",
  dispatch_counter_uas: "Dispatch counter-UAS resources",
};

function withAlpha(c: string, a: number) {
  if (c[0] !== "#" || c.length < 7) return c;
  const r = parseInt(c.slice(1, 3), 16);
  const g = parseInt(c.slice(3, 5), 16);
  const b = parseInt(c.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function Meter({ label, value, tint }: { label: string; value: number | null; tint: string }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <View style={styles.meterRow}>
      <Text style={styles.meterLabel}>{label}</Text>
      <View style={styles.meterTrack}>
        <View
          style={[
            styles.meterFill,
            { width: `${pct}%`, backgroundColor: value == null ? colors.tertiary : tint },
          ]}
        />
      </View>
      <Text style={styles.meterValue}>{value == null ? "—" : `${pct}%`}</Text>
    </View>
  );
}

function ActionButton({
  label,
  tint,
  filled,
  onPress,
}: {
  label: string;
  tint: string;
  filled?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.btn,
        filled ? { backgroundColor: tint } : { borderColor: withAlpha(tint, 0.5), borderWidth: 1 },
        pressed && styles.btnPressed,
      ]}
    >
      <Text style={[styles.btnText, { color: filled ? "#0B0B0D" : tint }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressable>
  );
}

export function ThreatPanel() {
  const assessment = useAppStore((s) => s.assessment);
  const threatLevel = useAppStore((s) => s.threatLevel);
  const subsystems = useAppStore((s) => s.subsystems);

  const tint = THREAT_COLOR[threatLevel];
  const rec = assessment?.recommendation;
  const sourceLabel =
    assessment?.source_mode === "acoustic_only"
      ? "acoustic-only"
      : assessment?.source_mode === "vision_only"
      ? "live POV vision"
      : "sound + vision";

  const act = (action: OperatorActionType) =>
    sendOperatorAction(action, assessment?.id ?? null);

  return (
    <GlassCard style={styles.panel}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Threat assessment</Text>
        <View style={[styles.levelBadge, { backgroundColor: withAlpha(tint, 0.18) }]}>
          <View style={[styles.levelDot, { backgroundColor: tint }]} />
          <Text style={[styles.levelText, { color: tint }]}>{threatLevel.toUpperCase()}</Text>
        </View>
      </View>

      {assessment ? (
        <>
          <Meter label="Fused" value={assessment.confidence} tint={tint} />
          <Meter label="Acoustic" value={assessment.acoustic_confidence} tint={colors.blue} />
          <Meter label="Vision" value={assessment.vision_confidence} tint={colors.blue} />

          {assessment.tracking ? (
            <Text style={styles.bearing}>
              Bearing {Math.round(assessment.tracking.bearing_deg)}°
              {"  ·  "}
              {sourceLabel}
            </Text>
          ) : null}

          {rec ? (
            <View style={[styles.recCard, { borderColor: withAlpha(tint, 0.35) }]}>
              <Text style={[styles.recAction, { color: tint }]}>
                {ACTION_LABEL[rec.action] ?? rec.action}
              </Text>
              <Text style={styles.recMsg}>{rec.message}</Text>
            </View>
          ) : null}

          {assessment.dispatch ? (
            <View style={styles.dispatchCard}>
              <Text style={styles.dispatchTitle}>Resource dispatch</Text>
              <Text style={styles.dispatchLine}>{assessment.dispatch.effector}</Text>
              <Text style={styles.dispatchMeta}>
                {assessment.dispatch.resources.join(" · ")}
              </Text>
              <Text style={styles.dispatchMeta}>
                {assessment.dispatch.soldier_location} · ETA {assessment.dispatch.eta_s}s
              </Text>
            </View>
          ) : null}

          <View style={styles.actions}>
            {rec?.requires_confirmation ? (
              <ActionButton label="Confirm" tint={colors.green} filled onPress={() => act("confirm")} />
            ) : null}
            <ActionButton label="Escalate" tint={colors.orange} onPress={() => act("escalate")} />
            <ActionButton label="Stand down" tint={colors.secondary} onPress={() => act("stand_down")} />
          </View>
        </>
      ) : (
        <Text style={styles.idle}>No active threat — sensors nominal.</Text>
      )}

      <View style={styles.chips}>
        {Object.entries(subsystems).map(([name, status]) => (
          <SubsystemChip key={name} name={name} status={status} />
        ))}
      </View>
    </GlassCard>
  );
}

function SubsystemChip({ name, status }: { name: string; status: string }) {
  const color =
    status === "active"
      ? colors.blue
      : status === "online"
      ? colors.green
      : status === "degraded"
      ? colors.orange
      : colors.tertiary;
  return (
    <View style={styles.chip}>
      <View style={[styles.chipDot, { backgroundColor: color }]} />
      <Text style={styles.chipText}>{name}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { paddingHorizontal: space.lg, paddingVertical: space.md, gap: 8 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  title: { ...type.headline, color: colors.label },
  levelBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderRadius: radius.pill,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  levelDot: { width: 7, height: 7, borderRadius: 999 },
  levelText: { ...type.caption2, fontWeight: "700" },

  meterRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  meterLabel: { ...type.footnote, color: colors.secondary, width: 64 },
  meterTrack: {
    flex: 1,
    height: 6,
    borderRadius: 999,
    backgroundColor: colors.fill,
    overflow: "hidden",
  },
  meterFill: { height: 6, borderRadius: 999 },
  meterValue: { ...type.footnote, color: colors.label, width: 40, textAlign: "right" },

  bearing: { ...type.footnote, color: colors.secondary, marginTop: 2 },

  recCard: {
    borderWidth: 1,
    borderRadius: radius.control,
    padding: space.md,
    gap: 4,
    marginTop: 4,
    backgroundColor: "rgba(255,255,255,0.02)",
  },
  recAction: { ...type.callout, fontWeight: "700" },
  recMsg: { ...type.footnote, color: colors.secondary, lineHeight: 18 },

  dispatchCard: {
    borderRadius: radius.control,
    padding: space.md,
    gap: 3,
    backgroundColor: "rgba(255,59,48,0.10)",
    borderWidth: 1,
    borderColor: "rgba(255,59,48,0.30)",
  },
  dispatchTitle: { ...type.caption2, color: colors.red, fontWeight: "700", textTransform: "uppercase" },
  dispatchLine: { ...type.callout, color: colors.label, fontWeight: "700" },
  dispatchMeta: { ...type.footnote, color: colors.secondary },

  actions: { flexDirection: "row", gap: space.sm, marginTop: 4 },
  btn: {
    flex: 1,
    height: 40,
    borderRadius: radius.control,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  btnPressed: { opacity: 0.6 },
  btnText: { ...type.subhead, fontWeight: "600" },

  idle: { ...type.subhead, color: colors.secondary, paddingVertical: space.sm },

  chips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 6,
    paddingTop: space.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.hairline,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: colors.fill,
    borderRadius: radius.pill,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  chipDot: { width: 6, height: 6, borderRadius: 999 },
  chipText: { ...type.caption2, color: colors.secondary, textTransform: "capitalize" },
});
