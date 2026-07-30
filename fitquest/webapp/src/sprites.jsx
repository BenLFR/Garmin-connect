// Pixel art sprites — 16×16 maps rendered as SVG rects (crisp at any scale).
// Legend chars map to palette colors; '.' is transparent.

const HERO_MAP = [
  '....HHHHHH......',
  '...HHHHHHHH.....',
  '..HHHHHHHHHH....',
  '..HHSSSSSSHH....',
  '..HSSESSESSH....',
  '...SSSSSSSS.....',
  '....SSSSSS......',
  '..CCCCCCCCCC....',
  '.CCCCCCCCCCCC...',
  '.CWWCCCCCCWWC...',
  '.CWWCCCCCCWWC...',
  '..CBBBBBBBBC....',
  '...LLL..LLL.....',
  '...LLL..LLL.....',
  '...OOO..OOO.....',
  '..OOOO..OOOO....',
]

const BOSS_MAP = [
  '................',
  '...GGGGGGGGGG...',
  '..GGGGGGGGGGGG..',
  '..GGRRGGGGRRGG..',
  '..GGGGGGGGGGGG..',
  '...GGGGGGGGGG...',
  '.GGGGGGGGGGGGGG.',
  'GGG.GGGGGGGG.GGG',
  'GG..GGGGGGGG..GG',
  'GG..GGGGGGGG..GG',
  '....GGGGGGGG....',
  '....GGG..GGG....',
  '...GGGG..GGGG...',
  '...GGG....GGG...',
  '..GGGG....GGGG..',
  '................',
]

// World boss — front-facing dragon with wings, fangs and glowing eyes
const WORLD_BOSS_MAP = [
  '.W..............W.',
  '.WW....DDDD....WW.',
  '.WWW..DDDDDD..WWW.',
  '.WWWDDDDDDDDDDWWW.',
  '..WWDDRDDDDRDDWW..',
  '..WDDDDDDDDDDDDW..',
  '...DDDDDDDDDDDD...',
  '...DDDFFFFFFDDD...',
  '....DDFFFFFFDD....',
  '.....DDDDDDDD.....',
  '....DD..DD..DD....',
  '...DDD..DD..DDD...',
]

const SKIN = { S: '#e8b88a', E: '#101528' }

// Gear overlays — same 16×16 grid as HERO_MAP, '.' transparent, rendered
// on top of the hero. Ids match server game/cosmetics.py ITEMS.
export const GEAR_MAPS = {
  g_bandeau: {
    palette: { R: '#ffb347' },
    map: [
      '................',
      '................',
      '................',
      '...RRRRRRRR.....',
      '................', '................', '................', '................',
      '................', '................', '................', '................',
      '................', '................', '................', '................',
    ],
  },
  g_epee: {
    palette: { W: '#cfd6ff', G: '#ffd166' },
    map: [
      '..............W.',
      '..............W.',
      '..............W.',
      '..............W.',
      '..............W.',
      '..............W.',
      '..............W.',
      '.............GGG',
      '..............G.',
      '..............G.',
      '................', '................', '................', '................',
      '................', '................',
    ],
  },
  g_bouclier: {
    palette: { B: '#8f7bff', D: '#372a73' },
    map: [
      '................', '................', '................', '................',
      '................', '................', '................',
      'DBB.............',
      'DBBB............',
      'DBBB............',
      'DBBB............',
      'DBB.............',
      '.DB.............',
      '................', '................', '................',
    ],
  },
  g_couronne: {
    palette: { G: '#ffd166', J: '#ff4d8f' },
    map: [
      '....G..J..G.....',
      '....GGGGGG......',
      '................', '................', '................', '................',
      '................', '................', '................', '................',
      '................', '................', '................', '................',
      '................', '................',
    ],
  },
  g_aile: {
    palette: { A: '#8f7bff', L: '#b3a6ff' },
    map: [
      '................', '................', '................', '................',
      '................', '................',
      'L..............L',
      'AL............LA',
      'AAL..........LAA',
      'AAL..........LAA',
      'AL............LA',
      'L..............L',
      '................', '................', '................', '................',
    ],
  },
}

export const PALETTES = {
  rodeur: { H: '#1f8f74', C: '#14513f', B: '#0d3328', L: '#1c2a24', O: '#3ee6c1', W: '#3ee6c1', ...SKIN },
  assassin: { H: '#2a2036', C: '#471c33', B: '#ff4d8f', L: '#241a2e', O: '#ff4d8f', W: '#ff4d8f', ...SKIN },
  guerrier: { H: '#8a5a22', C: '#6b4a1d', B: '#ffb347', L: '#3a2c14', O: '#ffb347', W: '#ffb347', ...SKIN },
  paladin: { H: '#4a3a94', C: '#372a73', B: '#ffd166', L: '#292052', O: '#8f7bff', W: '#ffd166', ...SKIN },
  voyageur: { H: '#8f6b1d', C: '#6e5216', B: '#ffd166', L: '#41320e', O: '#ffd166', W: '#3ee6c1', ...SKIN },
  boss: { G: '#7e3050', R: '#ff4d8f' },
  worldBoss: { D: '#6b2447', R: '#ff4d8f', F: '#c96a8e', W: '#4a3a94' },
}

function mapRects(map, palette, keyPrefix = '') {
  const rects = []
  map.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      const color = palette[row[x]]
      if (color) rects.push(<rect key={`${keyPrefix}${x}-${y}`} x={x} y={y} width="1.02" height="1.02" fill={color} />)
    }
  })
  return rects
}

export function PixelSprite({ map = HERO_MAP, palette, size = 96, idle = true, halo, layers = [] }) {
  const rows = map.length
  const cols = map[0].length
  const rects = mapRects(map, palette)
  layers.forEach((layer, i) => rects.push(...mapRects(layer.map, layer.palette, `l${i}-`)))
  return (
    <svg
      className={`sprite${idle ? ' idle' : ''}${halo ? ' sprite-halo' : ''}`}
      style={halo ? { '--halo': halo } : undefined}
      width={size}
      height={(size / cols) * rows}
      viewBox={`0 0 ${cols} ${rows}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      {rects}
    </svg>
  )
}

export function HeroSprite({ playerClass, size = 96, idle = true, halo, gear }) {
  const layers = gear && GEAR_MAPS[gear] ? [GEAR_MAPS[gear]] : []
  return (
    <PixelSprite
      map={HERO_MAP} palette={PALETTES[playerClass] || PALETTES.rodeur}
      size={size} idle={idle} halo={halo} layers={layers}
    />
  )
}

export function BossSprite({ size = 112, idle = true }) {
  return <PixelSprite map={BOSS_MAP} palette={PALETTES.boss} size={size} idle={idle} halo="rgba(255,77,143,0.4)" />
}

export function WorldBossSprite({ size = 160, idle = true }) {
  return <PixelSprite map={WORLD_BOSS_MAP} palette={PALETTES.worldBoss} size={size} idle={idle} halo="rgba(143,123,255,0.45)" />
}

export const ACTIVITY_ICONS = {
  running: '🏃', trail_running: '⛰️', track_running: '🏃', cycling: '🚴',
  gravel_cycling: '🚴', mountain_biking: '🚵', indoor_cycling: '🚴',
  lap_swimming: '🏊', open_water_swimming: '🏊', strength_training: '🏋️',
  hiit: '🔥', hiking: '🥾', walking: '🚶', stair_climbing: '🪜',
  mountaineering: '🏔️', other: '⚔️',
}
