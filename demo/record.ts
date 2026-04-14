/**
 * FieldPack AI — Demo Video Recording Orchestration
 *
 * Drives TWO browser windows simultaneously for OBS screen capture:
 *   Left  (1152x1080): video-frames app at :5178 — hash-based frame changes
 *   Right (~430x932):  frontend phone app at :5173 — types, clicks, uploads
 *
 * Prerequisites:
 *   1. Backend running with DEMO_MODE=true on :8000
 *   2. Frontend dev server on :5173
 *   3. Video-frames dev server on :5178
 *   4. OBS capturing the positioned windows
 *
 * Run:  cd demo && npm run record
 * Dry:  cd demo && npm run record:dry   (prints timeline, no browser)
 */

import { chromium, type Page } from 'playwright'
import * as path from 'path'
import * as fs from 'fs'

// ─── Config ──────────────────────────────────────────────────────────────────

const LEFT_URL = 'http://localhost:5178'
const RIGHT_URL = 'http://localhost:5173'
const PHOTO_PATH = path.resolve(__dirname, 'assets/photos/disease_cmd_figure.jpg')

// Window geometry
const LEFT_WIDTH = 1152
const LEFT_HEIGHT = 1080
const RIGHT_WIDTH = 430
const RIGHT_HEIGHT = 932
// Position the right window next to the left, with some margin for the phone frame
const RIGHT_X = LEFT_WIDTH + 40
const RIGHT_Y = Math.floor((LEFT_HEIGHT - RIGHT_HEIGHT) / 2) // vertically center

// Typing speed: characters per keystroke delay (ms)
const TYPING_DELAY = 45

const DRY_RUN = process.argv.includes('--dry-run')

// ─── Timeline ────────────────────────────────────────────────────────────────

interface Scene {
  id: string
  startSec: number
  endSec: number
  leftFrame: string | null   // hash fragment, or null = no change / full-screen moment
  rightAction: (ctx: Context) => Promise<void>
}

interface Context {
  left: Page
  right: Page
  log: (msg: string) => void
}

// Helper: wait for a duration in milliseconds
const wait = (ms: number) => new Promise<void>(r => setTimeout(r, ms))

// Helper: type character by character (cinematic feel)
async function typeSlowly(page: Page, selector: string, text: string, delayMs = TYPING_DELAY) {
  await page.click(selector)
  await page.type(selector, text, { delay: delayMs })
}

// Helper: wait until streaming response finishes (stop button disappears)
async function waitForResponseDone(page: Page, timeoutMs = 30_000) {
  // Wait for the stop button to appear first (streaming started)
  await page.waitForSelector('[aria-label="Stop generating"]', { timeout: 10_000 }).catch(() => {})
  // Then wait for it to disappear (streaming finished)
  await page.waitForFunction(
    () => !document.querySelector('[aria-label="Stop generating"]'),
    { timeout: timeoutMs }
  )
  // Small settle time for final rendering
  await wait(500)
}

// Helper: wait for mission chat response (typing indicator disappears)
async function waitForMissionResponse(page: Page, timeoutMs = 15_000) {
  // Wait for the assistant message to appear
  await wait(1000)
  // Wait for isTyping to become false — the send button re-enables
  await page.waitForSelector('button[aria-label="Send message"]:not([disabled])', { timeout: timeoutMs })
  await wait(500)
}

const SCENES: Scene[] = [
  // ────────────────────────────────────────────────────────────────────────
  // SCENE 1: Cold Open — diseased leaf (0:00–0:05)
  // Full-screen story moment — no app shown. Left panel blank, right panel blank.
  // This scene is composited in Resolve with the stock cassava leaf photo.
  {
    id: 'cold-open',
    startSec: 0,
    endSec: 5,
    leftFrame: null,
    rightAction: async () => {},  // nothing — OBS captures static setup
  },

  // SCENE 2: The Answer — phone centered with diagnosis streaming (0:05–0:12)
  // Full-screen app moment. In the video this is a composed shot.
  // Right panel shows field chat with a pre-loaded diagnosis — we skip this
  // in the Playwright flow because it's composited from the hero shot footage.
  {
    id: 'the-answer',
    startSec: 5,
    endSec: 12,
    leftFrame: null,
    rightAction: async () => {},  // composited in Resolve from hero shot footage
  },

  // SCENE 3: Title Card (0:12–0:18)
  // Full-screen story moment.
  {
    id: 'title-card',
    startSec: 12,
    endSec: 18,
    leftFrame: 'title',
    rightAction: async () => {},
  },

  // SCENE 4: Amina's Profile (0:18–0:28)
  // Split screen begins. Right panel: home screen with pack loaded.
  {
    id: 'persona',
    startSec: 18,
    endSec: 28,
    leftFrame: 'persona',
    rightAction: async ({ right }) => {
      await right.goto(`${RIGHT_URL}/`)
      await wait(1000)
    },
  },

  // SCENE 5: The Map (0:28–0:35)
  {
    id: 'map',
    startSec: 28,
    endSec: 35,
    leftFrame: 'map',
    rightAction: async () => {},  // right stays on home
  },

  // SCENE 6: Impact Stats (0:35–0:45)
  {
    id: 'stats',
    startSec: 35,
    endSec: 45,
    leftFrame: 'stats',
    rightAction: async () => {},  // right stays on home
  },

  // SCENE 7: Architecture (0:45–0:55)
  {
    id: 'architecture',
    startSec: 45,
    endSec: 55,
    leftFrame: 'architecture',
    rightAction: async () => {},  // right stays on home
  },

  // SCENE 8: Online Phase — Mission Chat (0:55–1:10)
  // Right panel: mission chat — two messages + dispatch button
  {
    id: 'mission-chat',
    startSec: 55,
    endSec: 70,
    leftFrame: 'online-phase',
    rightAction: async ({ right, log }) => {
      await right.goto(`${RIGHT_URL}/mission`)
      await wait(1500)  // let initial welcome message render

      // Message 1: Describe the mission
      log('Typing mission description...')
      const missionTextarea = 'textarea[placeholder="Describe your mission..."]'
      await typeSlowly(
        right,
        missionTextarea,
        "I'm deploying to the Casamance region of Senegal to help smallholder farmers with cassava disease and drought",
      )
      await wait(400)
      await right.click('button[aria-label="Send message"]')
      log('Sent mission message 1, waiting for response...')
      await waitForMissionResponse(right)

      // Message 2: Specify crops → triggers mission_card
      log('Typing crops message...')
      await typeSlowly(
        right,
        missionTextarea,
        'Working with cassava and rice farmers',
      )
      await wait(400)
      await right.click('button[aria-label="Send message"]')
      log('Sent mission message 2, waiting for response + mission card...')
      await waitForMissionResponse(right, 20_000)

      // Wait for the Dispatch button to render
      await wait(1000)
      log('Clicking Dispatch Agents...')
      const dispatchBtn = right.getByRole('button', { name: /Dispatch Agents/i })
      await dispatchBtn.click()
      log('Dispatched — navigating to progress page')
    },
  },

  // SCENE 9: Agent Progress (1:10–1:30)
  // Auto-plays pipeline. 25.5s demo time but scene is 20s.
  // Let it run — the overflow into transition scene looks good on video.
  {
    id: 'agent-progress',
    startSec: 70,
    endSec: 90,
    leftFrame: 'progress',
    rightAction: async ({ right, log }) => {
      // AgentProgressPage auto-starts on mount via location.state.missionCard
      // Wait for "Pack Ready" or completion indicator
      log('Waiting for pipeline completion...')
      try {
        await right.waitForFunction(
          () => document.body.innerText.includes('Pack Ready') ||
                document.body.innerText.includes('Complete') ||
                document.body.innerText.includes('ready'),
          { timeout: 28_000 }
        )
        log('Pipeline complete!')
      } catch {
        log('Pipeline did not fully complete within scene window — continuing')
      }
    },
  },

  // SCENE 10: Transition — NO WIFI / NO DATA / NO CLOUD (1:30–1:40)
  {
    id: 'transition',
    startSec: 90,
    endSec: 100,
    leftFrame: 'transition',
    rightAction: async ({ right }) => {
      // Navigate to home or settings to show "offline" state
      await right.goto(`${RIGHT_URL}/`)
      await wait(500)
    },
  },

  // SCENE 11: Field Session — first offline interaction (1:40–1:55)
  // Right panel: navigate to field chat, load pack, type planting question
  {
    id: 'field-session',
    startSec: 100,
    endSec: 115,
    leftFrame: 'field-session',
    rightAction: async ({ right, log }) => {
      // Navigate to field chat — in DEMO_MODE the pack is already "loaded",
      // so packInfo is set automatically from the API and chat is ready
      await right.goto(`${RIGHT_URL}/field`)
      await right.waitForSelector('textarea[placeholder="Ask about your crops..."]', { timeout: 10_000 })
      log('Field chat ready (pack auto-loaded)')
      await wait(1000)

      // Type the planting question
      log('Typing planting question...')
      await typeSlowly(
        right,
        'textarea[placeholder="Ask about your crops..."]',
        'When should I plant cassava in Casamance this season?',
      )
      await wait(300)
      await right.click('button[aria-label="Send message"]')
      log('Sent planting question, waiting for response...')
      await waitForResponseDone(right, 20_000)
      log('Planting response complete')
    },
  },

  // SCENE 12: Hero Shot — plant photo → diagnosis (1:55–2:20)
  // THE key moment. Upload photo, wait for full diagnosis to stream.
  {
    id: 'hero-shot',
    startSec: 115,
    endSec: 140,
    leftFrame: 'pipeline',
    rightAction: async ({ right, log }) => {
      // Inject the cassava disease photo via file input
      log('Uploading plant disease photo...')
      const fileInput = right.locator('input[type="file"][accept="image/jpeg,image/png,image/webp"]')
      await fileInput.setInputFiles(PHOTO_PATH)
      // Wait for preview to appear
      await wait(1500)

      // Send with the default text "What disease does this plant have?"
      // The textarea placeholder changes to "Describe the issue (optional)..." when image attached
      // handleSend will use the default text if input is empty and pendingImage is set
      log('Sending photo for diagnosis...')
      await right.click('button[aria-label="Send message"]')
      log('Photo sent, waiting for diagnosis to stream...')
      await waitForResponseDone(right, 35_000)
      log('Diagnosis complete — hero shot done!')
      await wait(2000)  // hold on the complete diagnosis
    },
  },

  // SCENE 13: Grounded AI — follow-up question (2:20–2:35)
  {
    id: 'grounded',
    startSec: 140,
    endSec: 155,
    leftFrame: 'grounded',
    rightAction: async ({ right, log }) => {
      // Type a follow-up about neem spray
      log('Typing neem spray follow-up...')
      await typeSlowly(
        right,
        'textarea[placeholder="Ask about your crops..."]',
        'How do I prepare the neem oil spray?',
      )
      await wait(300)
      await right.click('button[aria-label="Send message"]')
      log('Sent neem follow-up, waiting for response...')
      await waitForResponseDone(right, 20_000)
      log('Neem response complete')
    },
  },

  // SCENE 14: Platform Vision — pack list (2:35–2:50)
  {
    id: 'platform',
    startSec: 155,
    endSec: 170,
    leftFrame: 'platform',
    rightAction: async ({ right, log }) => {
      log('Navigating to pack list...')
      await right.goto(`${RIGHT_URL}/packs`)
      await wait(1000)
    },
  },

  // SCENE 15: Closing (2:50–3:00)
  {
    id: 'closing',
    startSec: 170,
    endSec: 180,
    leftFrame: 'closing',
    rightAction: async () => {},  // static — hold on pack list or home
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
  console.log('\n  Total: 3:00 (180 seconds)\n')
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

  console.log('\n  FieldPack AI — Demo Recording\n')
  console.log('  Launching browsers...')

  // Two separate browser instances = two separate OS windows
  const leftBrowser = await chromium.launch({
    headless: false,
    args: [
      '--disable-infobars',
      '--no-first-run',
      '--no-default-browser-check',
      `--window-position=0,0`,
      `--window-size=${LEFT_WIDTH},${LEFT_HEIGHT}`,
    ],
  })

  const rightBrowser = await chromium.launch({
    headless: false,
    args: [
      '--disable-infobars',
      '--no-first-run',
      '--no-default-browser-check',
      `--window-position=${RIGHT_X},${RIGHT_Y}`,
      `--window-size=${RIGHT_WIDTH},${RIGHT_HEIGHT}`,
    ],
  })

  // ── Left window: video-frames app ──
  const leftContext = await leftBrowser.newContext({
    viewport: { width: LEFT_WIDTH, height: LEFT_HEIGHT },
    colorScheme: 'dark',
  })
  const left = await leftContext.newPage()

  // ── Right window: frontend phone app ──
  const rightContext = await rightBrowser.newContext({
    viewport: { width: RIGHT_WIDTH, height: RIGHT_HEIGHT },
    colorScheme: 'dark',
  })
  const right = await rightContext.newPage()

  // Fine-tune window positions via CDP (the launch args set initial position,
  // but CDP gives pixel-perfect control after the window is created)
  try {
    const leftCdp = await leftContext.newCDPSession(left)
    const leftWindowId = (await leftCdp.send('Browser.getWindowForTarget')).windowId
    await leftCdp.send('Browser.setWindowBounds', {
      windowId: leftWindowId,
      bounds: { left: 0, top: 0, width: LEFT_WIDTH, height: LEFT_HEIGHT, windowState: 'normal' },
    })

    const rightCdp = await rightContext.newCDPSession(right)
    const rightWindowId = (await rightCdp.send('Browser.getWindowForTarget')).windowId
    await rightCdp.send('Browser.setWindowBounds', {
      windowId: rightWindowId,
      bounds: { left: RIGHT_X, top: RIGHT_Y, width: RIGHT_WIDTH, height: RIGHT_HEIGHT, windowState: 'normal' },
    })
  } catch {
    console.warn('  Warning: Could not fine-tune window positions via CDP — adjust manually')
  }

  // Navigate to starting URLs
  await left.goto(`${LEFT_URL}/`)
  await right.goto(`${RIGHT_URL}/`)
  await wait(2000)

  // Timestamp log file for narration alignment
  const timestamps: { scene: string; startedAt: string; elapsedMs: number }[] = []
  const recordingStart = Date.now()

  const log = (msg: string) => {
    const elapsed = Date.now() - recordingStart
    const mins = Math.floor(elapsed / 60_000)
    const secs = Math.floor((elapsed % 60_000) / 1000)
    const ms = elapsed % 1000
    const ts = `${mins}:${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
    console.log(`  [${ts}] ${msg}`)
  }

  // ── Ready signal ──
  console.log('\n  ============================================')
  console.log('  Windows positioned. Start OBS recording now.')
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

  const t0 = Date.now()
  log('Recording started!')

  // ── Execute timeline ──
  for (let i = 0; i < SCENES.length; i++) {
    const scene = SCENES[i]
    const sceneStart = Date.now()

    // Wait until scene start time
    const targetMs = scene.startSec * 1000
    const elapsed = Date.now() - t0
    if (elapsed < targetMs) {
      await wait(targetMs - elapsed)
    }

    log(`▸ Scene: ${scene.id} [${fmtTime(scene.startSec)}–${fmtTime(scene.endSec)}]`)

    timestamps.push({
      scene: scene.id,
      startedAt: new Date().toISOString(),
      elapsedMs: Date.now() - t0,
    })

    // Left panel: change frame
    if (scene.leftFrame) {
      await left.goto(`${LEFT_URL}/#${scene.leftFrame}`)
    }

    // Right panel: execute action
    try {
      await scene.rightAction({ left, right, log })
    } catch (err) {
      log(`  ✗ Error in scene ${scene.id}: ${err instanceof Error ? err.message : err}`)
    }

    // If the right action finished early, hold until scene end
    const sceneElapsed = Date.now() - sceneStart
    const sceneDuration = (scene.endSec - scene.startSec) * 1000
    if (sceneElapsed < sceneDuration) {
      // Don't hard-wait the full remainder — the next scene's targetMs handles sync
    }
  }

  // Wait until 3:00
  const totalElapsed = Date.now() - t0
  if (totalElapsed < 180_000) {
    log(`Holding for ${Math.ceil((180_000 - totalElapsed) / 1000)}s until 3:00...`)
    await wait(180_000 - totalElapsed)
  }

  log('Recording complete! (3:00)')

  // Write timestamp log
  const logPath = path.resolve(__dirname, 'timestamps.json')
  fs.writeFileSync(logPath, JSON.stringify(timestamps, null, 2))
  log(`Timestamps written to ${logPath}`)

  console.log('\n  Stop OBS recording now. Windows will close in 5 seconds...\n')
  await wait(5000)

  await leftContext.close()
  await rightContext.close()
  await leftBrowser.close()
  await rightBrowser.close()
}

function fmtTime(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
