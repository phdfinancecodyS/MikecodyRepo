import Link from 'next/link';

export default function Home() {
  return (
    <main className="shell">
      {/* ---- Hero ---- */}
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">Free 2-minute check-in</div>
          <h1>You already know something feels off. Ask anyway.</h1>
          <p style={{ fontSize: '1.1rem', maxWidth: 520 }}>
            10 honest questions. A matched guide written for your exact situation.
            No sign-up required. Crisis resources stay visible the whole time.
          </p>
          <div className="hero-actions" style={{ marginTop: 22 }}>
            <Link className="btn" href="/quiz">Take the Free Check-In</Link>
          </div>
        </div>
        <aside className="hero-side hero-card">
          <div className="section-label">What you get</div>
          <ul>
            <li><strong>Personalized score</strong> across 10 dimensions of well-being</li>
            <li><strong>Matched guide</strong> for your topic, written for your audience</li>
            <li><strong>Next steps</strong> you can actually do this week</li>
            <li><strong>Crisis resources</strong> visible at every step, no exceptions</li>
          </ul>
        </aside>
      </section>

      {/* ---- How it works ---- */}
      <section style={{ marginTop: 48 }}>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>How it works</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {[
            { step: '1', title: 'Answer 10 questions', body: 'Honest, no-judgment check-in. Takes about 2 minutes.' },
            { step: '2', title: 'Get your score', body: 'We map your answers across mood, sleep, stress, connection, and more.' },
            { step: '3', title: 'Pick your lens', body: 'Choose an audience that fits (veteran, educator, parent, etc.) or keep it general.' },
            { step: '4', title: 'Get your guide', body: 'A matched guide with real talk, real tools, and next steps you can start today.' },
          ].map((item) => (
            <div key={item.step} className="panel" style={{ textAlign: 'center' }}>
              <div className="score-number">{item.step}</div>
              <h3 style={{ margin: '8px 0 4px' }}>{item.title}</h3>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---- Social proof placeholder ---- */}
      <section style={{ marginTop: 48, textAlign: 'center' }}>
        <div className="panel" style={{ maxWidth: 600, margin: '0 auto', padding: 32 }}>
          <p style={{ fontSize: '1.15rem', fontStyle: 'italic', color: 'var(--ink)' }}>
            &ldquo;I thought I was fine until question 4. The guide it matched me with
            said exactly what I needed to hear.&rdquo;
          </p>
          <p className="muted" style={{ marginTop: 8 }}>Beta tester, first responder</p>
        </div>
      </section>

      {/* ---- Second CTA ---- */}
      <section style={{ marginTop: 48, textAlign: 'center' }}>
        <h2>Ready?</h2>
        <p className="muted" style={{ marginBottom: 16 }}>No account needed. 100% private. Takes 2 minutes.</p>
        <Link className="btn" href="/quiz">Start the Check-In</Link>
      </section>

      {/* ---- Crisis footer ---- */}
      <section className="notice warning" style={{ marginTop: 48, borderRadius: 'var(--radius)' }}>
        <div className="section-label">Crisis resources</div>
        <ul className="crisis-list">
          <li><a href="tel:988">Call or text 988</a> (Suicide & Crisis Lifeline, 24/7)</li>
          <li><a href="sms:741741&body=HOME">Text HOME to 741741</a> (Crisis Text Line, 24/7)</li>
          <li><a href="tel:911">Call 911</a> for emergencies</li>
        </ul>
      </section>

      <p className="footer-note" style={{ textAlign: 'center' }}>
        Ask Anyway is educational, not therapy or diagnosis. Built by a licensed clinical social worker (LCSW)
        with personal loss experience. Crisis resources are always visible.
      </p>
    </main>
  );
}