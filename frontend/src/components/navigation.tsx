import React, { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useCart } from '@/contexts/cart-context'
import { useAuth } from '@/contexts/auth-context'

const links = [
  { to: '/shop', label: 'THE RACK', number: '01' },
  { to: '/wardrobe', label: 'YOUR CLOSET', number: '02' },
  { to: '/outfits', label: 'FITTING ROOM', number: '03' },
]

export function Navigation() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { state } = useCart()
  const { user, session, signOut } = useAuth()
  const navigate = useNavigate()

  const closeMenu = () => setMenuOpen(false)
  const handleSignOut = async () => {
    try {
      if (session?.access_token) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }).catch(() => {})
      }
    } catch {
      // Best-effort backend notification
    }
    await signOut()
    closeMenu()
    navigate('/login')
  }

  return (
    <>
      <header className="masthead glass-masthead">
        <Link to="/" className="masthead-brand" aria-label="StyleSense home" onClick={closeMenu}>
          <img src="/logo-mark-light.png" alt="StyleSense logo" className="brand-logo-img" />
          <span>STYLESENSE</span>
        </Link>

        <nav className="masthead-nav" aria-label="Main navigation">
          {links.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `masthead-link${isActive ? ' is-active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
          <NavLink to="/ai" className={({ isActive }) => `masthead-link${isActive ? ' is-active' : ''}`}>
            SECOND OPINION
          </NavLink>
        </nav>

        <div className="masthead-actions">
          {user ? (
            <>
              <Link to="/settings" className="masthead-account" title={user.email || 'Account'}>
                ACCOUNT
              </Link>
              <button
                type="button"
                className="masthead-account"
                onClick={handleSignOut}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                title="Log out of StyleSense"
              >
                SIGN OUT
              </button>
            </>
          ) : (
            <Link to="/login" className="masthead-account">SIGN IN</Link>
          )}
          <Link to="/cart" className="masthead-bag" aria-label={`Bag, ${state.itemCount} items`}>
            BAG <span>[{String(state.itemCount).padStart(2, '0')}]</span>
          </Link>
          <button
            type="button"
            className="masthead-menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="mobile-index"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? 'CLOSE ×' : 'MENU +'}
          </button>
        </div>
      </header>

      {menuOpen && (
        <div className="mobile-index glass-surface" id="mobile-index">
          <p className="eyebrow">STYLESENSE / INDEX</p>
          {links.map((item) => (
            <Link key={item.to} to={item.to} onClick={closeMenu} className="mobile-index-link">
              <span>{item.number}</span>
              <span>{item.label}</span>
              <b>→</b>
            </Link>
          ))}
          <Link to="/style-dna" onClick={closeMenu} className="mobile-index-link">
            <span>04</span>
            <span>STYLE PROFILE</span>
            <b>→</b>
          </Link>
          <Link to="/ai" onClick={closeMenu} className="mobile-index-link">
            <span>05</span>
            <span>SECOND OPINION</span>
            <b>→</b>
          </Link>
          <div className="mobile-index-secondary">
            <Link to="/about" onClick={closeMenu}>ABOUT</Link>
            <Link to="/settings" onClick={closeMenu}>PRIVACY & SETTINGS</Link>
            {user ? (
              <button type="button" onClick={handleSignOut}>SIGN OUT</button>
            ) : (
              <Link to="/login" onClick={closeMenu}>SIGN IN</Link>
            )}
          </div>
        </div>
      )}
    </>
  )
}
