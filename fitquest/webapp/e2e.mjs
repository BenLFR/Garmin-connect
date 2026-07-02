// E2E drive: full onboarding → tavern → sync ×N until level-up → all tabs.
// Screenshots to scratchpad.
import { chromium } from 'playwright'

const SHOTS = process.env.SHOTS_DIR
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })
const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
const shot = (name) => page.screenshot({ path: `${SHOTS}/${name}.png` })
const fail = async (msg) => { console.error('FAIL:', msg); await shot('failure'); process.exit(1) }

await page.goto('http://localhost:8000/')

// S1 welcome
await page.waitForSelector('text=FITQUEST', { timeout: 8000 }).catch(() => fail('welcome screen'))
await shot('01-onboarding-welcome')
await page.click('text=COMMENCER')

// S2 connect
await page.waitForSelector('text=MODE DÉMO')
await shot('02-onboarding-connect')
await page.click('text=MODE DÉMO')

// S3 scan (animated) — catch it mid-scan
await page.waitForSelector('text=Lecture des runes', { timeout: 4000 }).catch(() => {})
await shot('03-onboarding-scan')

// S4 reveal
await page.waitForSelector('.class-card', { timeout: 10000 }).catch(() => fail('reveal'))
await page.waitForTimeout(400)
await shot('04-onboarding-reveal')
const recoText = await page.textContent('h1.px')
console.log('reveal:', recoText.replace(/\s+/g, ' ').trim())
await page.click('.cta-zone button:not([disabled])')

// S5 confirm
await page.waitForSelector('input')
await page.fill('input', 'Ben')
await shot('05-onboarding-confirm')
await page.click("text=ENTRER DANS L'ARÈNE")

// Tavern
await page.waitForSelector('text=NIVEAU', { timeout: 10000 }).catch(() => fail('tavern'))
await page.waitForTimeout(900) // let XP bar tween
await shot('06-tavern')

// Sync until level up (max 8 tries)
let leveled = false
for (let i = 0; i < 8 && !leveled; i++) {
  await page.click('text=SIMULER UNE SÉANCE')
  await page.waitForTimeout(500)
  if (i === 0) await shot('07-sync-floating-xp')
  leveled = await page.locator('text=LEVEL UP!').isVisible().catch(() => false)
  if (!leveled) {
    await page.waitForTimeout(900)
    leveled = await page.locator('text=LEVEL UP!').isVisible().catch(() => false)
  }
}
if (leveled) {
  await page.waitForTimeout(400)
  await shot('08-levelup')
  await page.click('.overlay')
} else console.log('note: no level-up in 8 syncs (fine, random loads)')

// Hero tab
await page.click('.tab-bar button:nth-child(2)')
await page.waitForSelector('text=Attributs')
await page.waitForTimeout(800)
await shot('09-hero-sheet')

// Quests tab
await page.click('.tab-bar button:nth-child(3)')
await page.waitForSelector('text=RÉCOMPENSE')
await page.waitForTimeout(800)
await shot('10-quests-boss')

// Journal tab
await page.click('.tab-bar button:nth-child(4)')
await page.waitForSelector('.act-row', { timeout: 6000 }).catch(() => fail('journal'))
await shot('11-journal')

const xpRows = await page.locator('.axp').count()
console.log(`journal rows: ${xpRows}`)
console.log('E2E OK')
await browser.close()
