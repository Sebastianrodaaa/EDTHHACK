import React from "react";
import { StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";
import { BlurView } from "expo-blur";
import { colors, radius } from "../theme";

/**
 * iOS 26 "Liquid Glass" surface: real blur on iOS, translucent frosted
 * fallback elsewhere, with a hairline edge and soft top highlight.
 */
export function GlassCard({
  children,
  style,
  intensity = 28,
  radius: r = radius.card,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  intensity?: number;
  radius?: number;
}) {
  return (
    <View style={[styles.wrap, { borderRadius: r }, style]}>
      <BlurView intensity={intensity} tint="dark" style={StyleSheet.absoluteFill} />
      <View style={[StyleSheet.absoluteFill, styles.fill]} pointerEvents="none" />
      <View style={[StyleSheet.absoluteFill, { borderRadius: r }, styles.edge]} pointerEvents="none" />
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { overflow: "hidden", backgroundColor: colors.glass },
  fill: { backgroundColor: "rgba(255,255,255,0.02)" },
  edge: {
    borderWidth: 1,
    borderColor: colors.hairline,
    borderTopColor: colors.highlight,
  },
});
