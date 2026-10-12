import { NextResponse } from 'next/server'
import { supabaseServer } from '@/lib/supabase/server'

export async function GET() {
  const supabase = await supabaseServer()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data, error } = await supabase
    .from('cart_items')
    .select('id,quantity,product:product_id(id,name,price_cents,image_url)')
    .eq('cart_user_id', user.id)
    .order('created_at', { ascending: false })

  if (error) return NextResponse.json({ error: error.message }, { status: 400 })
  return NextResponse.json(data)
}

export async function POST(req: Request) {
  const supabase = await supabaseServer()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  let { productId, quantity = 1, product } = body as {
    productId?: string
    quantity?: number
    product?: { name: string; price?: number; price_cents?: number; image?: string; image_url?: string }
  }

  // Ensure cart exists
  const { error: cartErr } = await supabase
    .from('carts')
    .upsert({ user_id: user.id }, { onConflict: 'user_id' })
  if (cartErr) return NextResponse.json({ error: cartErr.message }, { status: 400 })

  // If productId not provided, try to upsert product by name
  if (!productId && product?.name) {
    const name = product.name
    const price_cents = typeof product.price_cents === 'number'
      ? product.price_cents
      : typeof product.price === 'number'
        ? Math.round(product.price * 100)
        : 0
    const image_url = product.image_url ?? product.image ?? null

    // Try find existing by name
    const { data: found, error: findErr } = await supabase
      .from('products')
      .select('id')
      .eq('name', name)
      .limit(1)
      .maybeSingle()
    if (findErr) return NextResponse.json({ error: findErr.message }, { status: 400 })

    if (found) {
      productId = found.id
    } else {
      const { data: inserted, error: insErr } = await supabase
        .from('products')
        .insert({ name, price_cents, image_url })
        .select('id')
        .single()
      if (insErr) return NextResponse.json({ error: insErr.message }, { status: 400 })
      productId = inserted.id
    }
  }

  if (!productId) return NextResponse.json({ error: 'Missing productId or product details' }, { status: 400 })

  // Upsert item
  const { data, error } = await supabase
    .from('cart_items')
    .upsert({ cart_user_id: user.id, product_id: productId, quantity }, { onConflict: 'cart_user_id,product_id' })
    .select('id,quantity')

  if (error) return NextResponse.json({ error: error.message }, { status: 400 })
  return NextResponse.json(data?.[0] ?? null, { status: 201 })
}
