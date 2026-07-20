import React, { useEffect, useRef } from "react";
import {
  liquidMetalFragmentShader,
  ShaderMount,
  type ShaderMountUniforms,
} from "@paper-design/shaders";

interface LiquidMetalProps {
  className?: string;
  config?: Partial<ShaderMountUniforms>;
}

export default function LiquidMetal({ className = "", config }: LiquidMetalProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const defaultConfig = {
      u_repetition: 1.5,
      u_softness: 0.5,
      u_shiftRed: 0.3,
      u_shiftBlue: 0.3,
      u_distortion: 0,
      u_contour: 0,
      u_angle: 100,
      u_scale: 1.5,
      u_shape: 1,
      u_offsetX: 0.1,
      u_offsetY: -0.1,
    };

    const shaderConfig = config ? { ...defaultConfig, ...config } : defaultConfig;

    const mount = new ShaderMount(
      containerRef.current,
      liquidMetalFragmentShader,
      shaderConfig,
      undefined,
      0.6,
    );

    return () => {
      mount.dispose();
    };
  }, [config]);

  // We set pointer-events-none so it acts purely as a visual background
  return (
    <div
      ref={containerRef}
      className={`pointer-events-none absolute inset-0 ${className}`}
      style={{ overflow: "hidden" }}
    />
  );
}
