"use client"

import { useRef, useMemo } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { Sphere, Float } from "@react-three/drei"
import * as THREE from "three"

function FloatingSphere({
  position,
  color,
  size = 1,
}: { position: [number, number, number]; color: string; size?: number }) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.1
      meshRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.1
    }
  })

  const material = useMemo(
    () => new THREE.MeshStandardMaterial({ 
      color: color, 
      metalness: 0.8, 
      roughness: 0.2 
    }),
    [color]
  )

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
      <mesh ref={meshRef} position={position} material={material}>
        <sphereGeometry args={[size, 32, 32]} />
      </mesh>
    </Float>
  )
}

export default function Scene3D() {
  return (
    <Canvas 
      camera={{ position: [0, 0, 10], fov: 50 }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <FloatingSphere position={[-4, 2, 0]} color="#06b6d4" size={0.8} />
      <FloatingSphere position={[4, -1, -2]} color="#84cc16" size={0.6} />
      <FloatingSphere position={[2, 3, -1]} color="#f59e0b" size={0.4} />
      <FloatingSphere position={[-2, -2, 1]} color="#ec4899" size={0.5} />
      <FloatingSphere position={[0, 0, -3]} color="#8b5cf6" size={0.7} />
      <FloatingSphere position={[-3, -3, 2]} color="#10b981" size={0.3} />
      <FloatingSphere position={[3, 1, 1]} color="#f97316" size={0.5} />
    </Canvas>
  )
}