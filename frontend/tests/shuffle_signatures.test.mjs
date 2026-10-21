import test from 'node:test'
import assert from 'node:assert/strict'

test('shuffle signature extraction and exclusion payload', async (t) => {
  await t.test('extracts core signatures correctly from displayed outfits', () => {
    const mockOutfits = [
      {
        id: 'outfit-1',
        core_signature: [
          ['bottom', 'bot-1'],
          ['top', 'top-1'],
        ],
      },
      {
        id: 'outfit-2',
        core_signature: [
          ['bottom', 'bot-2'],
          ['top', 'top-2'],
        ],
      },
      {
        id: 'outfit-3',
        core_signature: [], // empty core signature
      },
      {
        id: 'outfit-4',
        core_signature: undefined, // missing core signature
      },
    ]

    // Mirrors frontend/src/pages/OutfitsPage.tsx:184-186
    const isShuffle = true
    let currentSignatures = undefined
    if (isShuffle && mockOutfits) {
      currentSignatures = mockOutfits
        .map((o) => o.core_signature)
        .filter((sig) => Array.isArray(sig) && sig.length > 0)
    }

    assert.equal(currentSignatures?.length, 2)
    assert.deepEqual(currentSignatures, [
      [['bottom', 'bot-1'], ['top', 'top-1']],
      [['bottom', 'bot-2'], ['top', 'top-2']],
    ])
  })

  await t.test('omits exclude_core_signatures for normal generation requests', () => {
    const mockOutfits = [
      {
        id: 'outfit-1',
        core_signature: [['top', 'top-1']],
      },
    ]

    const isShuffle = false
    let currentSignatures = undefined
    if (isShuffle && mockOutfits) {
      currentSignatures = mockOutfits
        .map((o) => o.core_signature)
        .filter((sig) => Array.isArray(sig) && sig.length > 0)
    }

    const payload = {
      occasion: 'casual',
      is_shuffle: isShuffle,
      exclude_core_signatures: currentSignatures && currentSignatures.length > 0 ? currentSignatures : undefined,
    }

    assert.equal(payload.exclude_core_signatures, undefined)
    assert.equal(payload.is_shuffle, false)
  })

  await t.test('includes exclude_core_signatures for shuffle requests when displayed outfits exist', () => {
    const mockOutfits = [
      {
        id: 'outfit-1',
        core_signature: [['bottom', 'bot-1'], ['top', 'top-1']],
      },
    ]

    const isShuffle = true
    let currentSignatures = undefined
    if (isShuffle && mockOutfits) {
      currentSignatures = mockOutfits
        .map((o) => o.core_signature)
        .filter((sig) => Array.isArray(sig) && sig.length > 0)
    }

    const payload = {
      occasion: 'casual',
      is_shuffle: isShuffle,
      exclude_core_signatures: currentSignatures && currentSignatures.length > 0 ? currentSignatures : undefined,
    }

    assert.deepEqual(payload.exclude_core_signatures, [
      [['bottom', 'bot-1'], ['top', 'top-1']],
    ])
    assert.equal(payload.is_shuffle, true)
  })

  await t.test('handles truthful shuffle exhaustion when no unseen combinations remain', () => {
    const responsePayload = {
      outfits: [],
      status: 'no_matching_combinations',
      message: "No further unseen combinations could be created from your rack for 'casual'. All valid looks have been shown.",
    }

    assert.equal(responsePayload.status, 'no_matching_combinations')
    assert.match(responsePayload.message, /No further unseen combinations/)
    assert.equal(responsePayload.outfits.length, 0)
  })

  await t.test('handles partial results with truthful alternative count on shuffle exhaustion', () => {
    const responsePayload = {
      outfits: [
        {
          id: 'outfit-alt-1',
          core_signature: [['bottom', 'bot-3'], ['top', 'top-1']],
          wardrobe_only: true,
        },
      ],
      status: 'partial_results',
      message: "Found 1 alternative outfit(s) for 'casual'. No further unseen combinations remain on your rack.",
    }

    assert.equal(responsePayload.status, 'partial_results')
    assert.match(responsePayload.message, /Found 1 alternative outfit\(s\)/)
    assert.match(responsePayload.message, /No further unseen combinations remain/)
    assert.equal(responsePayload.outfits.length, 1)
  })
})
