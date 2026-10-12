import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function resolveColor(colorName?: string | null): string {
  if (!colorName) return "transparent"
  const normalized = colorName.toLowerCase().trim()
  const map: Record<string, string> = {
    black: "#000000",
    white: "#ffffff",
    grey: "#6b7280",
    gray: "#6b7280",
    navy: "#1e3a8a",
    blue: "#2563eb",
    red: "#dc2626",
    green: "#16a34a",
    beige: "#f5f5dc",
    cream: "#fffdd0",
    brown: "#78350f",
    olive: "#556b2f",
    pink: "#ec4899",
    purple: "#9333ea",
    yellow: "#eab308",
    orange: "#ea580c",
  }
  return map[normalized] || normalized
}
