import React from "react";
import { View } from "react-native";
import { Canvas, Fill, Shader, Skia } from "@shopify/react-native-skia";
import { useDerivedValue } from "react-native-reanimated";
import { useAcousticDrive } from "../acoustic/useAcousticDrive";
import type { OrbMode } from "../store";

const SIZE = 280;

/**
 * Liquid-glass acoustic sphere rendered with a Skia RuntimeEffect (SkSL).
 *
 * The shader composes, per pixel:
 *   - a shaded 3D sphere (diffuse + Blinn-Phong specular highlight)
 *   - an animated liquid boundary driven by acoustic energy (fbm noise)
 *   - a fresnel rim that reads as a refractive glass edge
 *   - an outer bloom glow + concentric sonar rings (energetic when active)
 *   - a calm white <-> alert red palette morph (u_red)
 */
const SKSL = `
uniform float2 u_resolution;
uniform float  u_time;
uniform float  u_level;
uniform float  u_low;
uniform float  u_high;
uniform float  u_red;

float hash(float2 p){ return fract(sin(dot(p, float2(127.1, 311.7))) * 43758.5453123); }

float vnoise(float2 p){
  float2 i = floor(p);
  float2 f = fract(p);
  float2 u = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + float2(1.0, 0.0));
  float c = hash(i + float2(0.0, 1.0));
  float d = hash(i + float2(1.0, 1.0));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(float2 p){
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++){
    v += a * vnoise(p);
    p = p * 2.02;
    a *= 0.5;
  }
  return v;
}

half4 main(float2 fragcoord){
  float2 res = u_resolution;
  float m = min(res.x, res.y);
  float2 uv = (fragcoord - 0.5 * res) / m;   // ~[-0.5, 0.5]
  float r = length(uv);
  float ang = atan(uv.y, uv.x);

  // Liquid boundary: angular fbm warped over time, modulated by low band.
  float wob = fbm(float2(cos(ang) * 1.6 + u_time * 0.25,
                         sin(ang) * 1.6 - u_time * 0.22));
  float baseR = 0.295 + 0.010 * sin(u_time * 1.3);
  float R = baseR + (0.012 + 0.05 * u_low) * (wob - 0.5);

  // Fake sphere normal inside R.
  float inside = R * R - r * r;
  float z = sqrt(max(inside, 0.0));
  float3 n = normalize(float3(uv, z / max(R, 0.0001)));
  float3 L = normalize(float3(-0.45, -0.65, 0.78));
  float3 V = float3(0.0, 0.0, 1.0);
  float diff = clamp(dot(n, L), 0.0, 1.0);
  float3 H = normalize(L + V);
  float spec = pow(clamp(dot(n, H), 0.0, 1.0), 48.0);

  // Inner turbulence texture.
  float surf = fbm(uv * 6.0 + float2(u_time * 0.3, -u_time * 0.2));

  // Palette: calm (cool white) -> alert (red).
  float3 calm     = float3(0.95, 0.97, 1.00);
  float3 calmDeep = float3(0.42, 0.58, 0.82);
  float3 hot      = float3(1.00, 0.34, 0.29);
  float3 hotDeep  = float3(0.50, 0.04, 0.05);
  float3 baseCol  = mix(calm, hot, u_red);
  float3 deepCol  = mix(calmDeep, hotDeep, u_red);

  float3 body = mix(deepCol, baseCol, diff * 0.82 + 0.18);
  body += 0.16 * (surf - 0.5);
  body += spec * 0.95;

  // Fresnel rim (glass edge).
  float fres = pow(1.0 - clamp(z / max(R, 0.0001), 0.0, 1.0), 2.6);
  float3 rimCol = mix(float3(0.70, 0.85, 1.00), float3(1.00, 0.52, 0.46), u_red);
  body += fres * rimCol * (0.55 + 0.65 * u_red);

  float sphereMask = smoothstep(0.0035, -0.0035, r - R);

  // Outer bloom.
  float glow = exp(-(r - R) * (10.0 - 3.5 * u_level));
  glow = clamp(glow, 0.0, 1.0) * (1.0 - sphereMask);
  float3 glowCol = mix(float3(0.45, 0.68, 1.00), float3(1.00, 0.32, 0.28), u_red);
  float glowI = 0.12 + 0.55 * u_level;

  // Concentric sonar rings (faster + brighter when active).
  float rings = 0.0;
  float speed = mix(0.5, 1.7, u_red);
  for (int i = 0; i < 3; i++){
    float prog = fract(u_time * speed * 0.28 + float(i) * 0.34);
    float ringR = R + prog * 0.19;
    float line = smoothstep(0.012, 0.0, abs(r - ringR));
    rings += line * (1.0 - prog) * (1.0 - sphereMask);
  }

  float3 col = body * sphereMask;
  col += glowCol * glow * glowI;
  col += glowCol * rings * (0.20 + 0.55 * u_red) * (0.4 + u_high);

  float alpha = clamp(sphereMask + glow * glowI * 1.4 + rings * 0.5, 0.0, 1.0);

  // Circular vignette so the glow fades to fully transparent before the
  // rectangular canvas edge (prevents a visible square halo).
  float vignette = smoothstep(0.5, 0.4, r);
  col *= vignette;
  alpha *= vignette;

  return half4(half3(col), half(alpha));
}
`;

const effect = Skia.RuntimeEffect.Make(SKSL);
if (!effect) {
  // Surfaces a clear error during development if the SkSL fails to compile.
  console.error("AcousticOrb: failed to compile SkSL shader");
}

export function AcousticOrb({ mode, size = SIZE }: { mode: OrbMode; size?: number }) {
  const active = mode === "red";
  const { time, level, low, high, red } = useAcousticDrive(active);

  const uniforms = useDerivedValue(() => ({
    u_resolution: [size, size],
    u_time: time.value,
    u_level: level.value,
    u_low: low.value,
    u_high: high.value,
    u_red: red.value,
  }), [size]);

  return (
    <View style={{ width: size, height: size }}>
      <Canvas style={{ flex: 1 }}>
        {effect ? (
          <Fill>
            <Shader source={effect} uniforms={uniforms} />
          </Fill>
        ) : null}
      </Canvas>
    </View>
  );
}
