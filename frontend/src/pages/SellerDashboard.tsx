import { useEffect, useState } from "react";
import type { Listing, SellerAnalytics } from "@lakasmarket/shared";
import { api, type Offer } from "../api/client";

// Seller's view of their own listings and the offers on them. Auto-rejected
// lowballs never arrive here — the backend hides them to protect sentiment.
export function SellerDashboard() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<SellerAnalytics | null>(null);
  const [statsNote, setStatsNote] = useState<string | null>(null);

  async function refresh() {
    try {
      setListings(await api.myListings());
    } catch (err) {
      setError((err as Error).message);
    }
    try {
      setStats(await api.sellerAnalytics());
      setStatsNote(null);
    } catch (err) {
      // Basic tier gets a 402 upsell instead of numbers.
      setStats(null);
      setStatsNote((err as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="container">
      <h2>My listings</h2>
      {stats ? (
        <div className="card" style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <Stat label="🛡️ Lowballs blocked" value={stats.lowballs_blocked} />
          <Stat label="Pending offers" value={stats.pending_offers} />
          <Stat label="Sold" value={stats.sold_listings} />
          <Stat
            label="Avg offer vs list"
            value={
              stats.avg_offer_percent_of_list === null
                ? "—"
                : `${stats.avg_offer_percent_of_list}%`
            }
          />
          <Stat label="✓ Funds Verified deals" value={stats.funds_verified_deals} />
          <Stat label="Expired 'tonight' offers" value={stats.expired_take_tonight_offers} />
        </div>
      ) : (
        statsNote && (
          <div className="card" style={{ color: "#4a5568" }}>
            {statsNote}
          </div>
        )
      )}
      {error && <div className="warn">{error}</div>}
      {listings.length === 0 && <p>You have no listings yet.</p>}
      {listings.map((l) => (
        <SellerListingRow key={l.id} listing={l} />
      ))}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#4a5568" }}>{label}</div>
    </div>
  );
}

function PaymentBadge({ status }: { status: string }) {
  if (status === "none") return <span style={{ color: "#94a3b8" }}>—</span>;
  const map: Record<string, [string, string]> = {
    pending: ["#b45309", "Funds sent — verify"],
    verified: ["#0b6b4f", "✓ Funds Verified"],
    released: ["#0b6b4f", "✓ Released"],
    refunded: ["#94a3b8", "Refunded"],
  };
  const [color, label] = map[status] ?? ["#1a1a1a", status];
  return <span style={{ color, fontWeight: 600, fontSize: 13 }}>{label}</span>;
}

function SellerListingRow({ listing }: { listing: Listing }) {
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadOffers() {
    setError(null);
    try {
      setOffers(await api.offersForListing(listing.id));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function act(offerId: number, action: "accept" | "decline" | "complete" | "report-ghost") {
    setBusy(true);
    setError(null);
    try {
      await api.offerAction(offerId, action);
      await loadOffers();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyFunds(offerId: number) {
    setBusy(true);
    setError(null);
    try {
      await api.verifyPayment(offerId);
      await loadOffers();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>{listing.title}</h3>
      <div>
        <span className="badge">{listing.status}</span>
        <span className="badge">B$ {Number(listing.list_price).toFixed(2)}</span>
      </div>
      <div className="floor">
        Floor B$ {listing.hard_floor_price.toFixed(2)} — offers below are auto-declined & hidden.
      </div>

      {offers === null ? (
        <button className="secondary" style={{ marginTop: 8 }} onClick={loadOffers}>
          View offers
        </button>
      ) : offers.length === 0 ? (
        <p>No offers to review. (Lowballs never reach you.)</p>
      ) : (
        <table style={{ width: "100%", marginTop: 8, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", fontSize: 13 }}>
              <th>Amount</th>
              <th>Speed</th>
              <th>Status</th>
              <th>Payment</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {offers.map((o) => (
              <tr key={o.id} style={{ borderTop: "1px solid #eee", fontSize: 14 }}>
                <td>B$ {Number(o.amount).toFixed(2)}</td>
                <td>{o.is_take_tonight ? "Tonight" : "—"}</td>
                <td>{o.status}</td>
                <td><PaymentBadge status={o.payment_status} /></td>
                <td style={{ display: "flex", gap: 6, padding: "6px 0" }}>
                  {o.payment_status === "pending" && (
                    <button disabled={busy} onClick={() => verifyFunds(o.id)}>
                      Verify funds
                    </button>
                  )}
                  {o.status === "pending" && (
                    <>
                      <button disabled={busy} onClick={() => act(o.id, "accept")}>
                        Accept
                      </button>
                      <button
                        disabled={busy}
                        className="secondary"
                        onClick={() => act(o.id, "decline")}
                      >
                        Decline
                      </button>
                    </>
                  )}
                  {o.status === "accepted" && (
                    <>
                      <button disabled={busy} onClick={() => act(o.id, "complete")}>
                        Mark sold
                      </button>
                      <button
                        disabled={busy}
                        className="secondary"
                        onClick={() => act(o.id, "report-ghost")}
                      >
                        Report ghosting
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {error && <div className="warn">{error}</div>}
    </div>
  );
}
