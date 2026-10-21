import React from 'react'
import { Link } from 'react-router-dom'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { usePageTracking } from '@/lib/tracking'

export default function AboutPage() {
  usePageTracking()
  return (
    <div className="page-shell about-page">
      <Navigation />
      <main className="page-main about-main">
        <section className="about-cover">
          <p className="eyebrow">STYLESENSE / THE POINT OF IT</p>
          <h1>Less scrolling.<br /><em>More getting dressed.</em></h1>
          <p className="about-deck">A closet is full of possibilities. StyleSense helps you notice the combinations hiding in plain sight.</p>
          <Link to="/outfits" className="home-primary-link">STEP INTO THE FITTING ROOM <span>→</span></Link>
        </section>

        <section className="about-columns">
          <article>
            <span className="eyebrow">01 / START WITH YOUR RACK</span>
            <h2>Wear more of what you own.</h2>
            <p>Add pieces from your closet and build looks around the plans you already have. When a key piece is missing, see what would make the most combinations possible.</p>
          </article>
          <article>
            <span className="eyebrow">02 / HOW LOOKS ARE BUILT</span>
            <h2>Clear rules. Your call.</h2>
            <p>Outfit suggestions come from explicit garment, occasion, season, and colour rules. Your feedback can shift future rankings, but it never overrides whether a look fits the brief.</p>
          </article>
          <article>
            <span className="eyebrow">03 / YOUR INFORMATION</span>
            <h2>Private by default.</h2>
            <p>Closet photos are kept in private storage. Body guidance is optional and can be deleted. A separate permission controls whether a sanitized garment photo can be used for optional tag suggestions.</p>
            <Link to="/settings" className="about-text-link">READ YOUR PRIVACY SETTINGS →</Link>
          </article>
        </section>

        <section className="about-last-word">
          <p className="eyebrow">A FINAL THING</p>
          <p>There is no perfect outfit.<br /><em>There is the one you feel like yourself in.</em></p>
        </section>
      </main>
      <Footer />
    </div>
  )
}
