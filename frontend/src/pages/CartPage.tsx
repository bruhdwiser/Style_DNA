import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { useCart } from '@/contexts/cart-context'
import { resolveColor } from '@/lib/utils'
import { usePageTracking } from '@/lib/tracking'

export default function CartPage() {
  usePageTracking()
  const { state, updateQuantity, removeItem, clearCart } = useCart()
  const shippingCost = state.total > 2000 || state.total === 0 ? 0 : 199
  const tax = state.total * 0.18
  const finalTotal = state.total + shippingCost + tax

  return (
    <div className="page-shell cart-page">
      <Navigation />
      <main className="page-main cart-main">
        <div className="cart-heading">
          <div>
            <p className="eyebrow">STYLESENSE / THE BAG</p>
            <h1>Your bag<span>.</span></h1>
          </div>
          <span className="cart-item-count">{String(state.itemCount).padStart(2, '0')} PIECES</span>
        </div>

        {!state.items.length ? (
          <section className="cart-empty">
            <span className="eyebrow">NOTHING HERE YET</span>
            <h2>A little room<br /><em>for something good.</em></h2>
            <Link to="/shop" className="home-primary-link">WALK THE RACK <span>→</span></Link>
          </section>
        ) : (
          <div className="cart-layout">
            <section className="cart-items" aria-label="Items in your bag">
              <div className="cart-items-heading">
                <span className="eyebrow">YOUR SELECTION</span>
                <button type="button" onClick={clearCart}>EMPTY BAG ×</button>
              </div>
              {state.items.map((item, index) => (
                <article className="cart-item" key={`${item.id}-${item.selectedColor || 'no-color'}-${item.selectedSize || 'no-size'}`}>
                  <span className="cart-item-index">{String(index + 1).padStart(2, '0')}</span>
                  <Link to={`/shop/${item.id}`} className="cart-item-image">
                    <img src={item.image || '/placeholder.svg'} alt={item.name} />
                  </Link>
                  <div className="cart-item-info">
                    <div>
                      <p className="eyebrow">{item.category || 'PIECE'}</p>
                      <Link to={`/shop/${item.id}`} className="cart-item-name">{item.name}</Link>
                      <div className="cart-item-variants">
                        {item.selectedColor && <span><i style={{ backgroundColor: resolveColor(item.selectedColor) }} />{item.selectedColor}</span>}
                        {item.selectedSize && <span>SIZE / {item.selectedSize}</span>}
                      </div>
                    </div>
                    <div className="cart-item-bottom">
                      <div className="quantity-control" aria-label={`Quantity for ${item.name}`}>
                        <button type="button" onClick={() => updateQuantity(item.id, item.quantity - 1)} disabled={item.quantity <= 1} aria-label="Decrease quantity">−</button>
                        <span>{String(item.quantity).padStart(2, '0')}</span>
                        <button type="button" onClick={() => updateQuantity(item.id, item.quantity + 1)} aria-label="Increase quantity">+</button>
                      </div>
                      <span className="cart-item-price">₹{(item.price * item.quantity).toFixed(0)}</span>
                    </div>
                  </div>
                  <button type="button" className="cart-item-remove" onClick={() => removeItem(item.id)}>REMOVE</button>
                </article>
              ))}
              <Link to="/shop" className="cart-continue">← KEEP LOOKING</Link>
            </section>

            <aside className="cart-summary">
              <p className="eyebrow">THE NUMBERS</p>
              <h2>Order note<span>.</span></h2>
              <dl>
                <div><dt>SUBTOTAL</dt><dd>₹{state.total.toFixed(0)}</dd></div>
                <div><dt>DELIVERY</dt><dd>{shippingCost === 0 ? 'ON US' : `₹${shippingCost.toFixed(0)}`}</dd></div>
                <div><dt>GST / 18%</dt><dd>₹{tax.toFixed(0)}</dd></div>
                <div className="cart-total"><dt>ESTIMATED TOTAL</dt><dd>₹{finalTotal.toFixed(0)}</dd></div>
              </dl>
              {state.total < 2000 && state.total > 0 && (
                <p className="cart-delivery-note">₹{(2000 - state.total).toFixed(0)} away from complimentary delivery.</p>
              )}
              <Button size="lg" className="cart-checkout" disabled>
                CHECKOUT NOT AVAILABLE YET
              </Button>
              <p className="cart-tax-note">Your bag is saved here. Online payment is not connected yet.</p>
            </aside>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}
