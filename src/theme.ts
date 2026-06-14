import { Platform, TextStyle } from "react-native";

// iOS 26 "Liquid Glass" inspired palette (dark). System colors, label tints,
// translucent glass surfaces and hairline separators.
export const colors = {
  bg: "#000000",
  bgElevated: "#0B0B0D",

  // Glass surfaces (translucent — sit over BlurView)
  glass: "rgba(28,28,30,0.55)",
  glassStrong: "rgba(44,44,46,0.72)",
  fill: "rgba(120,120,128,0.16)", // iOS systemFill (dark)
  fillSecondary: "rgba(120,120,128,0.24)",

  // Separators / hairlines
  hairline: "rgba(255,255,255,0.08)",
  hairlineStrong: "rgba(255,255,255,0.16)",
  highlight: "rgba(255,255,255,0.14)",

  // Labels (iOS dark)
  label: "#FFFFFF",
  secondary: "rgba(235,235,245,0.6)",
  tertiary: "rgba(235,235,245,0.3)",
  quaternary: "rgba(235,235,245,0.18)",

  // System colors (dark variants)
  red: "#FF453A",
  redSoft: "#FF6961",
  green: "#30D158",
  blue: "#0A84FF",
  yellow: "#FFD60A",
  orange: "#FF9F0A",

  white: "#F2F2F7",
} as const;

// System font (SF Pro on iOS, Roboto on Android, system stack on web).
export const font = Platform.select({
  ios: "System",
  android: "sans-serif",
  default:
    '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif',
}) as string;

type T = TextStyle;
export const type: Record<string, T> = {
  largeTitle: { fontFamily: font, fontSize: 32, fontWeight: "700", letterSpacing: 0.2 },
  title2: { fontFamily: font, fontSize: 22, fontWeight: "700", letterSpacing: 0.2 },
  title3: { fontFamily: font, fontSize: 20, fontWeight: "600" },
  headline: { fontFamily: font, fontSize: 17, fontWeight: "600" },
  body: { fontFamily: font, fontSize: 17, fontWeight: "400" },
  callout: { fontFamily: font, fontSize: 16, fontWeight: "400" },
  subhead: { fontFamily: font, fontSize: 15, fontWeight: "400" },
  footnote: { fontFamily: font, fontSize: 13, fontWeight: "400" },
  caption: { fontFamily: font, fontSize: 12, fontWeight: "400" },
  caption2: { fontFamily: font, fontSize: 11, fontWeight: "500" },
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const radius = { card: 24, control: 16, chip: 9, pill: 999 } as const;
