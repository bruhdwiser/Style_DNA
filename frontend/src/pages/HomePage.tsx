import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { ProductCard } from '@/components/product-card'
import { api, type ProductItem } from '@/lib/api'
import { usePageTracking } from '@/lib/tracking'

const edits = [
  {
    number: '01',
    title: 'Out the door',
    note: 'A good shirt earns its keep.',
    category: 'casual',
    image: '/trendy-streetwear-fashion-collection.png',
  },
  {
    number: '02',
    title: 'The long lunch',
    note: 'Easy does it. With intention.',
    category: 'formal',
    image: '/elegant-formal-business-attire-collection.png',
  },
  {
    number: '03',
    title: 'After dark',
    note: 'A little more than the usual.',
    category: 'luxury',
    image: '/elegant-woman-in-minimalist-fashion-outfit.png',
  },
]

export default function HomePage() {
  usePageTracking()
  const [featuredProducts, setFeaturedProducts] = useState<ProductItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.products.list({ limit: 4 })
      .then((res) => setFeaturedProducts(res.items || []))
      .catch((err) => console.error('Failed to load featured products:', err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-shell home-page">
      <Navigation />
      <section className="home-hero" aria-label="Editorial overview">
        <div className="home-hero-inner">
          <div className="home-hero-copy">
            <p className="eyebrow">STYLESENSE / EDITORIAL STUDY 001</p>
            <h1>Get dressed.<br /><em>Go somewhere.</em></h1>
            <div className="home-hero-bottom">
              <p>Good clothes are already in your orbit.<br />Let’s put them together.</p>
              <div className="home-hero-actions">
                <Link to="/shop" className="home-primary-link">WALK THE RACK <span>→</span></Link>
                <Link to="/outfits" className="home-secondary-link">BUILD A LOOK <span>↗</span></Link>
              </div>
            </div>
          </div>
        </div>
        <div className="hero-editorial-badge" aria-hidden="true">
          <span>EDITORIAL ARCHIVES / VOL. 01</span>
          <span>ARCHITECTURAL SILHOUETTES & EVERYDAY LAYERS</span>
        </div>
        <div className="home-hero-index" aria-hidden="true">01 <span>—</span> 04</div>
      </section>

      <main className="home-main">

        <section className="home-edits content-section">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">PICK YOUR PLOT</p>
              <h2>What’s the plan?</h2>
            </div>
            <Link to="/shop" className="text-arrow-link">ALL PIECES <span>→</span></Link>
          </div>
          <div className="edit-grid">
            {edits.map((edit) => (
              <Link to={`/shop?category=${edit.category}`} key={edit.number} className="edit-tile">
                <div className="edit-tile-image">
                  <img src={edit.image} alt="" loading="lazy" />
                  <span className="edit-number">{edit.number}</span>
                  <span className="edit-arrow" aria-hidden="true">↗</span>
                </div>
                <div className="edit-tile-copy">
                  <h3>{edit.title}</h3>
                  <p>{edit.note}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="home-featured content-section">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">ON THE RACK RIGHT NOW</p>
              <h2>Pieces with mileage.</h2>
            </div>
            <Link to="/shop" className="text-arrow-link">SEE EVERYTHING <span>→</span></Link>
          </div>
          {loading ? (
            <div className="product-grid home-product-grid" aria-label="Loading pieces">
              {[1, 2, 3, 4].map((i) => <div className="product-skeleton" key={i} />)}
            </div>
          ) : featuredProducts.length ? (
            <div className="product-grid home-product-grid">
              {featuredProducts.map((product) => <ProductCard key={product.id} {...product} />)}
            </div>
          ) : (
            <div className="home-empty-edit">
              <p>The rack is quiet for a moment.</p>
              <Link to="/shop">TAKE A LOOK AROUND →</Link>
            </div>
          )}
        </section>

        <section className="home-note">
          <p className="eyebrow">A SMALL NOTE FROM THE FITTING ROOM</p>
          <p className="home-note-line">You own the shirt.<br /><em>We found the outfit.</em></p>
          <Link to="/outfits" className="home-note-link">PULL A FEW LOOKS <span>→</span></Link>
        </section>
      </main>
      <Footer />
    </div>
  )
}
