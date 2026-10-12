import { NextResponse } from 'next/server'
import { supabaseServer, supabaseAdmin } from '@/lib/supabase/server'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const limit = Number(searchParams.get('limit') ?? '12')
  const offset = Number(searchParams.get('offset') ?? '0')
  const search = searchParams.get('search')?.trim() ?? ''
  const category = searchParams.get('category')?.trim() ?? ''
  const sort = searchParams.get('sort') ?? 'featured'

  const supabase = await supabaseServer()
  let query = supabase
    .from('products')
    .select('id,name,price_cents,original_price_cents,image_url,category,is_new,is_sale,colors,sizes', { count: 'exact' })

  if (search) query = query.ilike('name', `%${search}%`)
  if (category && category.toLowerCase() !== 'all') query = query.ilike('category', category)

  if (sort === 'price-low') query = query.order('price_cents', { ascending: true, nullsFirst: true })
  else if (sort === 'price-high') query = query.order('price_cents', { ascending: false, nullsFirst: true })
  else if (sort === 'name') query = query.order('name', { ascending: true })
  else query = query.order('created_at', { ascending: false })

  query = query.range(offset, offset + limit - 1)

  const { data, error, count } = await query
  if (error) return NextResponse.json({ error: error.message }, { status: 400 })

  const items = (data ?? []).map((p, idx) => ({
    id: idx + 1, // local page index; client will merge and reassign
    dbId: p.id as string,
    name: p.name as string,
    price: Math.round(((p.price_cents as number) ?? 0) / 100),
    originalPrice: p.original_price_cents ? Math.round((p.original_price_cents as number) / 100) : undefined,
    category: (p.category as string) ?? 'General',
    image: (p.image_url as string) ?? '/placeholder.svg',
    colors: (p.colors as string[]) ?? [],
    sizes: (p.sizes as string[]) ?? [],
    isNew: Boolean(p.is_new),
    isSale: Boolean(p.is_sale),
  }))

  const total = count ?? 0
  const nextOffset = offset + items.length
  const hasMore = nextOffset < total
  return NextResponse.json({ items, total, nextOffset, hasMore })
}

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { name, description, price_cents, category, image_url, colors, sizes } = body

    // Validate required fields
    if (!name || !description || price_cents === undefined || !category) {
      return NextResponse.json(
        { error: 'Missing required fields: name, description, price_cents, category' },
        { status: 400 }
      )
    }

    // Use admin client to bypass RLS
    const supabase = supabaseAdmin()
    
    // Insert the new product (excluding brand field which doesn't exist in schema)
    const { data, error } = await supabase
      .from('products')
      .insert([
        {
          name,
          description,
          price_cents: parseInt(price_cents),
          category,
          image_url: image_url || null,
          colors: colors || [],
          sizes: sizes || [],
          is_new: true,
          is_sale: false
        }
      ])
      .select()
      .single()

    if (error) {
      console.error('Supabase insert error:', error)
      return NextResponse.json(
        { error: error.message || 'Failed to create product' },
        { status: 500 }
      )
    }

    return NextResponse.json({ success: true, product: data }, { status: 201 })
  } catch (error: any) {
    console.error('Error creating product:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
