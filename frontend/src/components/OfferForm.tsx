import { useMemo, useState } from "react";
import type { Listing } from "@lakasmarket/shared";
import { wouldBeRejected } from "@lakasmarket/shared";
import { api } from "../api/client";

interface Props {
  listing: Listing;
  onClose: () => void;
}

// Buyer-facing offer flow: passes the Product Knowledge Gateway quiz first,
// then collects the offer amount, Take Tonight and delivery options. The client
// warns before submitting an offer that the backend would silently reject.
export function OfferForm({ listing, onClose }: Props) {
  const questions = listing.knowledge_questions;
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [amount, setAmount] = useState<string>(listing.hard_floor_price.toFixed(2));
  const [isTakeTonight, setIsTakeTonight] = useState(false);
  const [wantDelivery, setWantDelivery] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const quizComplete = questions.every((q) => answers[q.id] !== undefined);

  // Local mirror of the backend floor check — purely a heads-up for the buyer.
  const willReject = useMemo(
    () =>
      wouldBeRejected(
        Number(listing.list_price),
        listing.floor_percent,
        Number(amount || 0),
        isTakeTonight,
        listing.sale_mode,
        listing.speed_discount_percent,
      ),
    [listing, amount, isTakeTonight],
  );

  function choose(questionId: number, optionIndex: number) {
    setAnswers((prev) => ({ ...prev, [questionId]: optionIndex }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const res = await api.makeOffer(listing.id, {
        amount: Number(amount),
        is_take_tonight: isTakeTonight,
        want_delivery: wantDelivery,
        quiz_answers: answers,
      });
      let msg = res.message;
      if (res.delivery_fee != null) {
        msg += ` Delivery fee: B$ ${Number(res.delivery_fee).toFixed(2)}.`;
      }
      setResult(msg);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit} style={{ background: "#fbfdfc" }}>
      <h4>Make an offer on “{listing.title}”</h4>

      {questions.length > 0 && (
        <div>
          <p className="warn" style={{ color: "#0b6b4f" }}>
            Answer these first — they confirm you read the description.
          </p>
          {questions.map((q) => (
            <fieldset key={q.id} style={{ border: 0, padding: 0, marginBottom: 8 }}>
              <legend style={{ fontWeight: 600, fontSize: 13 }}>{q.prompt}</legend>
              {q.options.map((opt, i) => (
                <label key={i} style={{ display: "block", fontWeight: 400 }}>
                  <input
                    type="radio"
                    name={`q-${q.id}`}
                    checked={answers[q.id] === i}
                    onChange={() => choose(q.id, i)}
                    style={{ width: "auto", marginRight: 6 }}
                  />
                  {opt}
                </label>
              ))}
            </fieldset>
          ))}
        </div>
      )}

      <label>Your offer (B$)</label>
      <input
        type="number"
        step="0.01"
        min="0"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
      />

      <label style={{ fontWeight: 400 }}>
        <input
          type="checkbox"
          checked={isTakeTonight}
          onChange={(e) => setIsTakeTonight(e.target.checked)}
          style={{ width: "auto", marginRight: 6 }}
        />
        I can take it tonight
      </label>
      <label style={{ fontWeight: 400 }}>
        <input
          type="checkbox"
          checked={wantDelivery}
          onChange={(e) => setWantDelivery(e.target.checked)}
          style={{ width: "auto", marginRight: 6 }}
          disabled={!listing.delivery_available}
        />
        Request delivery {listing.delivery_available ? "" : "(not offered)"}
      </label>

      {willReject && !result && (
        <div className="warn">
          Heads up: this offer is below the seller's floor and will be declined
          automatically. Consider raising it.
        </div>
      )}
      {error && <div className="warn">{error}</div>}
      {result && (
        <div className="warn" style={{ color: "#0b6b4f" }}>
          {result}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button disabled={busy || !quizComplete}>
          {busy ? "Sending…" : "Submit offer"}
        </button>
        <button type="button" className="secondary" onClick={onClose}>
          Cancel
        </button>
      </div>
      {!quizComplete && questions.length > 0 && (
        <div className="warn" style={{ color: "#8a6d1f" }}>
          Answer all questions to enable the offer.
        </div>
      )}
    </form>
  );
}
