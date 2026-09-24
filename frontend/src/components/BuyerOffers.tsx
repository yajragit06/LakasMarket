import { useEffect, useState } from "react";
import type { Offer } from "@lakasmarket/shared";
import { api } from "../api/client";

// The buyer's own offers, with the manual escrow action: once a deal is
// accepted, mark funds sent so the seller can verify ("Funds Verified").
export function BuyerOffers() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [refInput, setRefInput] = useState<Record<number, string>>({});

  async function load() {
    try {
      setOffers(await api.myOffers());
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function markSent(offerId: number) {
    setBusyId(offerId);
    setError(null);
    try {
      await api.markPaymentSent(offerId, refInput[offerId] || undefined);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  const active = offers.filter((o) => o.status === "accepted" || o.payment_status !== "none");
  if (active.length === 0) return null;

  return (
    <div className="card">
      <h3>Your deals</h3>
      {error && <div className="warn">{error}</div>}
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ textAlign: "left", fontSize: 13 }}>
            <th>Amount</th>
            <th>Deal</th>
            <th>Payment</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {active.map((o) => (
            <tr key={o.id} style={{ borderTop: "1px solid #eee" }}>
              <td>B$ {Number(o.amount).toFixed(2)}</td>
              <td>{o.status}</td>
              <td>{paymentLabel(o.payment_status)}</td>
              <td>
                {o.status === "accepted" && o.payment_status === "none" ? (
                  <div style={{ display: "flex", gap: 6 }}>
                    <input
                      placeholder="Transfer ref (optional)"
                      value={refInput[o.id] ?? ""}
                      onChange={(e) => setRefInput((p) => ({ ...p, [o.id]: e.target.value }))}
                      style={{ margin: 0, fontSize: 13 }}
                    />
                    <button disabled={busyId === o.id} onClick={() => markSent(o.id)}>
                      I've sent funds
                    </button>
                  </div>
                ) : o.payment_status === "pending" ? (
                  <span style={{ color: "#b45309" }}>Awaiting seller verification…</span>
                ) : (
                  <span style={{ color: "#94a3b8" }}>—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function paymentLabel(status: string): string {
  return (
    {
      none: "—",
      pending: "Funds sent",
      verified: "✓ Verified",
      released: "✓ Released",
      refunded: "Refunded",
    }[status] ?? status
  );
}
