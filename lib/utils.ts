import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Safely resolve a product color to a CSS-friendly value.
// - Handles undefined/null by returning a neutral gray.
// - Maps a few brand color names to hex for consistency.
// - Returns valid hex or CSS color names unchanged (case-insensitive).
export function resolveColor(color?: string | null): string {
  if (!color) return "#E5E7EB" // gray-200 as fallback
  const c = String(color).trim().toLowerCase()

  const map: Record<string, string> = {
    beige: "#F5F5DC",
    navy: "#000080",
    burgundy: "#800020",
    pink: "#FFC0CB",
  }

  if (map[c]) return map[c]

  // If it's a hex value, return as-is
  if (/^#([0-9a-f]{3}){1,2}$/i.test(color)) return color

  // Otherwise, assume it's a valid CSS color name
  return c
}
