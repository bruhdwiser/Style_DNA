'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart3, Package, PlusCircle } from 'lucide-react'

export default function AdminDashboard() {
  return (
    <div className="min-h-screen bg-background py-12">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Manage your fashion store and track analytics
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Add Product Card */}
          <Link href="/admin/add-product">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <PlusCircle className="h-6 w-6 text-primary" />
                  <CardTitle>Add Product</CardTitle>
                </div>
                <CardDescription>
                  Add new products to your store
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Create new product listings with details, pricing, and inventory
                </p>
              </CardContent>
            </Card>
          </Link>

          {/* Analytics Card */}
          <Link href="/admin/analytics">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-6 w-6 text-primary" />
                  <CardTitle>Analytics</CardTitle>
                </div>
                <CardDescription>
                  View store analytics and insights
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Track visitor activity, page views, and user behavior
                </p>
              </CardContent>
            </Card>
          </Link>

          {/* Manage Products Card */}
          <Link href="/shop">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Package className="h-6 w-6 text-primary" />
                  <CardTitle>View Products</CardTitle>
                </div>
                <CardDescription>
                  Browse all products in store
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  View and manage your product catalog
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>

        <div className="mt-12">
          <Card>
            <CardHeader>
              <CardTitle>Quick Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-6 bg-primary/5 rounded-lg">
                  <p className="text-3xl font-bold text-primary mb-2">11</p>
                  <p className="text-sm text-muted-foreground">Total Products</p>
                </div>
                <div className="text-center p-6 bg-primary/5 rounded-lg">
                  <p className="text-3xl font-bold text-primary mb-2">4</p>
                  <p className="text-sm text-muted-foreground">Brands</p>
                </div>
                <div className="text-center p-6 bg-primary/5 rounded-lg">
                  <p className="text-3xl font-bold text-primary mb-2">Active</p>
                  <p className="text-sm text-muted-foreground">Store Status</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
