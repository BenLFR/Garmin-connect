// Onboarding S0→S5 (UX_FLOWS.md §1) — Duolingo pattern: the "aha moment"
// (personalized class reveal) happens BEFORE any commitment.
import { useEffect, useState } from 'react'
import { api } from '../api'
import { HeroSprite } from '../sprites.jsx'

const STEPS = ['welcome', 'connect', 'garmin-login', 'scan', 'reveal', 'confirm']

const AUTH_ERRORS = {
  bad_credentials: 'Email ou mot de passe refusé par Garmin.',
  bad_mfa_code: 'Code refusé — vérifie et réessaie.',
  rate_limited: 'Garmin limite les tentatives : réessaie dans 20-30 minutes.',
  no_pending_login: 'Session expirée — repars des identifiants.',
  garmin_error: 'Garmin est injoignable pour le moment.',
}

export default function Onboarding({ onDone }) {
  const [step, setStep] = useState('welcome')
  const [mode, setMode] = useState('demo')
  const [analysis, setAnalysis] = useState(null)
  const [selected, setSelected] = useState(null)
  const [name, setName] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [mfaNeeded, setMfaNeeded] = useState(false)
  const [authError, setAuthError] = useState(null)

  const stepIndex = STEPS.indexOf(step)

  // Returning from the Strava OAuth redirect: resume the flow seamlessly
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const strava = params.get('strava')
    if (!strava) return
    window.history.replaceState({}, '', '/')
    if (strava === 'connected') startScan('strava')
    else {
      setError(strava === 'denied'
        ? 'Autorisation Strava refusée — réessaie ou choisis une autre porte.'
        : 'Échange de jetons Strava impossible — réessaie.')
      setStep('connect')
    }
  }, [])

  const connectStrava = async () => {
    setBusy(true)
    setError(null)
    try {
      const { configured, connected } = await api.stravaStatus()
      setBusy(false)
      if (connected) return startScan('strava')
      if (!configured) {
        setError('Strava n\'est pas configuré sur ce serveur : crée une app sur '
          + 'strava.com/settings/api et renseigne STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET.')
        return
      }
      window.location.href = '/api/strava/connect'
    } catch (e) {
      setBusy(false)
      setError(String(e.message || e))
    }
  }

  const connectGarmin = async () => {
    setBusy(true)
    setError(null)
    try {
      const { connected } = await api.garminStatus()
      setBusy(false)
      if (connected) return startScan('garmin')
      setAuthError(null)
      setMfaNeeded(false)
      setStep('garmin-login')
    } catch (e) {
      setBusy(false)
      setError(AUTH_ERRORS[e.message] || String(e.message || e))
    }
  }

  const submitLogin = async () => {
    setBusy(true)
    setAuthError(null)
    try {
      const res = await api.garminLogin(email.trim(), password)
      setPassword('')
      setBusy(false)
      if (res.status === 'mfa_required') return setMfaNeeded(true)
      startScan('garmin')
    } catch (e) {
      setBusy(false)
      setAuthError(AUTH_ERRORS[e.message] || String(e.message || e))
      if (e.message === 'no_pending_login') setMfaNeeded(false)
    }
  }

  const submitMfa = async () => {
    setBusy(true)
    setAuthError(null)
    try {
      await api.garminMfa(mfaCode)
      setBusy(false)
      startScan('garmin')
    } catch (e) {
      setBusy(false)
      setAuthError(AUTH_ERRORS[e.message] || String(e.message || e))
      if (e.message === 'no_pending_login') setMfaNeeded(false)
    }
  }

  const startScan = async (chosenMode) => {
    setMode(chosenMode)
    setStep('scan')
    setError(null)
    const t0 = Date.now()
    try {
      const res = await api.analyze(chosenMode)
      // the scan screen is part of the show — let it breathe ≥1.6 s
      await new Promise((r) => setTimeout(r, Math.max(0, 1600 - (Date.now() - t0))))
      setAnalysis(res)
      setSelected(res.recommendation.recommended)
      setStep('reveal')
    } catch (e) {
      setError(String(e.message || e))
      setStep('connect')
    }
  }

  const confirm = async () => {
    setBusy(true)
    try {
      await api.choose(mode, selected, name || 'Héros')
      onDone()
    } catch (e) {
      setError(String(e.message || e))
      setBusy(false)
    }
  }

  return (
    <div className="onb screen">
      {step === 'welcome' && (
        <>
          <div style={{ textAlign: 'center' }}>
            <HeroSprite playerClass="rodeur" size={120} halo="rgba(62,230,193,0.4)" />
            <h1 className="px" style={{ marginTop: 24 }}>FITQUEST</h1>
            <p style={{ color: 'var(--ink-dim)', marginTop: 16, fontSize: 15, lineHeight: 1.6 }}>
              Ton corps est ton personnage.<br />
              Chaque séance de sport te fait gagner de l'expérience,<br />
              monter de niveau et affronter des boss.
            </p>
          </div>
          <div className="cta-zone">
            <button className="px-btn" onClick={() => setStep('connect')}>COMMENCER L'AVENTURE</button>
          </div>
        </>
      )}

      {step === 'connect' && (
        <>
          <h1 className="px" style={{ fontSize: 15, lineHeight: 1.8 }}>Relie ton grimoire de données</h1>
          <p style={{ color: 'var(--ink-dim)', fontSize: 14, lineHeight: 1.6 }}>
            FitQuest lit tes 4 dernières semaines d'entraînement pour découvrir
            quel héros tu es déjà. L'effort est jugé <b style={{ color: 'var(--ink)' }}>relatif à toi</b> —
            jamais aux autres.
          </p>
          {error && (
            <div className="px-panel" style={{ color: 'var(--neon-boss)', fontSize: 12 }}>
              Connexion Garmin impossible : {error} — réessaie ou pars en mode démo.
            </div>
          )}
          <div className="cta-zone">
            <button className="px-btn" disabled={busy} onClick={connectGarmin}>⌚ CONNECTER GARMIN</button>
            <button className="px-btn" disabled={busy} onClick={connectStrava}
              style={{ background: '#fc5200', boxShadow: '0 4px 0 #7a2800, 0 0 24px rgba(252,82,0,0.35)' }}>
              🏃 CONNECTER STRAVA
            </button>
            <button className="px-btn ghost" onClick={() => startScan('demo')}>MODE DÉMO (SANS COMPTE)</button>
          </div>
          <p style={{ color: 'var(--ink-dim)', fontSize: 11, textAlign: 'center' }}>
            Pas de montre Garmin ? Strava fonctionne avec Apple Watch, Polar,
            Suunto, Coros… et même un simple téléphone.
          </p>
        </>
      )}

      {step === 'garmin-login' && (
        <>
          <h1 className="px" style={{ fontSize: 15, lineHeight: 1.8 }}>
            {mfaNeeded ? 'Sceau de protection' : 'Pacte avec Garmin'}
          </h1>
          <p style={{ color: 'var(--ink-dim)', fontSize: 13, lineHeight: 1.6 }}>
            {mfaNeeded
              ? 'Garmin vient de t\'envoyer un code (email ou app). Saisis-le pour sceller le pacte.'
              : 'Tes identifiants partent directement vers Garmin depuis ton propre serveur ' +
                'et n\'y sont jamais stockés — seuls des jetons (~1 an) sont conservés.'}
          </p>
          {authError && (
            <div className="px-panel" style={{ color: 'var(--neon-boss)', fontSize: 12 }}>
              {authError}
            </div>
          )}
          {!mfaNeeded ? (
            <>
              <input
                type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="Email Garmin" autoComplete="username"
                style={{
                  background: 'var(--bg-panel)', border: 'none', color: 'var(--ink)',
                  padding: '14px', fontFamily: 'var(--body)', fontSize: 14, width: '100%',
                  textAlign: 'center', outline: 'none',
                }}
              />
              <input
                type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="Mot de passe" autoComplete="current-password"
                onKeyDown={(e) => { if (e.key === 'Enter' && email && password && !busy) submitLogin() }}
                style={{
                  background: 'var(--bg-panel)', border: 'none', color: 'var(--ink)',
                  padding: '14px', fontFamily: 'var(--body)', fontSize: 14, width: '100%',
                  textAlign: 'center', outline: 'none',
                }}
              />
              <div className="cta-zone">
                <button className="px-btn" disabled={busy || !email || !password} onClick={submitLogin}>
                  {busy ? 'CONNEXION…' : 'SE CONNECTER'}
                </button>
                <button className="px-btn ghost" onClick={() => setStep('connect')}>← RETOUR</button>
              </div>
            </>
          ) : (
            <>
              <input
                inputMode="numeric" value={mfaCode} maxLength={6}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                placeholder="Code à 6 chiffres" autoComplete="one-time-code"
                onKeyDown={(e) => { if (e.key === 'Enter' && mfaCode.length >= 6 && !busy) submitMfa() }}
                style={{
                  background: 'var(--bg-panel)', border: 'none', color: 'var(--ink)',
                  padding: '14px', fontFamily: 'var(--px)', fontSize: 14, width: '100%',
                  textAlign: 'center', outline: 'none', letterSpacing: 6,
                }}
              />
              <div className="cta-zone">
                <button className="px-btn" disabled={busy || mfaCode.length < 6} onClick={submitMfa}>
                  {busy ? 'VÉRIFICATION…' : 'VALIDER LE CODE'}
                </button>
                <button className="px-btn ghost" onClick={() => setMfaNeeded(false)}>← IDENTIFIANTS</button>
              </div>
            </>
          )}
        </>
      )}

      {step === 'scan' && (
        <div style={{ textAlign: 'center' }}>
          <h2 className="px" style={{ marginBottom: 28 }}>Lecture des runes…</h2>
          <div className="scan-bar" />
          <p style={{ color: 'var(--ink-dim)', fontSize: 13, marginTop: 24 }}>
            Analyse de tes 4 dernières semaines d'activités
          </p>
        </div>
      )}

      {step === 'reveal' && analysis && (
        <>
          <h1 className="px" style={{ fontSize: 14, lineHeight: 1.8, textAlign: 'center' }}>
            D'après tes {analysis.activityCount} activités,<br />tu es à{' '}
            <span style={{ color: 'var(--gold)' }}>
              {analysis.recommendation.affinities[analysis.recommendation.recommended]}%
            </span>{' '}
            un<br />
            <span style={{ color: analysis.classes[analysis.recommendation.recommended].color, fontSize: 18 }}>
              {analysis.classes[analysis.recommendation.recommended].name.toUpperCase()}
            </span>
          </h1>
          <div className="class-scroll">
            {Object.entries(analysis.classes).map(([key, cls]) => (
              <div
                key={key}
                className={`class-card${selected === key ? ' selected' : ''}`}
                style={{ '--card-glow': `${cls.color}44` }}
                onClick={() => setSelected(key)}
              >
                {key === analysis.recommendation.recommended && <span className="badge-reco">RECO</span>}
                <HeroSprite playerClass={key} size={72} idle={selected === key} />
                <div className="cname" style={{ color: cls.color }}>{cls.name}</div>
                <div className="ctag">{cls.tagline} — {cls.favors}</div>
                <div className="affinity">AFFINITÉ {analysis.recommendation.affinities[key]}%</div>
              </div>
            ))}
          </div>
          <p style={{ color: 'var(--ink-dim)', fontSize: 12, textAlign: 'center' }}>
            Choix non définitif : tu pourras changer de classe une fois par saison.
          </p>
          <div className="cta-zone">
            <button className="px-btn" disabled={!selected} onClick={() => setStep('confirm')}>
              CHOISIR {selected ? analysis.classes[selected].name.toUpperCase() : ''}
            </button>
          </div>
        </>
      )}

      {step === 'confirm' && analysis && selected && (
        <>
          <div style={{ textAlign: 'center' }}>
            <HeroSprite playerClass={selected} size={120} halo={`${analysis.classes[selected].color}66`} />
            <h1 className="px" style={{ fontSize: 16, marginTop: 18, color: analysis.classes[selected].color }}>
              {analysis.classes[selected].name.toUpperCase()}
            </h1>
            <p style={{ color: 'var(--ink-dim)', fontSize: 13, marginTop: 10 }}>
              {analysis.classes[selected].tagline}. XP ×1.5 sur : {analysis.classes[selected].favors}.
            </p>
          </div>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nom de ton héros (optionnel)"
            maxLength={16}
            style={{
              background: 'var(--bg-panel)', border: 'none', color: 'var(--ink)',
              padding: '14px', fontFamily: 'var(--px)', fontSize: 11, width: '100%',
              textAlign: 'center', outline: 'none',
            }}
          />
          <p style={{ color: 'var(--ink-dim)', fontSize: 12, textAlign: 'center' }}>
            🎁 Ton passé compte : tes {analysis.activityCount} dernières activités
            seront converties en XP de départ.
          </p>
          <div className="cta-zone">
            <button className="px-btn" disabled={busy} onClick={confirm}>
              {busy ? 'INVOCATION…' : "ENTRER DANS L'ARÈNE"}
            </button>
            <button className="px-btn ghost" onClick={() => setStep('reveal')}>← REVOIR LES CLASSES</button>
          </div>
        </>
      )}

      <div className="dots">
        {STEPS.map((s, i) => <span key={s} className={i <= stepIndex ? 'on' : ''} />)}
      </div>
    </div>
  )
}
