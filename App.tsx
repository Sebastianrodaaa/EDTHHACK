import { Pressable, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { AcousticOrb } from "./src/components/AcousticOrb";
import { ReasoningTrail } from "./src/components/ReasoningTrail";
import { ThreatPanel } from "./src/components/ThreatPanel";
import { TrackingOverlay } from "./src/components/TrackingOverlay";
import { GlassCard } from "./src/components/GlassCard";
import { useAppStore } from "./src/store";
import { useServerEvents } from "./src/transport/useServerEvents";
import { startScenario, resetScenario } from "./src/transport/api";
import { DEMO_SCENARIO } from "./src/config";
import { colors, radius, space, type } from "./src/theme";

function Screen() {
  useServerEvents();

  const mode = useAppStore((s) => s.mode);
  const connected = useAppStore((s) => s.connected);
  const scenarioActive = useAppStore((s) => s.scenarioActive);
  const red = mode === "red";
  const accent = red ? colors.red : colors.green;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right", "bottom"]}>
      <StatusBar style="light" />

      <View style={styles.header}>
        <GlassCard radius={radius.pill} style={styles.pill}>
          <View style={styles.pillInner}>
            <View
              style={[
                styles.pillDot,
                { backgroundColor: connected ? colors.green : colors.tertiary },
              ]}
            />
            <Text
              style={[
                styles.pillText,
                { color: connected ? colors.green : colors.tertiary },
              ]}
            >
              {connected ? "Live" : "Offline"}
            </Text>
          </View>
        </GlassCard>

        <GlassCard radius={radius.pill} style={styles.pill}>
          <View style={styles.pillInner}>
            <View style={[styles.pillDot, { backgroundColor: accent }]} />
            <Text style={[styles.pillText, { color: accent }]}>
              {red ? "Detection" : "Nominal"}
            </Text>
          </View>
        </GlassCard>
      </View>

      <View style={styles.orbSection}>
        <AcousticOrb mode={mode} />
        <Text style={[styles.orbStatus, { color: red ? colors.red : colors.label }]}>
          {red ? "Drone-like signature" : "Listening — clear"}
        </Text>

        <View style={styles.controls}>
          <Pressable
            onPress={() => startScenario(DEMO_SCENARIO)}
            style={({ pressed }) => [styles.ctrlBtn, styles.ctrlPrimary, pressed && styles.pressed]}
          >
            <Text style={styles.ctrlPrimaryText}>
              {scenarioActive ? "Restart scenario" : "Run scenario"}
            </Text>
          </Pressable>
          <Pressable
            onPress={() => resetScenario()}
            style={({ pressed }) => [styles.ctrlBtn, styles.ctrlGhost, pressed && styles.pressed]}
          >
            <Text style={styles.ctrlGhostText}>Reset</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.threatSection}>
        <TrackingOverlay />
        <ThreatPanel />
      </View>

      <View style={styles.trailSection}>
        <ReasoningTrail />
      </View>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <Screen />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg, paddingHorizontal: space.lg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: space.sm,
    paddingBottom: space.xs,
  },

  pill: { alignSelf: "flex-start" },
  pillInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  pillDot: { width: 8, height: 8, borderRadius: 999 },
  pillText: { ...type.footnote, fontWeight: "600" },

  orbSection: { alignItems: "center", justifyContent: "center", gap: 4, paddingVertical: space.xs },
  orbStatus: { ...type.title3, marginTop: 2 },

  controls: { flexDirection: "row", gap: space.sm, marginTop: space.sm },
  ctrlBtn: {
    height: 40,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 22,
  },
  ctrlPrimary: { backgroundColor: colors.white },
  ctrlPrimaryText: { ...type.subhead, fontWeight: "700", color: "#0B0B0D" },
  ctrlGhost: { borderWidth: 1, borderColor: colors.hairlineStrong },
  ctrlGhostText: { ...type.subhead, fontWeight: "600", color: colors.label },
  pressed: { opacity: 0.6 },

  threatSection: { paddingVertical: space.xs, gap: space.sm },
  trailSection: { flex: 1, paddingBottom: space.md, paddingTop: space.xs },
});
