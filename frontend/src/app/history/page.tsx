"use client";

import Link from "next/link";
import { ArrowLeft, Check, Clock3, FileClock, LoaderCircle, ReceiptText, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";
import {
  getPaymentReceipt,
  getProcurementHistory,
  type PaymentReceipt,
  type ProcurementHistoryItem,
} from "@/lib/api/requests";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export default function HistoryPage() {
  const [requests, setRequests] = useState<ProcurementHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [receipt, setReceipt] = useState<PaymentReceipt | null>(null);
  const [isLoadingReceipt, setIsLoadingReceipt] = useState(false);
  const [receiptError, setReceiptError] = useState<string | null>(null);

  async function openReceipt(requestId: string) {
    setIsLoadingReceipt(true);
    setReceiptError(null);
    try {
      setReceipt(await getPaymentReceipt(requestId));
    } catch {
      setReceiptError("ARC could not load this payment receipt.");
    } finally {
      setIsLoadingReceipt(false);
    }
  }

  useEffect(() => {
    void getProcurementHistory()
      .then(setRequests)
      .catch(() => setHasError(true))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <main className="history-page">
      <Link className="back-link" href="/">
        <ArrowLeft size={16} aria-hidden="true" />
        Back to workspace
      </Link>
      <div className="history-card history-card-wide glass-surface">
        <div className="history-icon">
          <FileClock size={23} strokeWidth={1.7} aria-hidden="true" />
        </div>
        <p className="eyebrow">PROCUREMENT HISTORY</p>
        <h1>Procurement history</h1>
        <p className="history-description">Every request is saved locally. Completed Sandbox payments include a persisted ARC receipt.</p>
        {isLoading && <div className="history-note"><LoaderCircle size={15} className="status-spinner" /><span>Loading saved requests</span></div>}
        {hasError && <div className="history-note"><span>History could not connect to the ARC API.</span></div>}
        {!isLoading && !hasError && !requests.length && <div className="history-note"><Clock3 size={15} /><span>No procurement requests yet</span></div>}
        <div className="history-list">
          {requests.map((request) => (
            <div className="history-row" key={request.id}>
              <Link className="history-row-main" href={`/?requestId=${request.id}`}>
                <span className="history-row-copy"><strong>{request.original_prompt}</strong><small>{new Date(request.updated_at).toLocaleString()} · {request.status.replaceAll("_", " ")}</small></span>
                <span className="history-open">Open</span>
              </Link>
              {request.payment?.status === "COMPLETED" && request.payment.paypal_capture_id && (
                <button className="receipt-button" type="button" onClick={() => void openReceipt(request.id)} disabled={isLoadingReceipt}>
                  <ReceiptText size={14} aria-hidden="true" /> View receipt
                </button>
              )}
            </div>
          ))}
        </div>
        <Link className="primary-button history-button" href="/">Return to workspace</Link>
      </div>
      {(receipt || receiptError) && <div className="modal-backdrop" onMouseDown={(event) => {
        if (event.target === event.currentTarget) { setReceipt(null); setReceiptError(null); }
      }}>
        <section className="receipt-modal glass-surface" role="dialog" aria-modal="true" aria-labelledby="receipt-title">
          <button className="modal-close icon-button" type="button" onClick={() => { setReceipt(null); setReceiptError(null); }} aria-label="Close receipt"><X size={18} aria-hidden="true" /></button>
          {receiptError ? <p className="receipt-error">{receiptError}</p> : receipt && <>
            <div className="receipt-heading-icon"><ReceiptText size={21} aria-hidden="true" /></div>
            <p className="eyebrow">PAYMENT RECEIPT</p>
            <h2 id="receipt-title">Sandbox payment confirmed</h2>
            <p className="receipt-issued">Issued {new Date(receipt.issued_at).toLocaleString()}</p>
            <div className="receipt-summary">
              <div className="receipt-product"><strong>{receipt.product_name}</strong><span>Quantity {receipt.quantity}{receipt.brand ? ` · ${receipt.brand}` : ""}{receipt.merchant ? ` · ${receipt.merchant}` : ""}</span></div>
              <div className="receipt-total"><span>Total paid</span><strong>{currency.format(Number(receipt.amount))} {receipt.currency}</strong></div>
              <div className="receipt-detail"><span>PayPal order ID</span><code>{receipt.paypal_order_id}</code></div>
              <div className="receipt-detail"><span>PayPal capture ID</span><code>{receipt.paypal_capture_id}</code></div>
            </div>
            <div className="receipt-confirmed"><Check size={15} aria-hidden="true" /><span>Captured successfully in {receipt.environment}</span></div>
            <p className="receipt-footnote"><ShieldCheck size={13} aria-hidden="true" /> This is a test receipt. No real money moved.</p>
          </>}
        </section>
      </div>}
    </main>
  );
}
