"use client"

import { useState } from "react"
import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AiChatbot } from "@/components/ai-chatbot"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Sphere, MeshDistortMaterial, Environment, Float } from "@react-three/drei"
import { Brain, Sparkles, Zap, Target, Palette, TrendingUp } from "lucide-react"
import { Suspense } from "react"

function AnimatedSphere() {
  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={2}>
      <Sphere args={[1, 100, 200]} scale={2}>
        <MeshDistortMaterial color="#06b6d4" attach="material" distort={0.3} speed={1.5} roughness={0} />
      </Sphere>
    </Float>
  )
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <AnimatedSphere />
      <Environment preset="studio" />
      <OrbitControls enableZoom={false} enablePan={false} />
    </>
  )
}

export default function FlashfitsAI() {
  const [isChatbotOpen, setIsChatbotOpen] = useState(false)

  const handleTryAIStyling = () => {
    setIsChatbotOpen(true)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      <Navigation />

      {/* Hero Section with 3D Elements */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* 3D Background */}
        <div className="absolute inset-0 opacity-30">
          <Canvas camera={{ position: [0, 0, 5] }}>
            <Suspense fallback={null}>
              <Scene />
            </Suspense>
          </Canvas>
        </div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="space-y-8">
            <Badge className="bg-cyan-500/20 text-cyan-300 border-cyan-500/30 px-4 py-2">
              <Brain className="h-4 w-4 mr-2" />
              Powered by Advanced AI
            </Badge>

            <h1 className="font-sans font-bold text-5xl md:text-7xl lg:text-8xl">
              <span className="bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                Flashfits AI
              </span>
            </h1>

            <p className="font-serif text-xl md:text-2xl text-gray-300 max-w-3xl mx-auto leading-relaxed">
              Experience the future of personalized fashion with our revolutionary AI that understands your style,
              predicts trends, and curates the perfect wardrobe just for you.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                onClick={handleTryAIStyling}
                size="lg"
                className="bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 text-white px-8 py-4 text-lg"
              >
                <Sparkles className="h-5 w-5 mr-2" />
                Try AI Styling
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="border-gray-600 text-gray-300 hover:bg-gray-800 px-8 py-4 text-lg bg-transparent"
              >
                Learn More
              </Button>
            </div>
          </div>
        </div>

        {/* Floating Elements */}
        <div className="absolute top-20 left-10 animate-pulse">
          <div className="w-3 h-3 bg-cyan-400 rounded-full"></div>
        </div>
        <div className="absolute top-40 right-20 animate-pulse delay-1000">
          <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
        </div>
        <div className="absolute bottom-40 left-20 animate-pulse delay-500">
          <div className="w-4 h-4 bg-pink-400 rounded-full"></div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="font-sans font-bold text-4xl md:text-5xl mb-6">AI-Powered Fashion Intelligence</h2>
            <p className="font-serif text-xl text-gray-400 max-w-2xl mx-auto">
              Our advanced algorithms analyze millions of fashion data points to deliver personalized recommendations
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card className="bg-slate-800/80 border-slate-700 backdrop-blur">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Target className="h-8 w-8 text-white" />
                </div>
                <h3 className="font-sans font-semibold text-2xl mb-4 text-white">Style Prediction</h3>
                <p className="text-gray-400 leading-relaxed">
                  Our AI analyzes your preferences, body type, and lifestyle to predict styles you'll love before you
                  even know it.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/80 border-slate-700 backdrop-blur">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Palette className="h-8 w-8 text-white" />
                </div>
                <h3 className="font-sans font-semibold text-2xl mb-4 text-white">Color Harmony</h3>
                <p className="text-gray-400 leading-relaxed">
                  Advanced color theory algorithms ensure every piece in your wardrobe complements your skin tone and
                  existing items.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/80 border-slate-700 backdrop-blur">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-teal-600 rounded-full flex items-center justify-center mx-auto mb-6">
                  <TrendingUp className="h-8 w-8 text-white" />
                </div>
                <h3 className="font-sans font-semibold text-2xl mb-4 text-white">Trend Forecasting</h3>
                <p className="text-gray-400 leading-relaxed">
                  Stay ahead of fashion trends with AI that monitors global fashion weeks, social media, and street
                  style.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-r from-slate-900 to-purple-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-sans font-bold text-4xl md:text-5xl mb-6">Ready to Transform Your Style?</h2>
          <p className="font-serif text-xl text-gray-300 mb-8 leading-relaxed">
            Join thousands of fashion-forward individuals who trust Flashfits AI to elevate their personal style.
          </p>
          <Button
            onClick={handleTryAIStyling}
            size="lg"
            className="bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 text-white px-12 py-4 text-lg"
          >
            <Zap className="h-5 w-5 mr-2" />
            Get Started Now
          </Button>
        </div>
      </section>

      <Footer />
      
      {/* AI Chatbot */}
      <AiChatbot isOpen={isChatbotOpen} onClose={() => setIsChatbotOpen(false)} />
    </div>
  )
}
