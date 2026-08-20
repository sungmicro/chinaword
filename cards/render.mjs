#!/usr/bin/env node
// 7.5cm x 10cm 다이어리 속지 카드 PNG 생성기 (300dpi)
//
//   node cards/render.mjs              # 카드 PNG + A4 인쇄 시트 생성
//   node cards/render.mjs --no-sheet   # 카드 PNG만
//   node cards/render.mjs --no-trim    # 재단선 없이
//
// 1mm = 10 CSS px 로 그린 뒤 deviceScaleFactor 로 300dpi 픽셀에 맞춘다.

import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'
import { chromium } from 'playwright-core'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = join(HERE, 'out')

const PX_PER_MM = 10 // CSS px
const DPI = 300
const SCALE = DPI / 25.4 / PX_PER_MM // 1.181333…
const CARD_W = 75 // mm
const CARD_H = 100 // mm

const argv = process.argv.slice(2)
const flag = (name, dflt = true) => (argv.includes(`--no-${name}`) ? false : argv.includes(`--${name}`) ? true : dflt)
const WITH_SHEET = flag('sheet')
const WITH_TRIM = flag('trim')

const esc = (s) =>
  String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])

/* ---------------------------------------------------------------- 폰트 */

const FONT_DIR = join(homedir(), '.local/share/fonts')
const WEIGHTS = [400, 500, 700]

async function ensureFonts() {
  let installed = ''
  try {
    installed = execFileSync('fc-list', [':lang=ko', 'family'], { encoding: 'utf8' })
  } catch {
    /* fontconfig 없음 — 그냥 진행 */
  }
  if (installed.includes('Noto Sans KR')) return true

  console.log('· Noto Sans KR 이 없어 내려받습니다…')
  try {
    await mkdir(FONT_DIR, { recursive: true })
    for (const w of WEIGHTS) {
      const dest = join(FONT_DIR, `NotoSansKR-${w}.ttf`)
      if (existsSync(dest)) continue
      const css = await (await fetch(`https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@${w}`)).text()
      const url = css.match(/https:\/\/[^)]*\.ttf/)?.[0]
      if (!url) throw new Error('폰트 주소를 찾지 못했습니다')
      const buf = Buffer.from(await (await fetch(url)).arrayBuffer())
      await writeFile(dest, buf)
    }
    execFileSync('fc-cache', ['-f'])
    return true
  } catch (err) {
    console.warn(`! 한글 폰트 설치 실패 (${err.message}). 시스템 기본 폰트로 렌더링합니다.`)
    return false
  }
}

/* ---------------------------------------------------------------- 스타일 */

const CSS = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { font-size: ${PX_PER_MM}px; }            /* 1rem = 1mm */
  body {
    font-family: 'Noto Sans KR', 'WenQuanYi Zen Hei', sans-serif;
    -webkit-font-smoothing: antialiased;
    background: #fff;
    color: var(--fg);
  }
  .card {
    --fg: #16181c;
    --muted: #79818c;
    --rule: #d9dde3;
    --accent: #1b3a5c;
    --tint: #eef2f7;
    position: relative;
    width: ${CARD_W}rem; height: ${CARD_H}rem;
    background: #fff;
    padding: 5.5rem 4.5rem 4.5rem 9.5rem;        /* 왼쪽은 바인더 펀치 여유 */
    display: flex; flex-direction: column;
    overflow: hidden;
  }
  .card[data-accent="red"] { --accent: #9c2a24; --tint: #f7eeed; }
  .card[data-trim="on"]::after {
    content: ''; position: absolute; inset: 0;
    border: 1px solid #e6e6e6; pointer-events: none;
  }

  .eyebrow {
    flex: none;
    font-size: 1.9rem; font-weight: 700; letter-spacing: .26rem;
    color: var(--accent); text-transform: uppercase;
  }
  .title { flex: none; font-size: 5rem; font-weight: 700; letter-spacing: -.05rem; margin-top: .6rem; }
  .rule { flex: none; height: .55rem; background: var(--accent); width: 8rem; margin: 1.8rem 0 2.8rem; }

  .body { flex: 1 1 auto; min-height: 0; padding-bottom: 1.4rem; display: flex; flex-direction: column; justify-content: space-between; }

  /* --- 라벨 + 기입선 --- */
  .row {
    display: grid; grid-template-columns: 18rem 1fr;
    align-items: end; column-gap: 1.5rem; row-gap: 1.9rem;
    margin-bottom: 1.9rem;
  }
  .row:last-child { margin-bottom: 0; }
  .row .label {
    grid-column: 1; grid-row: 1;
    font-size: 2.3rem; font-weight: 500; color: var(--muted); padding-bottom: .8rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .row .value {
    grid-column: 2;
    font-size: 3rem; font-weight: 500; line-height: 1.15;
    min-height: 4.1rem; padding-bottom: .7rem;
    border-bottom: .2rem dotted #c3c9d1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  /* --- 체크리스트 --- */
  .check { display: flex; align-items: flex-end; gap: 1.8rem; margin-bottom: 2.6rem; }
  .check:last-child { margin-bottom: 0; }
  .check .box {
    flex: none; width: 3.4rem; height: 3.4rem; margin-bottom: .8rem;
    border: .3rem solid var(--accent); border-radius: .5rem;
  }
  .check .text {
    flex: 1; font-size: 3.1rem; font-weight: 500; line-height: 1.2;
    min-height: 4.1rem; padding-bottom: .7rem;
    border-bottom: .2rem dotted #c3c9d1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  /* --- 분기 4분면 --- */
  .q .qline:last-child { margin-bottom: 0; }
  .quarters { flex: 1; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 2.5rem; }
  .q { display: flex; flex-direction: column; }
  .q .qhead { display: flex; align-items: baseline; gap: 1.2rem; margin-bottom: 1.8rem; }
  .q .qlabel {
    font-size: 2.6rem; font-weight: 700; color: #fff; background: var(--accent);
    padding: .5rem 1.2rem; border-radius: .6rem; letter-spacing: .06rem;
  }
  .q .qmonths { font-size: 2.2rem; color: var(--muted); font-weight: 500; }
  .q .qline {
    flex: 1; display: flex; align-items: flex-end;
    font-size: 2.6rem; font-weight: 500; line-height: 1.15;
    min-height: 3.8rem; padding-bottom: .6rem;
    border-bottom: .2rem dotted #c3c9d1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  /* --- 바닥 --- */
  .foot { flex: none; margin-top: auto; padding-top: 2.2rem; border-top: .2rem solid var(--rule); display: flex; gap: 1.5rem; align-items: baseline; }
  .foot .note { flex: 1; font-size: 1.9rem; line-height: 1.35; color: var(--muted); word-break: keep-all; }
  .foot .who { font-size: 1.9rem; color: var(--muted); font-weight: 500; white-space: nowrap; }
`

/* ---------------------------------------------------------------- 카드 */

const line = (v, cls = 'value') => `<div class="${cls}">${esc(v) || '&nbsp;'}</div>`

function fieldsBody(card) {
  return card.rows
    .map((r) => {
      const lines = Array.from({ length: r.span || 1 }, (_, i) => line(i === 0 ? r.value : ''))
      return `<div class="row">
        <div class="label">${esc(r.label)}</div>
        ${lines.join('')}
      </div>`
    })
    .join('')
}

function checklistBody(card) {
  return card.items
    .map((it) => `<div class="check"><div class="box"></div>${line(it.text, 'text')}</div>`)
    .join('')
}

function quartersBody(card) {
  return `<div class="quarters">${card.quarters
    .map(
      (q) => `<div class="q">
        <div class="qhead"><span class="qlabel">${esc(q.label)}</span><span class="qmonths">${esc(q.months)}</span></div>
        ${(q.lines || []).map((l) => line(l, 'qline')).join('')}
      </div>`
    )
    .join('')}</div>`
}

const BODIES = { fields: fieldsBody, checklist: checklistBody, quarters: quartersBody }

function cardHtml(card, meta) {
  const build = BODIES[card.type]
  if (!build) throw new Error(`알 수 없는 카드 형식: ${card.type}`)
  const who = [meta.owner, meta.updated].filter(Boolean).join(' · ')
  return `<div class="card" data-accent="${esc(card.accent || 'ink')}" data-trim="${WITH_TRIM ? 'on' : 'off'}">
    <div class="eyebrow">${esc(card.eyebrow)}</div>
    <div class="title">${esc(card.title)}</div>
    <div class="rule"></div>
    <div class="body">${build(card)}</div>
    <div class="foot">
      <div class="note">${esc(card.footnote || '')}</div>
      ${who ? `<div class="who">${esc(who)}</div>` : ''}
    </div>
  </div>`
}

const pageHtml = (inner, extraCss = '') =>
  `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${CSS}${extraCss}</style></head><body>${inner}</body></html>`

/* ---------------------------------------------------------------- A4 시트 */

const SHEET_CSS = `
  body { background: #fff; }
  .sheet {
    position: relative; width: 210rem; height: 297rem; padding: 23.5rem 27.5rem;
    display: grid; grid-template-columns: repeat(2, ${CARD_W}rem); grid-template-rows: repeat(2, ${CARD_H}rem);
    gap: 5rem; justify-content: center; align-content: center;
  }
  .slot { position: relative; }
  .slot .mark { position: absolute; background: #b9bec6; }
  .slot .mark.v { width: 1px; height: 4rem; }
  .slot .mark.h { height: 1px; width: 4rem; }
  .sheet-caption {
    position: absolute; left: 27.5rem; bottom: 12rem;
    font-size: 2.4rem; color: #8a919b;
  }
`

const marks = () => {
  const m = []
  for (const [x, y] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
    const hx = x ? 'right: 0;' : 'left: 0;'
    const vy = y ? 'bottom: 0;' : 'top: 0;'
    m.push(`<span class="mark v" style="${hx}${y ? 'bottom: -4.8rem;' : 'top: -4.8rem;'}"></span>`)
    m.push(`<span class="mark h" style="${vy}${x ? 'right: -4.8rem;' : 'left: -4.8rem;'}"></span>`)
  }
  return m.join('')
}

const sheetHtml = (cards, meta) =>
  pageHtml(
    `<div class="sheet">${cards
      .map((c) => `<div class="slot">${marks()}${cardHtml(c, meta)}</div>`)
      .join('')}<div class="sheet-caption">A4 100% 크기로 인쇄 → 재단선 따라 자르기 → 7.5 × 10 cm</div></div>`,
    SHEET_CSS
  )

/* ---------------------------------------------------------------- main */

async function shoot(browser, html, selector, wMm, hMm, dest) {
  const page = await browser.newPage({
    viewport: { width: Math.round(wMm * PX_PER_MM), height: Math.round(hMm * PX_PER_MM) },
    deviceScaleFactor: SCALE,
  })
  await page.setContent(html, { waitUntil: 'load' })
  await page.evaluate(() => document.fonts.ready)
  await page.locator(selector).screenshot({ path: dest, scale: 'device' })
  await page.close()
}

// 실제 개인정보는 data.local.json 에 적으면 저장소에 올라가지 않는다.
const dataPath = existsSync(join(HERE, 'data.local.json')) ? join(HERE, 'data.local.json') : join(HERE, 'data.json')
console.log(`· 데이터: ${dataPath.replace(HERE + '/', 'cards/')}`)
const data = JSON.parse(await readFile(dataPath, 'utf8'))
const meta = data.meta || {}

await ensureFonts()
await mkdir(OUT, { recursive: true })

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium',
})

for (const card of data.cards) {
  const dest = join(OUT, `${card.id}.png`)
  await shoot(browser, pageHtml(cardHtml(card, meta)), '.card', CARD_W, CARD_H, dest)
  console.log(`✓ ${dest}`)
}

if (WITH_SHEET) {
  const dest = join(OUT, 'print-a4.png')
  await shoot(browser, sheetHtml(data.cards.slice(0, 4), meta), '.sheet', 210, 297, dest)
  console.log(`✓ ${dest}`)
}

await browser.close()
console.log(`\n${CARD_W} × ${CARD_H} mm @ ${DPI}dpi = ${Math.round((CARD_W / 25.4) * DPI)} × ${Math.round((CARD_H / 25.4) * DPI)} px`)
