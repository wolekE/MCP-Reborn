import { expect, test, type Page } from '@playwright/test'
import { LETTERS, type Letter } from '../../src/data/letters'
import { soundClips } from '../../src/session/items'

const STORAGE_KEY = 'cyrillic-trainer'

/** Records every media play() call so tests can assert what was heard. */
async function spyOnAudio(page: Page) {
  await page.addInitScript(() => {
    const w = window as unknown as { __played: string[] }
    w.__played = []
    const original = HTMLMediaElement.prototype.play
    HTMLMediaElement.prototype.play = function (this: HTMLMediaElement) {
      w.__played.push(decodeURIComponent(this.src || this.currentSrc))
      return original.call(this)
    }
  })
}
const played = (page: Page) => page.evaluate(() => (window as unknown as { __played: string[] }).__played)

/** A save where group 1 (А К М О Т) has been learned. */
async function seedGroupOne(page: Page) {
  await page.addInitScript((key) => {
    if (localStorage.getItem(key)) return
    const now = Date.now()
    const letter = () => ({ ease: 2.5, intervalMin: 0, reps: 0, lapses: 0, due: now, introducedAt: now, attempts: 0, correct: 0, recent: [], lastSeen: null })
    localStorage.setItem(
      key,
      JSON.stringify({
        version: 1,
        settings: { voice: 'svetlana', rate: 1, sfxMuted: true, theme: 'system' },
        letters: Object.fromEntries(['a', 'k', 'm', 'o', 't'].map((id) => [id, letter()])),
        unlockedBatches: 1,
        confusions: {},
        streak: { current: 0, best: 0, lastDay: null },
        sessionsCompleted: 0,
        createdAt: now,
      }),
    )
  }, STORAGE_KEY)
}

test('completes a Learn session from the home screen', async ({ page }) => {
  await spyOnAudio(page)
  await page.goto('/')
  await page.getByRole('link', { name: /start session/i }).first().click()

  const group1 = ['А', 'К', 'М', 'О', 'Т']
  for (let i = 0; i < group1.length; i++) {
    await expect(page.getByText(`${i + 1} / 5`)).toBeVisible()
    await expect(page.locator('.learn-print')).toContainText(group1[i])
    if (i === 0) {
      // The card says the letter's name; Space plays it again.
      await expect.poll(async () => (await played(page)).filter((s) => s.endsWith('/name-a.mp3')).length).toBe(1)
      await page.keyboard.press('Space')
      await expect.poll(async () => (await played(page)).filter((s) => s.endsWith('/name-a.mp3')).length).toBe(2)
      // The syllable button plays the syllable clip.
      await page.getByRole('button', { name: /ма/ }).click()
      await expect.poll(async () => (await played(page)).some((s) => s.endsWith('/syl-ma.mp3'))).toBe(true)
    }
    await page.getByRole('button', { name: i < 4 ? /got it/i : /finish/i }).click()
  }

  await expect(page.getByTestId('learn-done')).toBeVisible()
  const save = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), STORAGE_KEY)
  const introduced = Object.entries(save.letters)
    .filter(([, p]) => (p as { introducedAt: number | null }).introducedAt !== null)
    .map(([id]) => id)
  expect(introduced.sort()).toEqual(['a', 'k', 'm', 'o', 't'])
  expect(save.sessionsCompleted).toBe(1)
})

test('plays a full Listen & Pick round', async ({ page }) => {
  await seedGroupOne(page)
  await spyOnAudio(page)
  await page.goto('/#/play/listen')
  await expect(page.getByTestId('drill')).toBeVisible()

  const sameClips = (l: Letter, clips: string[]) => soundClips(l).join(' ') === clips.join(' ')
  let answered = 0
  while (!(await page.getByTestId('summary').isVisible())) {
    const clips = (await page.getByTestId('prompt-card').getAttribute('data-clips'))!.split(' ')
    // The prompt auto-plays.
    await expect.poll(async () => (await played(page)).some((s) => s.endsWith(`/${clips[0]}.mp3`))).toBe(true)
    // А and М share the syllable "ма"; only one of them is ever offered.
    let clicked = false
    for (const l of LETTERS.filter((x) => sameClips(x, clips))) {
      const option = page.locator('.option', { hasText: `${l.upper} ${l.lower}` })
      if (await option.count()) {
        await option.click()
        clicked = true
        break
      }
    }
    expect(clicked, `no option matches ${clips}`).toBe(true)
    answered++
    await expect(page.getByTestId('score')).toHaveText(`${answered}/${answered}`)
    await expect(page.locator('.option.correct')).toBeVisible()
    await expect(page.locator('.option:not([disabled])').first().or(page.getByTestId('summary'))).toBeVisible()
  }

  expect(answered).toBe(10)
  await expect(page.getByTestId('summary')).toContainText('10 / 10 correct')
  const save = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), STORAGE_KEY)
  const attempts = Object.values(save.letters).reduce((n: number, p) => n + (p as { attempts: number }).attempts, 0)
  expect(attempts).toBe(10)
})

test('falls back to speech, and explains how to get a Russian voice when there is none', async ({ page }) => {
  await page.route('**/audio/**/*.mp3', (route) => route.abort())
  await page.addInitScript(() => {
    speechSynthesis.getVoices = () => []
  })
  await page.goto('/#/learn')
  await expect(page.getByRole('alertdialog', { name: /no russian voice/i })).toBeVisible()
  await expect(page.getByText(/macOS/)).toBeVisible()
  await expect(page.getByText(/Windows/)).toBeVisible()
})
