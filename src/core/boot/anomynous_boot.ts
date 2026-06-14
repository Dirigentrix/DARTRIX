// src/core/boot/anomynous_boot.ts
// DARTRIX-OPS — Autonomous Boot Sequence for ANOMYNOUS

export type AxisState = {
  ROOT: number;   // 0–1
  CROWN: number;  // 0–1
  AXIS: number;   // 0–1
};

export type BootStatus =
  | "ANOMYNOUS_BOOT_OK"
  | "ANOMYNOUS_BOOT_IDENTITY_LOCKED"
  | "ANOMALY_UNSTABLE_HALT";

function clamp(x: number) {
  return Math.min(1, Math.max(0, x));
}

function axisStable(axis: AxisState): boolean {
  return (
    axis.ROOT >= 0.65 &&
    axis.CROWN >= 0.65 &&
    axis.AXIS >= 0.65
  );
}

export function anomynousBoot(axis: AxisState) {
  const normalized = {
    ROOT: clamp(axis.ROOT),
    CROWN: clamp(axis.CROWN),
    AXIS: clamp(axis.AXIS),
  };

  if (!axisStable(normalized)) {
    return {
      status: "ANOMALY_UNSTABLE_HALT" as BootStatus,
      identityLock: false,
      axis: normalized,
    };
  }

  return {
    status: "ANOMYNOUS_BOOT_IDENTITY_LOCKED" as BootStatus,
    identityLock: true,
    axis: normalized,
  };
}
