// Client-side mirror of the Anti-Lowball floor logic. Lets the UI warn a buyer
// *before* they submit an insulting offer, while the backend remains the source
// of truth. Kept intentionally in sync with backend/app/core/anti_lowball.py.
import { SaleMode } from "./types";

export function hardFloorPrice(listPrice: number, floorPercent: number): number {
  return round2(listPrice * (1 - floorPercent / 100));
}

export function speedFloor(
  listPrice: number,
  saleMode: SaleMode,
  speedDiscountPercent: number,
): number {
  if (saleMode === SaleMode.Fast) {
    return round2(listPrice * (1 - speedDiscountPercent / 100));
  }
  return listPrice;
}

/** Returns true if an offer would be silently auto-rejected by the backend. */
export function wouldBeRejected(
  listPrice: number,
  floorPercent: number,
  amount: number,
  isTakeTonight: boolean,
  saleMode: SaleMode,
  speedDiscountPercent: number,
): boolean {
  const floor = hardFloorPrice(listPrice, floorPercent);
  if (amount < floor) return true;
  if (isTakeTonight) {
    const effective = Math.max(floor, speedFloor(listPrice, saleMode, speedDiscountPercent));
    return amount < effective;
  }
  return false;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
