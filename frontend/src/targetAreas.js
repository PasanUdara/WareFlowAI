/**
 * Centralized Target Areas Registry for WareFlow AI Digital Twin
 * Provides exact grid coordinates, friendly names, descriptions, and categories.
 */

export const TARGET_GROUPS = [
  {
    category: 'Packing Stations',
    icon: 'Package',
    items: [
      { id: 'packing-1', name: 'Packing Station 1', x: 15, y: 12, category: 'Packing Station', description: 'Outbound sorting & conveyor 1' },
      { id: 'packing-2', name: 'Packing Station 2', x: 16, y: 12, category: 'Packing Station', description: 'Outbound packaging & conveyor 2' },
      { id: 'packing-3', name: 'Packing Station 3', x: 17, y: 12, category: 'Packing Station', description: 'Main outbound dispatch conveyor 3' },
    ]
  },
  {
    category: 'Storage Shelves (Aisle A)',
    icon: 'Layers',
    items: [
      { id: 'shelf-a1', name: 'Shelf A1', x: 3, y: 3, category: 'Shelf', description: 'Storage bay A1 — Priority inventory' },
      { id: 'shelf-a2', name: 'Shelf A2', x: 3, y: 4, category: 'Shelf', description: 'Storage bay A2 — Standard pallet racking' },
      { id: 'shelf-a3', name: 'Shelf A3', x: 3, y: 5, category: 'Shelf', description: 'Storage bay A3 — Medical & pharma goods' },
    ]
  },
  {
    category: 'Storage Shelves (Aisle B)',
    icon: 'Layers',
    items: [
      { id: 'shelf-b1', name: 'Shelf B1', x: 6, y: 3, category: 'Shelf', description: 'Storage bay B1 — Heavy equipment & motors' },
      { id: 'shelf-b2', name: 'Shelf B2', x: 6, y: 4, category: 'Shelf', description: 'Storage bay B2 — Industrial parts & tools' },
      { id: 'shelf-b3', name: 'Shelf B3', x: 6, y: 5, category: 'Shelf', description: 'Storage bay B3 — Bulk packaging inventory' },
    ]
  },
  {
    category: 'Storage Shelves (Aisles C & D)',
    icon: 'Layers',
    items: [
      { id: 'shelf-c1', name: 'Shelf C1', x: 10, y: 3, category: 'Shelf', description: 'Storage bay C1 — Electronics & sensors' },
      { id: 'shelf-c2', name: 'Shelf C2', x: 10, y: 4, category: 'Shelf', description: 'Storage bay C2 — High-value components' },
      { id: 'shelf-d1', name: 'Shelf D1', x: 14, y: 3, category: 'Shelf', description: 'Storage bay D1 — Consumer boxed goods' },
      { id: 'shelf-d2', name: 'Shelf D2', x: 14, y: 4, category: 'Shelf', description: 'Storage bay D2 — Fast-moving retail items' },
    ]
  },
  {
    category: 'Receiving Dock',
    icon: 'Truck',
    items: [
      { id: 'receiving-1', name: 'Receiving Dock 1', x: 1, y: 1, category: 'Receiving Dock', description: 'Inbound freight intake bay 1' },
      { id: 'receiving-2', name: 'Receiving Dock 2', x: 2, y: 1, category: 'Receiving Dock', description: 'Inbound freight intake bay 2' },
      { id: 'receiving-3', name: 'Receiving Dock 3', x: 3, y: 1, category: 'Receiving Dock', description: 'Inbound freight intake bay 3' },
    ]
  },
  {
    category: 'Charging Bay',
    icon: 'Zap',
    items: [
      { id: 'charge-1', name: 'Charging Bay - Pad 1', x: 1, y: 13, category: 'Charging Bay', description: 'AMR high-speed induction pad 1' },
      { id: 'charge-2', name: 'Charging Bay - Pad 2', x: 2, y: 13, category: 'Charging Bay', description: 'AMR high-speed induction pad 2' },
      { id: 'charge-3', name: 'Charging Bay - Pad 3', x: 3, y: 13, category: 'Charging Bay', description: 'AMR high-speed induction pad 3' },
      { id: 'charge-4', name: 'Charging Bay - Pad 4', x: 4, y: 13, category: 'Charging Bay', description: 'AMR high-speed induction pad 4' },
    ]
  },
  {
    category: 'Hazardous & Restricted Zones',
    icon: 'AlertTriangle',
    items: [
      { id: 'hazmat-4', name: 'Hazmat Aisle 4', x: 11, y: 5, category: 'Hazmat', description: 'Chemical & flammable solvent storage' },
      { id: 'restricted-center', name: 'Restricted Zone', x: 9, y: 12, category: 'Restricted Zone', description: 'NO ENTRY — Forbidden to AMR fleet' },
    ]
  }
];

export const ALL_TARGET_AREAS = TARGET_GROUPS.flatMap((group) => group.items);

export const TARGET_LOOKUP_BY_KEY = new Map();
ALL_TARGET_AREAS.forEach((item) => {
  TARGET_LOOKUP_BY_KEY.set(`${item.x}:${item.y}`, item);
  TARGET_LOOKUP_BY_KEY.set(item.name.toLowerCase(), item);
  TARGET_LOOKUP_BY_KEY.set(item.id.toLowerCase(), item);
});

/**
 * Returns detailed landmark & zoning information for any hovered (x, y) coordinate.
 */
export function getGridCellDetails(x, y) {
  const nx = Number(x);
  const ny = Number(y);
  const exact = TARGET_LOOKUP_BY_KEY.get(`${nx}:${ny}`);

  if (exact) {
    return {
      title: exact.name,
      category: exact.category,
      description: exact.description,
      isTarget: true,
      targetId: exact.id,
      x: nx,
      y: ny
    };
  }

  // Packing Station zone (x: 14..19, y: 11..14)
  if (ny >= 11 && ny <= 14 && nx >= 14 && nx <= 19) {
    return {
      title: 'Packing Station Area',
      category: 'Workstation / Conveyor Zone',
      description: 'Outbound packaging and palletizing floor',
      isTarget: false,
      x: nx,
      y: ny
    };
  }

  // Charging Bay zone (x: 0..5, y: 11..14)
  if (ny >= 11 && ny <= 14 && nx <= 5) {
    return {
      title: 'Charging Bay Zone',
      category: 'Fleet Power Infrastructure',
      description: 'Automated AMR wireless charging area',
      isTarget: false,
      x: nx,
      y: ny
    };
  }

  // Restricted Zone (x: 7..12, y: 11..14)
  if (ny >= 11 && ny <= 14 && nx >= 7 && nx <= 12) {
    return {
      title: 'Restricted Zone (No Entry)',
      category: 'Hazard Zone',
      description: 'Human-only or hazardous maintenance zone',
      isHazard: true,
      x: nx,
      y: ny
    };
  }

  // Receiving Dock (x: 0..4, y: 0..2)
  if (ny <= 2 && nx <= 4) {
    return {
      title: 'Receiving Dock Staging',
      category: 'Inbound Freight Zone',
      description: 'Unloading doors and intake inspection floor',
      isTarget: false,
      x: nx,
      y: ny
    };
  }

  // Shelving Racks (x in [4, 5, 8, 9, 12, 13, 16, 17], y in 3..9)
  if ([4, 5].includes(nx) && ny >= 3 && ny <= 9) {
    return { title: `Shelf Rack A (Tier ${ny - 2})`, category: 'Static Storage Rack', isShelf: true, x: nx, y: ny };
  }
  if ([8, 9].includes(nx) && ny >= 3 && ny <= 9) {
    return { title: `Shelf Rack B (Tier ${ny - 2})`, category: 'Static Storage Rack', isShelf: true, x: nx, y: ny };
  }
  if ([12, 13].includes(nx) && ny >= 3 && ny <= 9) {
    return { title: `Shelf Rack C (Tier ${ny - 2})`, category: 'Static Storage Rack', isShelf: true, x: nx, y: ny };
  }
  if ([16, 17].includes(nx) && ny >= 3 && ny <= 9) {
    return { title: `Shelf Rack D (Tier ${ny - 2})`, category: 'Static Storage Rack', isShelf: true, x: nx, y: ny };
  }

  // Vertical Transit Aisles
  if (nx === 6 && ny >= 3 && ny <= 9) return { title: 'Aisle A Transit Lane', category: 'Aisle (Southbound)', x: nx, y: ny };
  if (nx === 9 && ny >= 3 && ny <= 9) return { title: 'Aisle B Transit Lane', category: 'Aisle (Northbound)', x: nx, y: ny };
  if (nx === 12 && ny >= 3 && ny <= 9) return { title: 'Aisle C Transit Lane', category: 'Aisle (Southbound)', x: nx, y: ny };
  if (nx === 15 && ny >= 3 && ny <= 9) return { title: 'Aisle D Transit Lane', category: 'Aisle (Northbound)', x: nx, y: ny };

  // Main Horizontal Corridors
  if (ny === 2) return { title: 'North Transit Corridor', category: 'High-Speed Transit', x: nx, y: ny };
  if (ny === 10) return { title: 'South Transit Corridor', category: 'Main East-West Bypass Road', x: nx, y: ny };

  return {
    title: 'Transit Aisle',
    category: 'Walkable Floor',
    description: 'Clear navigation path',
    x: nx,
    y: ny
  };
}

/**
 * Resolves a natural-language location string (e.g. 'Shelf A2', 'Packing Station 3')
 * to standard grid coordinates and canonical display names.
 */
export function resolveTargetLocation(name) {
  if (!name || typeof name !== 'string') return null;
  const clean = name.trim().toLowerCase().replace(/[,.]/g, '');
  const direct = TARGET_LOOKUP_BY_KEY.get(clean);
  if (direct) {
    return { x: direct.x, y: direct.y, name: direct.name, id: direct.id, category: direct.category };
  }

  // Common keywords & abbreviations
  if (clean.includes('shelf') && clean.includes('a1')) return { x: 3, y: 3, name: 'Shelf A1', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('a2')) return { x: 3, y: 4, name: 'Shelf A2', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('a3')) return { x: 3, y: 5, name: 'Shelf A3', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('b1')) return { x: 6, y: 3, name: 'Shelf B1', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('b2')) return { x: 6, y: 4, name: 'Shelf B2', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('b3')) return { x: 6, y: 5, name: 'Shelf B3', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('c1')) return { x: 10, y: 3, name: 'Shelf C1', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('c2')) return { x: 10, y: 4, name: 'Shelf C2', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('d1')) return { x: 14, y: 3, name: 'Shelf D1', category: 'Shelf' };
  if (clean.includes('shelf') && clean.includes('d2')) return { x: 14, y: 4, name: 'Shelf D2', category: 'Shelf' };
  if (clean.includes('station') && clean.includes('1')) return { x: 15, y: 12, name: 'Packing Station 1', category: 'Packing Station' };
  if (clean.includes('station') && clean.includes('2')) return { x: 16, y: 12, name: 'Packing Station 2', category: 'Packing Station' };
  if (clean.includes('station') && clean.includes('3')) return { x: 17, y: 12, name: 'Packing Station 3', category: 'Packing Station' };
  if (clean.includes('packing')) return { x: 17, y: 12, name: 'Packing Station 3', category: 'Packing Station' };
  if (clean.includes('dock') || clean.includes('receiving')) return { x: 2, y: 1, name: 'Receiving Dock 2', category: 'Receiving Dock' };
  if (clean.includes('charge') || clean.includes('charging') || clean.includes('bay')) return { x: 2, y: 13, name: 'Charging Bay - Pad 2', category: 'Charging Bay' };
  if (clean.includes('hazmat')) return { x: 11, y: 5, name: 'Hazmat Aisle 4', category: 'Hazmat' };

  return null;
}

