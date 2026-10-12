import { NextResponse } from 'next/server'
import { supabaseServer, supabaseAdmin } from '@/lib/supabase/server'

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const id = params.id
  const supabase = await supabaseServer()

  try {
    // Try to fetch the product by id (numeric) or dbId
    let { data: product, error } = await supabase
      .from('products')
      .select('*')
      .eq('id', id)
      .single()

    // If not found by numeric id, try by dbId
    if (error && !product) {
      const result = await supabase
        .from('products')
        .select('*')
        .eq('dbId', id)
        .single()
      
      product = result.data
      error = result.error
    }

    if (error || !product) {
      return NextResponse.json(
        { error: 'Product not found' },
        { status: 404 }
      )
    }

    // Format the product data for the frontend
    const formattedProduct = {
      id: product.id as string,
      name: product.name as string,
      description: product.description as string,
      price: Math.round(((product.price_cents as number) ?? 0) / 100),
      originalPrice: product.original_price_cents ? Math.round((product.original_price_cents as number) / 100) : undefined,
      category: (product.category as string) ?? 'General',
      image: (product.image_url as string) ?? '/placeholder.svg',
      colors: (product.colors as string[]) ?? [],
      sizes: (product.sizes as string[]) ?? [],
      isNew: Boolean(product.is_new),
      isSale: Boolean(product.is_sale),
    }

    return NextResponse.json(formattedProduct)
  } catch (error) {
    console.error('Error fetching product:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(_req: Request, { params }: { params: { id: string } }) {
  const id = params.id
  
  // Use admin client to bypass RLS
  const supabase = supabaseAdmin()

  // Look up the product so we can optionally remove its storage object
  const { data: product, error: prodErr } = await supabase
    .from('products')
    .select('id,image_url')
    .eq('id', id)
    .single()

  if (prodErr) {
    // Not found or other DB error
    return NextResponse.json({ error: prodErr.message }, { status: 404 })
  }

  // If product had an image uploaded to the 'products' bucket, try removing it
  try {
    if (product?.image_url) {
      try {
        const url = new URL(product.image_url)
        // public URL path: /storage/v1/object/public/products/<path>
        const parts = url.pathname.split('/')
        const idx = parts.findIndex((p) => p === 'products')
        if (idx > -1) {
          const objectPath = parts.slice(idx + 1).join('/')
          // remove expects an array of paths
          await supabase.storage.from('products').remove([objectPath])
        }
      } catch (e) {
        // ignore errors parsing/removing the storage object
      }
    }
  } catch (e) {
    // noop
  }

  const { error } = await supabase.from('products').delete().eq('id', id)
  if (error) return NextResponse.json({ error: error.message }, { status: 400 })

  return NextResponse.json({ success: true })
}
