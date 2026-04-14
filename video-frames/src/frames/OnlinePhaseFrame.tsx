import { MapPin, Clock, Search, Pill, Sprout, CloudSun, BookOpen } from 'lucide-react'

/**
 * SCENE 8 (0:55-1:10): Phase 1 mission briefing -- AI research agents
 * Five agents spin up before deployment. First 3 are active (amber glow),
 * last 2 are queued (dimmed). Staggered fade-in top to bottom.
 */

interface ActiveAgentRowProps {
  icon: React.ReactNode
  name: string
  animateClass: string
}

function GlowDot() {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: '#D4A017',
        flexShrink: 0,
        animation: 'dotPulse 1.4s ease-in-out infinite',
        boxShadow: '0 0 6px rgba(212,160,23,0.6)',
        alignSelf: 'center',
      }}
    />
  )
}

function ActiveAgentRow({ icon, name, animateClass }: ActiveAgentRowProps) {
  return (
    <div className={`${animateClass}`}>
      <div
        className="flex items-center gap-4 border-l-[3px] border-gold pl-4 rounded-lg p-4"
        style={{
          background: 'rgba(212,160,23,0.08)',
          boxShadow: '0 0 15px rgba(212,160,23,0.15)',
        }}
      >
        {/* Pulsing dot + icon cluster */}
        <div className="flex items-center gap-2 shrink-0">
          <GlowDot />
          <div className="text-gold w-6 h-6 shrink-0">
            {icon}
          </div>
        </div>
        <div className="flex-1 min-w-0 flex items-center flex-wrap gap-0">
          <span
            className="font-heading font-semibold text-cream leading-tight"
            style={{ fontSize: '22px' }}
          >
            {name}
          </span>
          <span
            className="bg-gold/20 text-gold tracking-[0.15em] uppercase font-bold px-2 py-0.5 rounded ml-3"
            style={{ fontSize: '12px' }}
          >
            ACTIVE
          </span>
        </div>
      </div>
    </div>
  )
}

interface QueuedAgentRowProps {
  icon: React.ReactNode
  name: string
  animateClass: string
}

function QueuedAgentRow({ icon, name, animateClass }: QueuedAgentRowProps) {
  return (
    <div className={`${animateClass}`}>
      <div
        className="flex items-center gap-4 border-l-[3px] pl-4 p-4 rounded-lg"
        style={{ borderColor: 'rgba(45,106,79,0.25)' }}
      >
        {/* Spacer to align with active rows' dot+icon cluster */}
        <div className="flex items-center gap-2 shrink-0">
          {/* placeholder dot: invisible, keeps column alignment */}
          <span style={{ width: 8, height: 8, flexShrink: 0 }} />
          <div
            className="w-6 h-6 shrink-0"
            style={{ color: 'rgba(200,194,184,0.45)' }}
          >
            {icon}
          </div>
        </div>
        <div className="flex-1 min-w-0 flex items-center flex-wrap gap-0">
          <span
            className="font-heading font-semibold leading-tight"
            style={{ color: 'rgba(200,194,184,0.55)', fontSize: '22px' }}
          >
            {name}
          </span>
          <span
            className="tracking-[0.15em] uppercase font-bold px-2 py-0.5 rounded ml-3 border"
            style={{
              background: 'rgba(200,194,184,0.12)',
              borderColor: 'rgba(200,194,184,0.50)',
              color: 'rgba(200,194,184,0.50)',
              fontSize: '12px',
            }}
          >
            QUEUED
          </span>
        </div>
      </div>
    </div>
  )
}

export default function OnlinePhaseFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-20" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Background photo -- woman planting in field */}
      <img
        src="/photos/persona_planting.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
      />
      {/* Dark overlay -- heavy, data needs to stay dominant */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.88)', pointerEvents: 'none' }}
      />
      <div className="w-full max-w-[680px]" style={{ position: 'relative' }}>

        {/* Header */}
        <div className="animate-in delay-0">
          <p
            className="font-body font-semibold text-green-light tracking-[0.2em] uppercase"
            style={{ fontSize: '18px' }}
          >
            PHASE 1 &middot; MISSION BRIEFING
          </p>
          <div className="h-px bg-green/30 w-full mt-3 mb-6" />
        </div>

        {/* Metadata */}
        <div className="flex flex-col gap-4 animate-in delay-1">
          {/* Location */}
          <div className="flex items-center gap-3">
            <MapPin className="w-4 h-4 text-gold shrink-0" />
            <span className="font-body text-cream-muted w-20" style={{ fontSize: '16px' }}>Location</span>
            <span className="font-body text-cream font-semibold" style={{ fontSize: '18px' }}>Casamance, Senegal</span>
          </div>
          {/* Status */}
          <div className="flex items-center gap-3">
            <Clock className="w-4 h-4 text-gold shrink-0" />
            <span className="font-body text-cream-muted w-20" style={{ fontSize: '16px' }}>Status</span>
            <span className="font-body text-cream font-semibold" style={{ fontSize: '18px' }}>Before deployment</span>
          </div>
        </div>

        {/* Agent Card */}
        <div className="bg-bg-card rounded-2xl border border-green/30 p-7 mt-8">

          {/* Card header */}
          <div className="animate-in delay-2 flex items-center gap-4">
            <span
              className="font-body font-semibold text-cream-muted tracking-[0.15em] uppercase shrink-0"
              style={{ fontSize: '14px' }}
            >
              AI Research Agents
            </span>
            <div className="flex-1 h-px bg-green/20" />
          </div>

          {/* Agent rows */}
          <div className="flex flex-col gap-4 mt-6">

            {/* Active agent 1 */}
            <ActiveAgentRow
              icon={<Search className="w-6 h-6" />}
              name="Cassava Disease Identification"
              animateClass="animate-in delay-3"
            />

            {/* Active agent 2 */}
            <ActiveAgentRow
              icon={<Pill className="w-6 h-6" />}
              name="Treatment &amp; Intervention"
              animateClass="animate-in delay-4"
            />

            {/* Active agent 3 */}
            <ActiveAgentRow
              icon={<Sprout className="w-6 h-6" />}
              name="Resistant Varieties"
              animateClass="animate-in delay-5"
            />

            {/* Separator: active cluster / queued cluster */}
            <div
              className="animate-in delay-5"
              style={{ height: 1, background: 'rgba(245,241,235,0.08)', margin: '2px 0' }}
            />

            {/* Queued agent 4 */}
            <QueuedAgentRow
              icon={<CloudSun className="w-6 h-6" />}
              name="Casamance Seasonal Climate"
              animateClass="animate-in delay-6"
            />

            {/* Queued agent 5 */}
            <QueuedAgentRow
              icon={<BookOpen className="w-6 h-6" />}
              name="Local Farmer Practices"
              animateClass="animate-in delay-7"
            />

          </div>
        </div>

        {/* Footer counter */}
        <p
          className="font-body text-green-light font-semibold mt-4 animate-in delay-8"
          style={{ fontSize: '16px' }}
        >
          3 of 5 agents active &mdash; initializing knowledge pack
        </p>

      </div>
    </div>
  )
}
