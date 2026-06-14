import { Pressable, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { AcousticOrb } from "./src/components/AcousticOrb";
import { ReasoningTrail } from "./src/components/ReasoningTrail";
import { GlassCard } from "./src/components/GlassCard";
import { useAppStore } from "./src/store";
import { colors, radius, space, type } from "./src/theme";

function Screen() {
  const mode = useAppStore((s) => s.mode);
  const toggle = useAppStore((s) => s.toggle);
  const red = mode === "red";
  const accent = red ? colors.red : colors.green;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right", "bottom"]}>
      <StatusBar style="light" />

      <View style={styles.header}>
        <GlassCard radius={radius.pill} style={styles.pill}>
          <View style={styles.pillInner}>
            <View style={[styles.pillDot, { backgroundColor: accent }]} />
            <Text style={[styles.pillText, { color: accent }]}>
              {red ? "Detection" : "Nominal"}
            </Text>
          </View>
        </GlassCard>
      </View>

      <Pressable style={styles.orbSection} onPress={toggle}>
        <AcousticOrb mode={mode} />
        <Text style={[styles.orbStatus, { color: red ? colors.red : colors.label }]}>
          {red ? "Drone-like signature" : "Listening — clear"}
        </Text>
        <Text style={styles.hint}>
          Tap to {red ? "stand down" : "simulate detection"}
        </Text>
      </Pressable>

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
    justifyContent: "flex-end",
    paddingTop: space.sm,
    paddingBottom: space.xs,
  },

  pill: { alignSelf: "flex-end" },
  pillInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  pillDot: { width: 8, height: 8, borderRadius: 999 },
  pillText: { ...type.footnote, fontWeight: "600" },

  orbSection: { alignItems: "center", justifyContent: "center", gap: 4, paddingVertical: space.md },
  orbStatus: { ...type.title3, marginTop: 4 },
  hint: { ...type.subhead, color: colors.tertiary },

  trailSection: { flex: 1, paddingBottom: space.md },
});
