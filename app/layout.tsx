import type React from "react"
import type { Metadata } from "next"
import { Work_Sans, Open_Sans } from "next/font/google"
import "./globals.css"
import { CartProvider } from "@/contexts/cart-context"
import { ThemeProvider } from "@/contexts/theme-context"
import { CookieConsentProvider } from "@/contexts/cookie-consent-context"
import { CookieConsentBanner } from "@/components/cookie-consent-banner"
import { CookieSettingsDialog } from "@/components/cookie-settings-dialog"

const workSans = Work_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-work-sans",
})

const openSans = Open_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-open-sans",
})

export const metadata: Metadata = {
  title: "Flashfits - Personalized Fashion Platform",
  description: "Algorithm-based intuitive fashion platform for personalized shopping experience",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${workSans.variable} ${openSans.variable} antialiased`} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const theme = localStorage.getItem('theme');
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (theme === 'dark' || (!theme && prefersDark)) {
                  document.documentElement.classList.add('dark');
                } else {
                  document.documentElement.classList.remove('dark');
                }
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body suppressHydrationWarning>
        <ThemeProvider>
          <CookieConsentProvider>
            <CartProvider>
              {children}
              <CookieConsentBanner />
              <CookieSettingsDialog />
            </CartProvider>
          </CookieConsentProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
