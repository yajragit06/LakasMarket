import { useCallback, useEffect, useState } from "react";
import type { Listing } from "@lakasmarket/shared";
import { District, SaleMode } from "@lakasmarket/shared";
import { api } from "../api/client";
import { ListingCard } from "../components/ListingCard";
import { BuyerOffers } from "../components/BuyerOffers";
import { CreateListing } from "./CreateListing";

export function Dashboard() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [district, setDistrict] = useState("");
  const [saleMode, setSaleMode] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setListings(
        await api.listListings({ q, district, sale_mode: saleMode, max_price: maxPrice }),
      );
    } catch (err) {
      setError((err as Error).message);
    }
  }, [q, district, saleMode, maxPrice]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="container">
      <BuyerOffers />
      <CreateListing onCreated={refresh} />

      <div className="card">
        <h3>Search & filter</h3>
        <input
          placeholder="Search title or description…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="grid2">
          <div>
            <label>District</label>
            <select value={district} onChange={(e) => setDistrict(e.target.value)}>
              <option value="">Any</option>
              {Object.values(District).map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Sale mode</label>
            <select value={saleMode} onChange={(e) => setSaleMode(e.target.value)}>
              <option value="">Any</option>
              <option value={SaleMode.Firm}>Firm</option>
              <option value={SaleMode.Fast}>Fast (Take Tonight)</option>
            </select>
          </div>
        </div>
        <label>Max price (B$)</label>
        <input
          type="number"
          min="0"
          value={maxPrice}
          onChange={(e) => setMaxPrice(e.target.value)}
        />
      </div>

      <h2>Active listings</h2>
      {error && <div className="warn">{error}</div>}
      {listings.length === 0 && <p>No listings match your filters.</p>}
      {listings.map((l) => (
        <ListingCard key={l.id} listing={l} />
      ))}
    </div>
  );
}
