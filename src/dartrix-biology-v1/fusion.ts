// src/dartrix-biology-v1/fusion.ts
// FUSION — warstwa łącząca sensory i motorykę w jeden strumień stanu

import {
  type AxisEarBreathState,
  type SpineAxis,
  computeAxisEarBreath,
} from "./runtimeAxisEarBreath"

import {
  computePhiD,
  computeShoulderCircle,
} from "./phiDeltoid"

export interface SensoryInput {
  dermatome: Record<string, number> // np. { C5: 0.3, C6: 0.1 }
  proprioception: number            // 0–1
  visionStability: number           // 0–1
}

export interface MotorOutput {
  myotome: Record<string, number>   // np. { C5: 0.4, C6: 0.2 }
  activation: number                // 0–1
}

export interface FusionState {
  axis: AxisEarBreathState
  sensory: SensoryInput
  motor: MotorOutput
  phiD: number
  circleLoad: number
  fusionScore: number
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

export function computeFusion(
  spine: SpineAxis,
  diaphragmDepth: number,
  sensory: SensoryInput,
  motor: MotorOutput,
  m: number,
  shoulderRadius: number
): FusionState {

  const axis = computeAxisEarBreath(spine, diaphragmDepth)

  const phiD = computePhiD(m)
  const shoulder = computeShoulderCircle(shoulderRadius)

  const fusionScore = clamp01(
    0.25 * (1 - axis.resonanceError) +
    0.25 * axis.ear.vestibularBalance +
    0.20 * sensory.proprioception +
    0.15 * sensory.visionStability +
    0.15 * motor.activation
  )

  return {
    axis,
    sensory,
    motor,
    phiD,
    circleLoad: shoulder.circumference * phiD,
    fusionScore,
  }
}
