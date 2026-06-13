// src/dartrix-biology-v1/dartrixXirtrad.ts
//
// XIRTRAD – operator osiowy DARTRIX
// warstwa: tożsamość • intencja • sterowanie Φ_total

import {
  computePhiTotal,
  type PhiTotalParams,
  type PhiTotalOutput,
} from './dartrixBioCore'

export interface XirtradIdentity {
  id: string          // unikalny identyfikator operatora
  label: string       // etykieta (np. "anomynous", "CommanderX")
  seed: number        // ziarno deterministyczne dla sesji
}

export interface XirtradAxisState {
  focus: number       // 0..1 – skupienie osiowe
  calm: number        // 0..1 – poziom wyciszenia
  intent: number      // 0..1 – siła intencji
}

export interface XirtradInput {
  identity: XirtradIdentity
  axis: XirtradAxisState
  phiParams: PhiTotalParams
}

export interface XirtradOutput {
  identity: XirtradIdentity
  axis: XirtradAxisState
  phi: PhiTotalOutput
  phiScaled: number   // Φ_total przeskalowane przez stan osiowy
}

export function runXirtrad(
  input: XirtradInput,
): XirtradOutput {
  const { identity, axis, phiParams } = input

  const phi = computePhiTotal(phiParams)

  const axisFactor =
    0.5 +
    0.5 * (
      clamp01(axis.focus) *
      clamp01(axis.calm) *
      clamp01(axis.intent)
    )

  const phiScaled = phi.phiTotal * axisFactor

  return {
    identity,
    axis,
    phi,
    phiScaled,
  }
}

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x))
}
