export function computePhiD(m: number): number {
  return m * 1.618;
}

export interface ShoulderCircle {
  circumference: number;
}

export function computeShoulderCircle(radius: number): ShoulderCircle {
  return {
    circumference: 2 * Math.PI * radius
  };
}
