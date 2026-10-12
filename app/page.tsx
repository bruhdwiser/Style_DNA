"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Sparkles, TrendingUp, User } from "lucide-react"
import Link from "next/link"
import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import { AiChatbot } from "@/components/ai-chatbot"
import { useEffect, useRef, useState } from "react"
import dynamic from "next/dynamic"

// Dynamically import the entire Scene3D component to avoid SSR issues
const Scene3D = dynamic(() => import("./Scene3D"), { 
  ssr: false,
  loading: () => <div className="w-full h-full bg-gradient-to-br from-primary/5 to-secondary/5 animate-pulse" />
})

function useScrollAnimation() {
  const [scrollY, setScrollY] = useState(0)

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY)
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return scrollY
}

export default function HomePage() {
  const scrollY = useScrollAnimation()
  const heroRef = useRef<HTMLDivElement>(null)
  const featuresRef = useRef<HTMLDivElement>(null)
  const collectionsRef = useRef<HTMLDivElement>(null)
  const [isChatbotOpen, setIsChatbotOpen] = useState(false)
  const [initialMessage, setInitialMessage] = useState('')

  const handleStyleQuiz = () => {
    setInitialMessage('Take Style quiz')
    setIsChatbotOpen(true)
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("animate-in")
          }
        })
      },
      { threshold: 0.1 },
    )

    const elements = document.querySelectorAll(".scroll-animate")
    elements.forEach((el) => observer.observe(el))

    return () => observer.disconnect()
  }, [])

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <Navigation />

      {/* Hero Section - Bulgari Video */}
      <section className="relative h-screen w-full overflow-hidden">
        {/* Video Background */}
        <div className="absolute inset-0 will-change-transform">
          <video
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            className="w-full h-full object-cover"
            style={{ transform: 'translateZ(0)' }}
          >
            <source src="/ff_grid/bvlgary.mp4" type="video/mp4" />
            Your browser does not support the video tag.
          </video>
          
          {/* Subtle Gradient Overlays for blending - Fixed position to prevent jitter */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-background/60 pointer-events-none" style={{ transform: 'translateZ(0)' }} />
          <div className="absolute inset-0 bg-gradient-to-t from-background/40 via-transparent to-transparent pointer-events-none" style={{ transform: 'translateZ(0)' }} />
        </div>
      </section>

      {/* Featured Looks Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out">
            <h2 className="font-sans font-bold text-4xl md:text-5xl mb-4">
              <span className="gradient-text">Featured Looks</span>
            </h2>
            <p className="font-serif text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
              Inspired by the latest trends. Discover styles that blend elegance and modernity.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div
              className="relative overflow-hidden rounded-3xl shadow-2xl card-hover scroll-animate opacity-0 translate-y-8 group"
            >
              <img
                src="/zara1.jpg"
                alt="Zara Inspired Look 1"
                className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-accent/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="absolute bottom-0 left-0 right-0 p-8 transform translate-y-8 group-hover:translate-y-0 transition-transform duration-500">
                <h3 className="font-sans font-bold text-3xl mb-2 text-white drop-shadow-lg">Elegant Minimalism</h3>
                <p className="font-serif text-lg text-white/90 drop-shadow-md">Timeless pieces with a modern twist</p>
              </div>
            </div>
            <div
              className="relative overflow-hidden rounded-3xl shadow-2xl card-hover scroll-animate opacity-0 translate-y-8 group"
              style={{ animationDelay: "200ms" }}
            >
              <img
                src="/zara2.jpg"
                alt="Zara Inspired Look 2"
                className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="absolute inset-0 bg-gradient-to-br from-secondary/20 via-transparent to-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="absolute bottom-0 left-0 right-0 p-8 transform translate-y-8 group-hover:translate-y-0 transition-transform duration-500">
                <h3 className="font-sans font-bold text-3xl mb-2 text-white drop-shadow-lg">Urban Chic</h3>
                <p className="font-serif text-lg text-white/90 drop-shadow-md">Bold statements for the city streets</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Video Showcase Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8 aurora-glow">
        <div className="absolute inset-0 bg-gradient-to-b from-background via-black/50 to-background dark:from-background dark:via-black/80 dark:to-background" />
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-12 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out">
            <h2 className="font-sans font-bold text-4xl md:text-5xl text-white mb-4">
              Spring-Summer 2026 Show
            </h2>
            <p className="font-serif text-xl text-gray-300 max-w-2xl mx-auto">
              Experience the future of fashion with our exclusive runway preview.
            </p>
          </div>
          <div 
            className="relative rounded-3xl overflow-hidden shadow-2xl scroll-animate opacity-0 scale-95 transition-all duration-1000 ease-out border-2 border-white/10"
            style={{ animationDelay: "200ms" }}
          >
            <video
              autoPlay
              muted
              loop
              playsInline
              className="w-full h-auto max-h-[70vh] object-cover"
              poster="/placeholder.svg"
            >
              <source src="/diordemo.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/10 pointer-events-none mix-blend-overlay" />
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="absolute inset-0 gradient-bg opacity-30" />
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out">
            <h2 className="font-sans font-bold text-4xl md:text-5xl mb-4">
              What Our Users <span className="gradient-text">Say</span>
            </h2>
            <p className="font-serif text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
              Hear from fashion enthusiasts who've transformed their style with Flashfits.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                quote: "Flashfits completely changed how I shop. The AI recommendations are spot-on!",
                author: "Saniya V.",
                role: "Actress",
                delay: "0ms",
              },
              {
                quote: "I discovered styles I never thought I'd love. It's like having a personal stylist.",
                author: "Tom C.",
                role: "Creative Director",
                delay: "200ms",
              },
              {
                quote: "The trend insights keep me ahead of the curve. Highly recommend!",
                author: "Brad P.",
                role: "Influencer",
                delay: "400ms",
              },
            ].map((testimonial, index) => (
              <Card
                key={index}
                className="p-8 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out card-hover glass border-2 border-primary/10 backdrop-blur-lg"
                style={{ animationDelay: testimonial.delay }}
              >
                <CardContent className="pt-0">
                  <div className="mb-6">
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary via-secondary to-accent flex items-center justify-center mb-4 shadow-lg">
                      <Sparkles className="h-7 w-7 text-white" />
                    </div>
                    <p className="font-serif italic text-lg text-foreground leading-relaxed">"{testimonial.quote}"</p>
                  </div>
                  <div className="flex items-center">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-bold text-lg mr-4 shadow-md">
                      {testimonial.author[0]}
                    </div>
                    <div>
                      <p className="font-sans font-bold text-foreground">{testimonial.author}</p>
                      <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Fashion Gallery - Pinterest-like Grid */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5 dark:from-primary/10 dark:via-secondary/10 dark:to-accent/10" />
        
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <h2 className="font-sans font-bold text-4xl md:text-5xl mb-4">
              Trending <span className="gradient-text">Collections</span>
            </h2>
            <p className="font-serif text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
              Discover the latest fashion moments from luxury brands around the world.
            </p>
          </div>
          
          {/* Horizontal Scrolling Container */}
          <div className="relative">
            <div className="overflow-x-auto scrollbar-hide pb-6">
              <div className="flex gap-6 w-max">
                {/* Video/Image Cards */}
                {[
                  { src: '/ff_grid/saint.mp4', title: 'Saint Laurent', type: 'video' },
                  { src: '/ff_grid/dior.mp4', title: 'Dior', type: 'video' },
                  { src: '/ff_grid/lux1.mp4', title: 'Gucci', type: 'video' },
                  { src: '/ff_grid/cos.mp4', title: 'Cos', type: 'video' },
                  { src: '/ff_grid/blacksuit.mp4', title: 'BRND', type: 'video' },
                  { src: '/ff_grid/prada.mp4', title: 'Prada', type: 'video' },
                ].map((item, index) => (
                  <div
                    key={index}
                    className="relative group flex-shrink-0 w-80 h-96 rounded-2xl overflow-hidden shadow-xl hover:shadow-2xl transition-all duration-500 cursor-pointer"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    {item.type === 'video' ? (
                      <video
                        autoPlay
                        muted
                        loop
                        playsInline
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                      >
                        <source src={item.src} type="video/mp4" />
                      </video>
                    ) : (
                      <img
                        src={item.src}
                        alt={item.title}
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                      />
                    )}
                    
                    {/* Gradient Overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-60 group-hover:opacity-80 transition-opacity duration-500" />
                    
                    {/* Title */}
                    <div className="absolute bottom-0 left-0 right-0 p-6 transform translate-y-2 group-hover:translate-y-0 transition-transform duration-500">
                      <h3 className="font-sans font-bold text-2xl text-white drop-shadow-lg">{item.title}</h3>
                    </div>
                    
                    {/* Hover Border Glow */}
                    <div className="absolute inset-0 border-2 border-primary/0 group-hover:border-primary/50 rounded-2xl transition-all duration-500" />
                  </div>
                ))}
              </div>
            </div>
            
            {/* Scroll Indicator */}
            <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 flex gap-2">
              <div className="w-2 h-2 rounded-full bg-primary/50"></div>
              <div className="w-2 h-2 rounded-full bg-primary/30"></div>
              <div className="w-2 h-2 rounded-full bg-primary/30"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-muted/30 via-background to-muted/30" />

        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out">
            <h2 className="font-sans font-bold text-4xl md:text-5xl mb-4">
              Why Choose <span className="gradient-text">Flashfits?</span>
            </h2>
            <p className="font-serif text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
              Our AI-powered platform learns your preferences to deliver personalized fashion recommendations.
            </p>
          </div>

          <div ref={featuresRef} className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: Sparkles,
                title: "AI Recommendations",
                desc: "Advanced algorithms analyze your style preferences to suggest perfect matches.",
                gradient: "from-primary to-secondary",
                delay: "0ms",
              },
              {
                icon: TrendingUp,
                title: "Trend Insights",
                desc: "Stay ahead with curated trends and seasonal fashion insights.",
                gradient: "from-secondary to-accent",
                delay: "200ms",
              },
              {
                icon: User,
                title: "Personal Styling",
                desc: "Get personalized styling advice tailored to your body type and lifestyle.",
                gradient: "from-accent to-primary",
                delay: "400ms",
              },
            ].map((feature, index) => (
              <Card
                key={index}
                className="text-center p-8 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out card-hover glass border-2 border-primary/10 backdrop-blur-md group relative overflow-hidden"
                style={{ animationDelay: feature.delay }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardContent className="pt-6 relative z-10">
                  <div
                    className={`w-16 h-16 bg-gradient-to-br ${feature.gradient} rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg group-hover:scale-110 group-hover:rotate-6 transition-all duration-500`}
                  >
                    <feature.icon className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="font-sans font-bold text-2xl mb-4 group-hover:gradient-text transition-all duration-300">{feature.title}</h3>
                  <p className="font-serif text-muted-foreground text-lg leading-relaxed group-hover:text-foreground transition-colors duration-300">{feature.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-24 px-4 sm:px-6 lg:px-8 overflow-hidden">
        <div className="absolute inset-0 gradient-bg opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/50 to-transparent" />
        
        <div className="max-w-4xl mx-auto text-center relative z-10 scroll-animate opacity-0 translate-y-8 transition-all duration-1000 ease-out">
          <div className="glass rounded-3xl p-12 md:p-16 backdrop-blur-xl border-2 border-white/10 shadow-2xl">
            <h2 className="font-sans font-bold text-4xl md:text-5xl mb-6">
              Ready to Transform Your <span className="gradient-text">Wardrobe?</span>
            </h2>
            <p className="font-serif text-xl md:text-2xl text-muted-foreground mb-10 leading-relaxed">
              Join thousands of fashion enthusiasts who trust Flashfits for their style journey.
            </p>
            <Link href="/shop">
              <Button
                size="lg"
                className="px-10 py-7 text-xl font-semibold rounded-2xl bg-gradient-to-r from-primary via-secondary to-accent hover:shadow-2xl hover:shadow-primary/50 transform hover:scale-110 transition-all duration-300 border-0 relative overflow-hidden group"
              >
                <span className="relative z-10 flex items-center gap-3">
                  <Sparkles className="h-6 w-6" />
                  Explore Collections
                </span>
                <div className="absolute inset-0 bg-gradient-to-r from-accent via-primary to-secondary opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />

      <style jsx global>{`
        .animate-in {
          opacity: 1 !important;
          transform: translateY(0) !important;
        }
      `}</style>

      {/* AI Chatbot */}
      <AiChatbot 
        isOpen={isChatbotOpen} 
        onClose={() => setIsChatbotOpen(false)}
        initialMessage={initialMessage}
      />
    </div>
  )
}
