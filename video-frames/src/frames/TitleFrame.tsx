/**
 * SCENE 3 (0:12–0:18): Title card
 * Full screen dark background. Logo + tagline fade in.
 */
export default function TitleFrame() {
  return (
    <div className="w-full h-full relative flex items-center justify-center">
      {/* Cinematic radial background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at center, #1A2E20 0%, #0F1A14 100%)',
        }}
      />

      {/* Content stack — optically centered */}
      <div
        className="relative flex flex-col items-center"
        style={{ gap: '2.5rem', marginTop: '-30px' }}
      >
        {/* Main title */}
        <h1
          className="font-heading text-cream animate-in delay-0"
          style={{
            fontSize: '96px',
            fontWeight: 800,
            letterSpacing: '0.12em',
            lineHeight: 1,
            textAlign: 'center',
            textShadow: '0 0 80px rgba(212,160,23,0.15)',
            margin: 0,
          }}
        >
          FIELDPACK AI
        </h1>

        {/* Gold rule divider */}
        <div
          className="animate-fade delay-1"
          style={{
            height: '3px',
            width: '160px',
            background: '#D4A017',
            borderRadius: '2px',
          }}
        />

        {/* Tagline */}
        <p
          className="font-body text-cream-muted animate-in delay-2"
          style={{
            fontSize: '28px',
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            margin: 0,
          }}
        >
          Offline expert knowledge for the field
        </p>
      </div>
    </div>
  )
}
