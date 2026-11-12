const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ??
  "http://localhost:8000/api/v1";

export type ProcurementRequest = {
  id: string;
  status: string;
  original_prompt: string;
  structured_requirements: Record<string, unknown> | null;
  report: { recommended_product_id?: string; eligible_count?: number; mode?: string } | null;
};

export type ProcurementHistoryItem = Pick<
  ProcurementRequest,
  "id" | "status" | "original_prompt" | "report"
> & {
  created_at: string;
  updated_at: string;
  payment: PaymentHistoryPayment | null;
};

export type PaymentHistoryPayment = {
  status: string;
  amount: string | number;
  currency: string;
  paypal_capture_id: string | null;
};

export type ApiProduct = {
  id: string;
  name: string;
  brand: string | null;
  merchant: string | null;
  price: string | number;
  currency: string;
  specifications: Record<string, unknown>;
  source: string;
  product_url: string | null;
  image_url: string | null;
};

export type ApiEvaluation = {
  product_candidate_id: string;
  eligible: boolean;
  score: string | number | null;
  rejection_reasons: string[];
  explanation: string;
};

export type CheckoutOrder = {
  payment_id: string;
  paypal_order_id: string;
  approval_url: string;
  status: string;
  amount: string | number;
  currency: string;
};

export type Payment = {
  id: string;
  product_candidate_id: string;
  paypal_order_id: string;
  paypal_capture_id: string | null;
  status: string;
  amount: string | number;
  currency: string;
  quantity: number;
};

export type PaymentReceipt = {
  procurement_request_id: string;
  original_prompt: string;
  product_name: string;
  brand: string | null;
  merchant: string | null;
  quantity: number;
  amount: string | number;
  currency: string;
  payment_status: string;
  paypal_order_id: string;
  paypal_capture_id: string;
  issued_at: string;
  environment: string;
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Accept: "application/json", ...init?.headers },
    cache: "no-store",
    ...init,
  });
  if (!response.ok) throw new Error(`ARC API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export function createProcurementRequest(message: string) {
  return apiFetch<{ id: string; status: string }>("/requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export function submitClarification(id: string, message: string) {
  return apiFetch<{ id: string; status: string }>(`/requests/${id}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export function getProcurementRequest(id: string) {
  return apiFetch<ProcurementRequest>(`/requests/${id}`);
}

export function getProcurementHistory() {
  return apiFetch<ProcurementHistoryItem[]>("/requests");
}

export function getRequestProducts(id: string) {
  return apiFetch<ApiProduct[]>(`/requests/${id}/products`);
}

export function getRequestEvaluations(id: string) {
  return apiFetch<ApiEvaluation[]>(`/requests/${id}/evaluations`);
}

export function createCheckoutOrder(id: string, productCandidateId: string) {
  return apiFetch<CheckoutOrder>(`/requests/${id}/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_candidate_id: productCandidateId }),
  });
}

export function captureCheckoutOrder(id: string, paypalOrderId: string) {
  return apiFetch<Payment>(`/requests/${id}/checkout/${paypalOrderId}/capture`, {
    method: "POST",
  });
}

export function getRequestPayment(id: string) {
  return apiFetch<Payment | null>(`/requests/${id}/payment`);
}

export function getPaymentReceipt(id: string) {
  return apiFetch<PaymentReceipt>(`/requests/${id}/receipt`);
}

export function workflowEventsUrl(id: string) {
  return `${apiBaseUrl}/requests/${id}/events`;
}
