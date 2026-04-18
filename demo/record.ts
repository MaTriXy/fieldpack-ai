/**
 * FieldPack AI — Demo Video Recording Orchestration
 *
 * Drives a SINGLE 1920x1080 browser window for OBS screen capture:
 *   Left  (1152x1080): video-frames app — hash-based frame changes
 *   Right (768x1080):  phone mockup with embedded frontend app (iframe)
 *
 * The video-frames app at :5178?mode=record renders both panels in one page.
 * Playwright changes left frames via URL hash and drives the phone iframe
 * via page.frame('phone-app').
 *
 * Prerequisites:
 *   1. Backend running with DEMO_MODE=true on :8003
 *   2. Frontend dev server on :5173
 *   3. Video-frames dev server on :5178
 *   4. OBS capturing the single browser window
 *
 * Run:  cd demo && npm run record
 * Dry:  cd demo && npm run record:dry   (prints timeline, no browser)
 */

import { chromium, type Page, type Frame } from 'playwright'
import * as path from 'path'
import * as fs from 'fs'

// ─── Config ──────────────────────────────────────────────────────────────────

const RECORDING_URL = 'http://localhost:5178/?mode=record'
const PHOTO_PATH = path.resolve(__dirname, 'assets/photos/disease_cmd_field.jpg')

// Single window at full HD
const WIDTH = 1920
const HEIGHT = 1080

// Typing speed: characters per keystroke delay (ms)
const TYPING_DELAY = 45

const DRY_RUN = process.argv.includes('--dry-run')

// ─── Timeline ────────────────────────────────────────────────────────────────

interface Scene {
  id: string
  startSec: number
  endSec: number
  leftFrame: string | null   // hash fragment, or null = no change
  rightAction: (ctx: Context) => Promise<void>
}

interface Context {
  page: Page           // the main page (video-frames recording page)
  phone: Frame         // the iframe containing the frontend app
  log: (msg: string) => void
}

// Helper: wait for a duration in milliseconds
const wait = (ms: number) => new Promise<void>(r => setTimeout(r, ms))

// Helper: type character by character (cinematic feel)
async function typeSlowly(frame: Frame, selector: string, text: string, delayMs = TYPING_DELAY) {
  await frame.click(selector)
  await frame.type(selector, text, { delay: delayMs })
}

// Helper: wait until streaming response finishes (stop button disappears)
async function waitForResponseDone(frame: Frame, timeoutMs = 30_000) {
  // Wait for the stop button to appear (streaming started).
  // Use a short timeout — if the button already appeared and vanished, fall through quickly.
  await frame.waitForSelector('[aria-label="Stop generating"]', { timeout: 1_000 }).catch(() => {})
  // Then wait for it to disappear (streaming finished)
  await frame.waitForFunction(
    () => !document.querySelector('[aria-label="Stop generating"]'),
    null,
    { timeout: timeoutMs }
  )
  // Small settle time for final rendering
  await wait(500)
}

// Helper: wait for mission chat response by checking for expected text
async function waitForMissionResponse(frame: Frame, expectedText: string, timeoutMs = 15_000) {
  await frame.waitForFunction(
    (text: string) => document.body.innerText.includes(text),
    expectedText,
    { timeout: timeoutMs }
  )
  await wait(500)
}

const SCENES: Scene[] = [
  // ────────────────────────────────────────────────────────────────────────
  // SCENE 1: Title Card (0:00–0:03) — tight logo intro, no cold-open
  {
    id: 'title-card',
    startSec: 0,
    endSec: 3,
    leftFrame: 'title',
    rightAction: async ({ phone, log }) => {
      await phone.waitForSelector('button:has-text("Get Started")', { timeout: 3_000 })
      log('Onboarding: Welcome slide ready')
      // Hold the Welcome slide stably until persona scene takes over
      await wait(2500)
    },
  },

  // SCENE 2: Amina's Profile (0:03–0:13)
  // Swipe through onboarding: Hero Workflow → Three Modes
  {
    id: 'persona',
    startSec: 3,
    endSec: 13,
    leftFrame: 'persona',
    rightAction: async ({ phone, log }) => {
      // Guard: Welcome slide must still be showing its nav button
      await phone.waitForSelector('button:has-text("Get Started")', { timeout: 5_000 })
      // Click "Get Started" → Hero Workflow (slide 1)
      await phone.locator('button:has-text("Get Started")').click()
      log('Onboarding: Hero Workflow slide')
      // Wait for slide animation to complete, then hold on slide 1 so the viewer sees it
      await wait(400)

      // Dwell on Hero Workflow for ~3.5s so it reads on screen
      await wait(3500)

      // Click "How it works" → Three Modes (slide 2)
      await phone.waitForSelector('button:has-text("How it works")', { timeout: 3_000 })
      await phone.locator('button:has-text("How it works")').click()
      log('Onboarding: Three Modes slide')
      // Wait for slide animation, then hold so the viewer sees Three Modes briefly
      await wait(400)
      await wait(1200)
    },
  },

  // SCENE 3: The Map (0:13–0:20)
  // Continue onboarding: Three Modes visible at start → Knowledge Packs slide
  {
    id: 'map',
    startSec: 13,
    endSec: 20,
    leftFrame: 'map',
    rightAction: async ({ phone, log }) => {
      // Dwell on Three Modes slide for 2s so the viewer can read it
      await wait(2000)
      // Click "Got it" → Knowledge Packs (slide 3)
      await phone.waitForSelector('button:has-text("Got it")', { timeout: 3_000 })
      await phone.locator('button:has-text("Got it")').click()
      log('Onboarding: Knowledge Packs slide')
      // Wait for slide animation to settle, then hold so the viewer sees the pack card
      await wait(400)
      await wait(2000)
    },
  },

  // SCENE 4: Impact Stats (0:20–0:30)
  // Finish onboarding: Knowledge Packs visible at start → Connect slide → auto-connects → "Get Started"
  {
    id: 'stats',
    startSec: 20,
    endSec: 30,
    leftFrame: 'stats',
    rightAction: async ({ phone, log }) => {
      // Dwell on Knowledge Packs slide so the viewer can read the pack card
      await wait(3500)
      // Click "Connect" bottom nav button → Connect slide (slide 4)
      // Use .first() to be explicit — the nav button is the primary "Connect" on this slide
      await phone.waitForSelector('button:has-text("Connect")', { timeout: 3_000 })
      await phone.locator('button:has-text("Connect")').first().click()
      log('Onboarding: Connect slide')
      // Wait for slide animation to settle
      await wait(400)

      // In browser mode connection status starts as "connected", so "FieldStation Found!"
      // renders immediately. Wait for it, then click "Get Started" in the connected-state content.
      try {
        await phone.waitForFunction(
          () => document.body.innerText.includes('FieldStation Found'),
          null,
          { timeout: 6_000 }
        )
        log('FieldStation found! Holding for viewer...')
        // Let the viewer read the connected state for a beat
        await wait(1500)
        log('Clicking Get Started to complete onboarding...')
        // The only "Get Started" visible on slide 4 is inside the connected-state content area
        await phone.waitForSelector('button:has-text("Get Started")', { timeout: 3_000 })
        await phone.locator('button:has-text("Get Started")').click()
        log('Onboarding complete — navigating to HomePage')
      } catch {
        log('Connection timeout — clicking Skip setup')
        await phone.waitForSelector('button:has-text("Skip setup")', { timeout: 3_000 })
        await phone.locator('button:has-text("Skip setup")').click()
      }
    },
  },

  // SCENE 5: Architecture (0:30–0:40)
  // HomePage — pack loaded, system status visible
  {
    id: 'architecture',
    startSec: 30,
    endSec: 40,
    leftFrame: 'architecture',
    rightAction: async ({ phone, log }) => {
      // Should now be on HomePage after onboarding complete
      log('HomePage — showing loaded pack and system status')
      await wait(2000)
    },
  },

  // SCENE 6: Online Phase — Mission Chat (0:40–0:55)
  {
    id: 'mission-chat',
    startSec: 40,
    endSec: 55,
    leftFrame: 'online-phase',
    rightAction: async ({ phone, log }) => {
      await phone.goto('http://localhost:5173/mission')
      await wait(1500)

      // Message 1: Describe the mission
      log('Typing mission description...')
      const missionTextarea = 'textarea[placeholder="Describe your mission..."]'
      await typeSlowly(
        phone,
        missionTextarea,
        "I'm deploying to the Casamance region of Senegal to help smallholder farmers with cassava disease and drought",
      )
      await wait(400)
      await phone.click('button[aria-label="Send message"]')
      log('Sent mission message 1, waiting for response...')
      await waitForMissionResponse(phone, 'Welcome')

      // Message 2: Specify crops → triggers mission_card
      log('Typing crops message...')
      await typeSlowly(
        phone,
        missionTextarea,
        'Working with cassava and rice farmers',
      )
      await wait(400)
      await phone.click('button[aria-label="Send message"]')
      log('Sent mission message 2, waiting for response + Dispatch button...')
      // Wait for the Dispatch Agents button to render (appears on the mission card)
      await phone.waitForSelector('button:has-text("Dispatch Agents")', { timeout: 20_000 })
      await wait(1000)
      log('Clicking Dispatch Agents...')
      await phone.locator('button:has-text("Dispatch Agents")').click()
      log('Dispatched — navigating to progress page')
    },
  },

  // SCENE 7: Agent Progress (0:55–1:15)
  {
    id: 'agent-progress',
    startSec: 55,
    endSec: 75,
    leftFrame: 'progress',
    rightAction: async ({ phone, log }) => {
      log('Waiting for pipeline completion...')
      try {
        await phone.waitForFunction(
          () => document.body.innerText.includes('Knowledge Pack Ready') ||
                document.body.innerText.includes('Build complete'),
          null,
          { timeout: 28_000 }
        )
        log('Pipeline complete!')
      } catch {
        log('Pipeline did not fully complete within scene window — continuing')
      }
    },
  },

  // SCENE 8: Transition — NO WIFI / NO DATA / NO CLOUD (1:15–1:25)
  {
    id: 'transition',
    startSec: 75,
    endSec: 85,
    leftFrame: 'transition',
    rightAction: async ({ phone }) => {
      await phone.goto('http://localhost:5173/')
      await wait(500)
    },
  },

  // SCENE 9: Field Session — first offline interaction (1:25–1:40)
  {
    id: 'field-session',
    startSec: 85,
    endSec: 100,
    leftFrame: 'field-session',
    rightAction: async ({ phone, log }) => {
      await phone.goto('http://localhost:5173/field')
      await phone.waitForSelector('textarea[placeholder="Ask about your crops..."]', { timeout: 10_000 })
      log('Field chat ready (pack auto-loaded)')
      await wait(1000)

      log('Typing planting question...')
      await typeSlowly(
        phone,
        'textarea[placeholder="Ask about your crops..."]',
        'When should I plant cassava in Casamance this season?',
      )
      await wait(300)
      await phone.click('button[aria-label="Send message"]')
      log('Sent planting question, waiting for response...')
      await waitForResponseDone(phone, 50_000)
      log('Planting response complete')
    },
  },

  // SCENE 10: Hero Shot — plant photo → diagnosis (1:40–2:05)
  // THE key moment.
  {
    id: 'hero-shot',
    startSec: 100,
    endSec: 125,
    leftFrame: 'pipeline',
    rightAction: async ({ phone, log }) => {
      // Type the question first, then attach photo
      log('Typing diagnosis question...')
      await typeSlowly(
        phone,
        'textarea[placeholder="Ask about your crops..."]',
        'Something is wrong with my cassava, what is this?',
      )
      await wait(500)

      // Inject the cassava disease photo via file input
      log('Uploading plant disease photo...')
      const fileInput = phone.locator('input[type="file"][accept="image/jpeg,image/png,image/webp"]')
      await fileInput.setInputFiles(PHOTO_PATH)
      await wait(1500)

      log('Sending photo for diagnosis...')
      await phone.click('button[aria-label="Send message"]')
      log('Photo sent, waiting for diagnosis to stream...')
      await waitForResponseDone(phone, 75_000)
      log('Diagnosis complete! Letting viewer read the answer...')

      // Dwell on the raw chat answer so viewers can read it before we navigate
      await wait(2500)

      // Click "View Full Diagnosis" to show the analysis page
      try {
        await phone.waitForSelector('button:has-text("View Full Diagnosis")', { timeout: 5_000 })
        await phone.locator('button:has-text("View Full Diagnosis")').click()
        log('Navigated to Diagnosis Card page')
        await wait(3000)
      } catch {
        log('View Full Diagnosis button not found — staying on chat')
        await wait(2000)
      }
    },
  },

  // SCENE 11: Grounded AI — follow-up question (2:05–2:20)
  {
    id: 'grounded',
    startSec: 125,
    endSec: 140,
    leftFrame: 'grounded',
    rightAction: async ({ phone, log }) => {
      // Navigate back to field chat from diagnosis page
      try {
        const backBtn = phone.locator('button:has-text("Back to Chat")')
        if (await backBtn.count() > 0) {
          await backBtn.click()
          log('Back to field chat from diagnosis page')
          await phone.waitForSelector('textarea[placeholder="Ask about your crops..."]', { timeout: 5_000 })
          await wait(500)
        }
      } catch {
        // Already on field chat
      }
      log('Typing neem spray follow-up...')
      await typeSlowly(
        phone,
        'textarea[placeholder="Ask about your crops..."]',
        'How do I prepare the neem oil spray?',
      )
      await wait(300)
      await phone.click('button[aria-label="Send message"]')
      log('Sent neem follow-up, waiting for response...')
      await waitForResponseDone(phone, 55_000)
      log('Neem response complete')
    },
  },

  // SCENE 12: Platform Vision — pack list (2:20–2:35)
  {
    id: 'platform',
    startSec: 140,
    endSec: 155,
    leftFrame: 'platform',
    rightAction: async ({ phone, log }) => {
      log('Navigating to pack list...')
      await phone.goto('http://localhost:5173/packs')
      await wait(1000)
    },
  },

  // SCENE 13: Closing (2:35–2:50)
  {
    id: 'closing',
    startSec: 155,
    endSec: 170,
    leftFrame: 'closing',
    rightAction: async () => {},
  },
]

// ─── Dry-run mode ────────────────────────────────────────────────────────────

function printTimeline() {
  console.log('\n  FieldPack AI — Demo Recording Timeline\n')
  console.log(`  ${'Scene'.padEnd(20)} ${'Time'.padEnd(12)} ${'Left Frame'.padEnd(17)} Duration`)
  console.log('  ' + '─'.repeat(70))
  for (const s of SCENES) {
    const start = `${Math.floor(s.startSec / 60)}:${String(s.startSec % 60).padStart(2, '0')}`
    const end = `${Math.floor(s.endSec / 60)}:${String(s.endSec % 60).padStart(2, '0')}`
    const dur = s.endSec - s.startSec
    const frame = s.leftFrame ?? '(full-screen)'
    console.log(`  ${s.id.padEnd(20)} ${(start + '–' + end).padEnd(12)} ${frame.padEnd(17)} ${dur}s`)
  }
  console.log('\n  Total: 2:50 (170 seconds)\n')
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  if (DRY_RUN) {
    printTimeline()
    return
  }

  // Verify photo exists
  if (!fs.existsSync(PHOTO_PATH)) {
    console.error(`ERROR: Plant photo not found at ${PHOTO_PATH}`)
    process.exit(1)
  }

  console.log('\n  FieldPack AI — Demo Recording (Single Window Mode)\n')
  console.log('  Launching browser...')

  // Single browser window at 1920x1080
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--disable-infobars',
      '--no-first-run',
      '--no-default-browser-check',
      '--window-position=0,0',
      `--window-size=${WIDTH},${HEIGHT}`,
      '--start-maximized',
    ],
  })

  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    colorScheme: 'dark',
  })
  const page = await context.newPage()

  // Navigate to the recording page
  await page.goto(RECORDING_URL)
  await wait(2000)

  // Get a handle to the phone iframe
  const phoneFrame = page.frame('phone-app')
  if (!phoneFrame) {
    console.error('ERROR: Could not find phone-app iframe. Is the frontend running on :5173?')
    await browser.close()
    process.exit(1)
  }

  // Pre-load the phone to the onboarding Welcome slide BEFORE recording starts
  // (avoids a visible blank flash when scene 3 tries to reload the same URL)
  await phoneFrame.evaluate(() => {
    localStorage.removeItem('fieldpack_onboarded')
    window.location.href = 'http://localhost:5173/'
  })
  await phoneFrame.waitForSelector('button:has-text("Get Started")', { timeout: 10_000 })
  console.log('  Phone ready on onboarding Welcome slide.')

  // Timestamp log file for narration alignment
  const timestamps: { scene: string; startedAt: string; elapsedMs: number }[] = []

  const log = (msg: string) => {
    const elapsed = Date.now() - recordingStart
    const mins = Math.floor(elapsed / 60_000)
    const secs = Math.floor((elapsed % 60_000) / 1000)
    const ms = elapsed % 1000
    const ts = `${mins}:${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
    console.log(`  [${ts}] ${msg}`)
  }

  let recordingStart = Date.now()

  // ── Ready signal ──
  console.log('\n  ============================================')
  console.log('  Single window ready. Start OBS capture now.')
  console.log('  In OBS: Window Capture → this Chromium window')
  console.log('  Press Enter to begin the 3-minute demo...')
  console.log('  ============================================\n')

  // Wait for Enter key to start
  await new Promise<void>(resolve => {
    if (process.stdin.isTTY) {
      process.stdin.setRawMode(true)
    }
    process.stdin.resume()
    process.stdin.once('data', () => {
      if (process.stdin.isTTY) {
        process.stdin.setRawMode(false)
      }
      process.stdin.pause()
      resolve()
    })
  })

  // 5-second countdown so OBS can start and first frame is clean
  console.log('\n  Starting in...')
  for (let i = 5; i >= 1; i--) {
    console.log(`  ${i}...`)
    await wait(1000)
  }
  console.log('  GO!\n')

  recordingStart = Date.now()
  log('Recording started!')

  // ── Execute timeline ──
  for (let i = 0; i < SCENES.length; i++) {
    const scene = SCENES[i]

    // Wait until scene start time
    const targetMs = scene.startSec * 1000
    const elapsed = Date.now() - recordingStart
    if (elapsed < targetMs) {
      await wait(targetMs - elapsed)
    }

    log(`▸ Scene: ${scene.id} [${fmtTime(scene.startSec)}–${fmtTime(scene.endSec)}]`)

    timestamps.push({
      scene: scene.id,
      startedAt: new Date().toISOString(),
      elapsedMs: Date.now() - recordingStart,
    })

    // Left panel: change frame via hash
    if (scene.leftFrame) {
      await page.evaluate((frame) => {
        window.location.hash = frame
      }, scene.leftFrame)
    }

    // Right panel: execute action on the phone iframe
    try {
      await scene.rightAction({ page, phone: phoneFrame, log })
    } catch (err) {
      log(`  ✗ Error in scene ${scene.id}: ${err instanceof Error ? err.message : err}`)
    }
  }

  // Wait until 2:50
  const totalElapsed = Date.now() - recordingStart
  if (totalElapsed < 170_000) {
    log(`Holding for ${Math.ceil((170_000 - totalElapsed) / 1000)}s until 2:50...`)
    await wait(170_000 - totalElapsed)
  }

  log('Recording complete! (2:50)')

  // Write timestamp log
  const logPath = path.resolve(__dirname, 'timestamps.json')
  fs.writeFileSync(logPath, JSON.stringify(timestamps, null, 2))
  log(`Timestamps written to ${logPath}`)

  // Validation: every scene in SCENES must be in timestamps.json
  const recordedIds = new Set(timestamps.map(t => t.scene))
  const missing = SCENES.map(s => s.id).filter(id => !recordedIds.has(id))
  if (missing.length > 0) {
    console.log(`\n  ⚠ WARNING: ${missing.length} scene(s) missing from timestamps.json:`)
    for (const id of missing) console.log(`    - ${id}`)
    console.log('  Audio build will skip narration clips tied to these scenes.\n')
  } else {
    console.log(`\n  ✓ All ${SCENES.length} scenes recorded to timestamps.json\n`)
  }

  console.log('\n  Stop OBS recording now. Window will close in 5 seconds...\n')
  await wait(5000)

  await context.close()
  await browser.close()
}

function fmtTime(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
