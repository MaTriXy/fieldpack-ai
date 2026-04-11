/**
 * Centralized settings persistence layer.
 *
 * All user preferences are stored in localStorage with typed getters/setters.
 * Camera and text-size configs are read at call time — no re-render needed.
 */

// ── Types ──────────────────────────────────────────────────

export type Language = 'en' | 'fr' | 'wo' | 'pt'
export type CameraPreset = 'low' | 'medium' | 'high'
export type TextSize = 'small' | 'medium' | 'large'

export interface CameraConfig {
  quality: number
  width: number
  height: number
}

// ── Constants ──────────────────────────────────────────────

const KEYS = {
  language: 'fieldpack_language',
  cameraPreset: 'fieldpack_camera_quality',
  textSize: 'fieldpack_text_size',
} as const

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: 'English',
  fr: 'Français',
  wo: 'Wolof',
  pt: 'Português',
}

export const LANGUAGE_OPTIONS: Language[] = ['en', 'fr', 'wo', 'pt']

const CAMERA_CONFIGS: Record<CameraPreset, CameraConfig> = {
  low:    { quality: 60,  width: 512,  height: 512  },
  medium: { quality: 80,  width: 1024, height: 1024 },
  high:   { quality: 95,  width: 2048, height: 2048 },
}

export const CAMERA_LABELS: Record<CameraPreset, { label: string; desc: string }> = {
  low:    { label: 'Low',    desc: 'Faster (512px)' },
  medium: { label: 'Medium', desc: 'Balanced (1024px)' },
  high:   { label: 'High',   desc: 'Best quality (2048px)' },
}

export const CAMERA_OPTIONS: CameraPreset[] = ['low', 'medium', 'high']

export const TEXT_SIZE_LABELS: Record<TextSize, string> = {
  small: 'S',
  medium: 'M',
  large: 'L',
}

export const TEXT_SIZE_OPTIONS: TextSize[] = ['small', 'medium', 'large']

// ── Language ───────────────────────────────────────────────

export function getLanguage(): Language {
  const val = localStorage.getItem(KEYS.language)
  return (val && val in LANGUAGE_LABELS) ? val as Language : 'en'
}

export function setLanguage(lang: Language): void {
  localStorage.setItem(KEYS.language, lang)
}

// ── Camera ─────────────────────────────────────────────────

export function getCameraPreset(): CameraPreset {
  const val = localStorage.getItem(KEYS.cameraPreset)
  return (val && val in CAMERA_CONFIGS) ? val as CameraPreset : 'medium'
}

export function setCameraPreset(preset: CameraPreset): void {
  localStorage.setItem(KEYS.cameraPreset, preset)
}

export function getCameraConfig(): CameraConfig {
  return CAMERA_CONFIGS[getCameraPreset()]
}

// ── Text Size ──────────────────────────────────────────────

const TEXT_SIZE_CLASSES: Record<TextSize, string | null> = {
  small: 'text-size-sm',
  medium: null,
  large: 'text-size-lg',
}

export function getTextSize(): TextSize {
  const val = localStorage.getItem(KEYS.textSize)
  return (val && val in TEXT_SIZE_CLASSES) ? val as TextSize : 'medium'
}

export function setTextSize(size: TextSize): void {
  localStorage.setItem(KEYS.textSize, size)
}

export function applyTextSize(size: TextSize): void {
  const el = document.documentElement
  // Remove all text-size classes first
  el.classList.remove('text-size-sm', 'text-size-lg')
  const cls = TEXT_SIZE_CLASSES[size]
  if (cls) el.classList.add(cls)
}
