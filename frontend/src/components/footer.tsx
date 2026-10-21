import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-topline">
        <span>STYLESENSE — GET DRESSED. GO SOMEWHERE.</span>
        <span>MADE FOR THE EVERYDAY EXIT.</span>
      </div>
      <div className="footer-main">
        <Link to="/" className="footer-wordmark">
          <img src="/logo-mark-light.png" alt="StyleSense logo" className="footer-logo-img" />
          <span>STYLESENSE<span>®</span></span>
        </Link>
        <p>Good clothes. Better combinations.<br />Your rack, with a point of view.</p>
        <nav className="footer-links" aria-label="Footer">
          <Link to="/about">ABOUT</Link>
          <Link to="/settings">PRIVACY</Link>
          <Link to="/settings">ACCOUNT</Link>
          <Link to="/admin">STOCK ROOM</Link>
        </nav>
      </div>
      <div className="footer-bottomline">
        <span>© {new Date().getFullYear()} STYLESENSE</span>
        <span>BUILT AROUND WHAT YOU ALREADY OWN.</span>
      </div>
    </footer>
  )
}
