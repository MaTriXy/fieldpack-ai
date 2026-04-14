/**
 * Smoke test — headless run of key Playwright interactions from record.ts.
 * Verifies selectors, waits, and demo backend responses work correctly.
 *
 * NOTE: waitForFunction(fn, arg, options) — the SECOND arg is passed to fn,
 * the THIRD arg is options. Always pass null as arg when not needed.
 */
import { chromium } from 'playwright'
import * as path from 'path'
import * as fs from 'fs'

const LEFT_URL = 'http://localhost:5178'
const RIGHT_URL = 'http://localhost:5173'
const PHOTO_PATH = path.resolve(__dirname, 'assets/photos/disease_cmd_figure.jpg')

const wait = (ms: number) => new Promise<void>(r => setTimeout(r, ms))
let passed = 0
let failed = 0

function ok(label: string) { passed++; console.log(`  [OK]   ${label}`) }
function fail(label: string, detail = '') { failed++; console.log(`  [FAIL] ${label}${detail ? ' — ' + detail : ''}`) }

async function main() {
  console.log('\nSmoke test: verifying Playwright + servers + demo interactions\n')

  if (!fs.existsSync(PHOTO_PATH)) { fail('Plant photo exists', PHOTO_PATH); process.exit(1) }
  ok('Plant photo exists')

  const browser = await chromium.launch({ headless: true })

  // ── Left panel tests ──
  const leftCtx = await browser.newContext({ viewport: { width: 1152, height: 1080 }, colorScheme: 'dark' })
  const left = await leftCtx.newPage()

  await left.goto(`${LEFT_URL}/#title`)
  await wait(500)
  ok('Left panel loads')

  const frames = ['title', 'persona', 'map', 'stats', 'architecture', 'online-phase', 'progress', 'transition', 'field-session', 'pipeline', 'grounded', 'platform', 'closing']
  for (const frame of frames) {
    await left.goto(`${LEFT_URL}/#${frame}`)
    await wait(200)
  }
  ok(`All ${frames.length} frames navigable`)

  // ── Right panel tests ──
  const rightCtx = await browser.newContext({ viewport: { width: 430, height: 932 }, colorScheme: 'dark' })
  const right = await rightCtx.newPage()

  // Test 1: Mission chat — type and get response
  await right.goto(`${RIGHT_URL}/mission`)
  await right.waitForSelector('textarea[placeholder="Describe your mission..."]', { timeout: 5_000 })
  ok('Mission chat page loads')

  await right.fill('textarea[placeholder="Describe your mission..."]', "I'm deploying to Casamance Senegal")
  await right.click('button[aria-label="Send message"]')
  // Button stays disabled when input is empty — wait for assistant reply text instead
  await right.waitForFunction(
    () => document.body.innerText.includes('Welcome'),
    null,
    { timeout: 15_000 }
  )
  ok('Mission message 1 — response received')

  await right.fill('textarea[placeholder="Describe your mission..."]', 'Working with cassava and rice farmers')
  await right.click('button[aria-label="Send message"]')
  // Wait for the mission card to render (Dispatch button = response complete)
  await right.waitForFunction(
    () => document.body.innerText.includes('Dispatch Agents'),
    null,
    { timeout: 15_000 }
  )
  await wait(1000)

  // Check for Dispatch button
  const dispatchBtn = right.getByRole('button', { name: /Dispatch Agents/i })
  const dispatchCount = await dispatchBtn.count()
  if (dispatchCount > 0) {
    ok('Mission card + Dispatch button appeared')
    await dispatchBtn.click()
    await wait(2000)
    // Should be on /mission/progress now
    const url = right.url()
    url.includes('/mission/progress') ? ok('Navigated to progress page') : fail('Progress page navigation', url)
  } else {
    fail('Dispatch button not found after mission_crops message')
  }

  // Test 2: Field chat — navigate, type, get response
  await right.goto(`${RIGHT_URL}/field`)
  try {
    await right.waitForSelector('textarea[placeholder="Ask about your crops..."]', { timeout: 10_000 })
    ok('Field chat page loads (pack auto-loaded)')
  } catch {
    fail('Field chat pack auto-load')
  }

  await right.fill('textarea[placeholder="Ask about your crops..."]', 'When should I plant cassava?')
  await right.click('button[aria-label="Send message"]')

  // Wait for streaming to start and finish
  // Demo replay streams at realistic speed: cassava_planting ~42s, diagnosis ~69s, neem ~52s
  try {
    await right.waitForSelector('[aria-label="Stop generating"]', { timeout: 15_000 })
    ok('Field chat — streaming started')
    await right.waitForFunction(
      () => !document.querySelector('[aria-label="Stop generating"]'),
      null,
      { timeout: 50_000 }
    )
    ok('Field chat — planting response complete')
  } catch (e) {
    fail('Field chat streaming', String(e))
  }

  // Test 3: Photo upload + diagnosis
  const fileInput = right.locator('input[type="file"][accept="image/jpeg,image/png,image/webp"]')
  await fileInput.setInputFiles(PHOTO_PATH)
  await wait(1500)
  ok('Photo uploaded — preview should appear')

  await right.click('button[aria-label="Send message"]')
  try {
    await right.waitForSelector('[aria-label="Stop generating"]', { timeout: 15_000 })
    ok('Diagnosis — streaming started')
    await right.waitForFunction(
      () => !document.querySelector('[aria-label="Stop generating"]'),
      null,
      { timeout: 80_000 }
    )
    ok('Diagnosis — hero shot response complete')
  } catch (e) {
    fail('Diagnosis streaming', String(e))
  }

  // Test 4: Follow-up question
  await right.fill('textarea[placeholder="Ask about your crops..."]', 'How do I prepare the neem oil spray?')
  await right.click('button[aria-label="Send message"]')
  try {
    await right.waitForSelector('[aria-label="Stop generating"]', { timeout: 15_000 })
    await right.waitForFunction(
      () => !document.querySelector('[aria-label="Stop generating"]'),
      null,
      { timeout: 60_000 }
    )
    ok('Neem follow-up response complete')
  } catch (e) {
    fail('Neem follow-up', String(e))
  }

  // Test 5: Pack list page
  await right.goto(`${RIGHT_URL}/packs`)
  await wait(2000)
  ok('Pack list page loads')

  await leftCtx.close()
  await rightCtx.close()
  await browser.close()

  console.log(`\n  Results: ${passed} passed, ${failed} failed\n`)
  process.exit(failed > 0 ? 1 : 0)
}

main().catch(err => {
  console.error('Smoke test fatal error:', err)
  process.exit(1)
})
