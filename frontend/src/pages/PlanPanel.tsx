import { useEffect, useState } from "react";
import { SubscriptionTier } from "@lakasmarket/shared";
import { api, type Subscription } from "../api/client";

const TIERS: { tier: SubscriptionTier; name: string; blurb: string; price: string }[] = [
  { tier: SubscriptionTier.Basic, name: "Basic", blurb: "Up to 5 listings, standard 20% floor.", price: "Free" },
  { tier: SubscriptionTier.Pro, name: "Pro", blurb: "Unlimited listings, AI Specs Guard, analytics, negotiation bot.", price: "B$15 / mo" },
  { tier: SubscriptionTier.Business, name: "Business", blurb: "Bulk tools, Funds Verified escrow, priority support.", price: "B$49 / mo" },
];

export function PlanPanel() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reference, setReference] = useState("");

  async function refresh() {
    try {
      setSub(await api.getSubscription());
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function upgrade(tier: SubscriptionTier) {
    setBusy(true);
    setError(null);
    try {
      setSub(await api.upgrade(tier));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function markPaid() {
    setBusy(true);
    setError(null);
    try {
      setSub(await api.markBillingSent(reference || undefined));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const pending = sub?.pending_tier ?? null;

  return (
    <div className="container">
      <h2>Your plan</h2>
      {error && <div className="warn">{error}</div>}
      {sub && (
        <p>
          Current tier: <strong>{sub.tier}</strong>
          {" · "}
          {sub.listing_limit === null ? "Unlimited listings" : `${sub.listing_limit} listings`}
          {sub.has_specs_guard ? " · Specs Guard on" : ""}
        </p>
      )}

      {pending && (
        <div className="card" style={{ background: "#fbfdfc" }}>
          <h3>Upgrade to {pending} — B$ {sub!.amount_due.toFixed(2)} / mo</h3>
          {sub!.payment_status === "pending" ? (
            <p className="warn" style={{ color: "#b45309" }}>
              Payment marked as sent. Awaiting verification — your plan activates once an admin
              confirms the transfer.
            </p>
          ) : (
            <>
              <p>
                Transfer the amount to the platform account, then confirm below. An admin verifies
                receipt and activates your plan (manual "Funds Verified" billing — no card needed).
              </p>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  placeholder="Transfer reference (optional)"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  style={{ margin: 0 }}
                />
                <button disabled={busy} onClick={markPaid}>
                  I've sent payment
                </button>
              </div>
            </>
          )}
        </div>
      )}

      <div className="grid2">
        {TIERS.map((t) => {
          const current = sub?.tier === t.tier;
          const requested = pending === t.tier;
          return (
            <div className="card" key={t.tier}>
              <h3>{t.name}</h3>
              <div className="price">{t.price}</div>
              <p>{t.blurb}</p>
              <button
                disabled={busy || current || requested}
                className={current || requested ? "secondary" : undefined}
                onClick={() => upgrade(t.tier)}
              >
                {current
                  ? "Current plan"
                  : requested
                    ? "Requested — awaiting payment"
                    : t.tier === SubscriptionTier.Basic
                      ? "Downgrade to Basic"
                      : `Upgrade to ${t.name}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
