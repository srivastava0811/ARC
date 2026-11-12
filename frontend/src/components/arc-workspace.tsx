"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  Activity,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Cpu,
  FileClock,
  Info,
  Keyboard,
  LockKeyhole,
  LoaderCircle,
  Monitor,
  Mouse,
  Moon,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { checkApiHealth, type ApiAvailability } from "@/lib/api/health";
import {
  createProcurementRequest,
  captureCheckoutOrder,
  createCheckoutOrder,
  getProcurementHistory,
  getProcurementRequest,
  getRequestPayment,
  getRequestEvaluations,
  getRequestProducts,
  submitClarification,
  type ApiEvaluation,
  type ApiProduct,
  type Payment,
  type ProcurementHistoryItem,
  workflowEventsUrl,
} from "@/lib/api/requests";

type Product = {
  id: string;
  name: string;
  category: string;
  detail: string;
  price: number;
  eligible: boolean;
  priceNeedsVerification: boolean;
  badge?: string;
  imageClass: string;
  specs: string[];
  pros: string[];
  cons: string[];
  warranty: string;
  source: string;
  imageUrl?: string;
  productUrl?: string;
};

type WorkflowEvent = {
  sequence: number;
  type: string;
  payload: Record<string, unknown>;
};

const activityCopy: Record<string, string> = {
  "workflow.started": "Workflow started",
  "agent.started": "Agent started",
  "agent.completed": "Agent completed",
  "agent.degraded": "Provider temporarily unavailable · deterministic result retained",
  "research.products_found": "Catalog research completed",
  "approval.required": "Selection ready for approval",
  "planner.clarification_required": "Clarification required",
  "workflow.completed": "Workflow completed",
  "workflow.failed": "Workflow failed",
  "payment.order_created": "PayPal Sandbox order ready",
  "payment.completed": "PayPal Sandbox payment completed",
  "payment.capture_failed": "PayPal Sandbox capture failed",
};

function titleCase(value: string) {
  return value.replaceAll(/[._-]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const paymentCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const workflowStages = [
  { status: "PLANNING", label: "Understand your request" },
  { status: "RESEARCHING", label: "Search live offers" },
  { status: "EVALUATING", label: "Compare eligible options" },
  { status: "GENERATING_REPORT", label: "Prepare recommendations" },
];

const processingCopy: Record<string, { title: string; detail: string }> = {
  CREATED: {
    title: "Preparing your request",
    detail: "ARC is starting a secure procurement workflow.",
  },
  PLANNING: {
    title: "Understanding what you need",
    detail: "ARC is extracting the budget, quantity, and product requirements.",
  },
  RESEARCHING: {
    title: "Searching live offers",
    detail: "ARC is checking the catalog for products that match your request.",
  },
  EVALUATING: {
    title: "Comparing the best fits",
    detail: "ARC is applying your requirements to the offers it found.",
  },
  GENERATING_REPORT: {
    title: "Preparing your recommendations",
    detail: "ARC is saving the ranked options for your review.",
  },
};

type PaymentReturn = { requestId: string; orderId: string };

function ProductPlaceholder({ category }: { category: string }) {
  if (category === "computer_keyboard") return <Keyboard size={36} aria-hidden="true" />;
  if (category === "computer_mouse") return <Mouse size={36} aria-hidden="true" />;
  return <><div className="monitor-screen"><span /><i /></div><div className="monitor-stand" /></>;
}

export function ArcWorkspace({ initialPaymentReturn }: { initialPaymentReturn?: PaymentReturn } = {}) {
  const [paymentReturnState, setPaymentReturnState] = useState<"confirming" | "loading" | "error" | null>(initialPaymentReturn ? "confirming" : null);
  const [paymentWasConfirmed, setPaymentWasConfirmed] = useState(false);
  const initialRequestLoaded = useRef(false);
  const [selectedProductId, setSelectedProductId] = useState("studio-27");
  const [products, setProducts] = useState<Product[]>([]);
  const [requestQuantity, setRequestQuantity] = useState(1);
  const [requestCategory, setRequestCategory] = useState("computer_monitor");
  const categoryLabel = ({ computer_monitor: "monitors", computer_keyboard: "keyboards", computer_mouse: "mice" } as Record<string, string>)[requestCategory] ?? "products";
  const [requestText, setRequestText] = useState("");
  const [submittedText, setSubmittedText] = useState("");
  const [workflowStatus, setWorkflowStatus] = useState<string | null>(null);
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);
  const [submittedRequestId, setSubmittedRequestId] = useState<string | null>(null);
  const [resultsReadyForId, setResultsReadyForId] = useState<string | null>(null);
  const [revealedRequestId, setRevealedRequestId] = useState<string | null>(null);
  const [workflowEvents, setWorkflowEvents] = useState<WorkflowEvent[]>([]);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [clarificationNeeds, setClarificationNeeds] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showApproval, setShowApproval] = useState(false);
  const [isStartingCheckout, setIsStartingCheckout] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState<string | null>(null);
  const [completedPayment, setCompletedPayment] = useState<Payment | null>(null);
  const [recentRequests, setRecentRequests] = useState<ProcurementHistoryItem[]>([]);
  const { theme, toggleTheme } = useTheme();
  const [apiAvailability, setApiAvailability] = useState<ApiAvailability>("checking");
  const selectedProduct =
    products.find((product) => product.id === selectedProductId && product.eligible) ??
    products.find((product) => product.eligible);
  const orderIsComplete =
    workflowStatus === "COMPLETED" && completedPayment?.status === "COMPLETED";
  const noEligibleMatches = workflowStatus === "COMPLETED" && !orderIsComplete &&
    resultsReadyForId === activeRequestId && !selectedProduct;
  const orderedProduct =
    products.find((product) => product.id === completedPayment?.product_candidate_id) ??
    selectedProduct;
  const hasLiveCatalogResults = products.some((product) =>
    product.source.startsWith("Channel3"),
  );
  const isProcessing = Boolean(
    workflowStatus &&
      !["AWAITING_APPROVAL", "NEEDS_CLARIFICATION", "COMPLETED", "FAILED"].includes(
        workflowStatus,
      ),
  );
  const showCompletedSteps = Boolean(
    !workflowError && activeRequestId &&
      activeRequestId === submittedRequestId &&
      revealedRequestId !== activeRequestId &&
      ["AWAITING_APPROVAL", "COMPLETED"].includes(workflowStatus ?? ""),
  );
  const displayedProducts = showCompletedSteps ? [] : products;
  const showProgress = isProcessing || showCompletedSteps;
  const currentStageIndex = workflowStages.findIndex(
    (stage) => stage.status === workflowStatus,
  );
  const currentProcessingCopy = showCompletedSteps
    ? { title: "All four steps complete", detail: "Your recommendations are ready to review." }
    : processingCopy[workflowStatus ?? ""] ?? processingCopy.CREATED;
  const statusTone = workflowError
    ? "error"
    : workflowStatus === "FAILED"
      ? "error"
    : workflowStatus === "NEEDS_CLARIFICATION" || noEligibleMatches
      ? "clarification"
      : orderIsComplete
        ? "approval"
      : workflowStatus === "AWAITING_APPROVAL"
        ? "approval"
        : isProcessing
          ? "processing"
          : "idle";
  const statusLabel = workflowError
    ? "Request could not be completed"
    : orderIsComplete
      ? "Order complete"
    : noEligibleMatches
      ? "No eligible matches"
    : workflowStatus === "NEEDS_CLARIFICATION"
      ? "More information needed"
      : workflowStatus === "AWAITING_APPROVAL"
        ? "Recommendations ready"
        : workflowStatus
          ? workflowStatus.replaceAll("_", " ")
          : "Ready for a request";

  useEffect(() => {
    if (!showCompletedSteps || resultsReadyForId !== activeRequestId) return;
    // Let the completed checklist paint before revealing newly fetched results.
    // Saved requests skip this pause; reset/navigation cancels the pending reveal.
    const timer = window.setTimeout(() => setRevealedRequestId(activeRequestId), 800);
    return () => window.clearTimeout(timer);
  }, [showCompletedSteps, resultsReadyForId, activeRequestId]);

  useEffect(() => {
    let activeController: AbortController | undefined;
    let isMounted = true;

    async function refreshHealth() {
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      try {
        const status = await checkApiHealth(controller.signal);
        if (isMounted) setApiAvailability(status);
      } catch {
        if (isMounted && !controller.signal.aborted) {
          setApiAvailability("unavailable");
        }
      }
    }

    void refreshHealth();
    const intervalId = window.setInterval(() => void refreshHealth(), 15_000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
      activeController?.abort();
    };
  }, []);

  useEffect(() => {
    void getProcurementHistory().then(setRecentRequests).catch(() => setRecentRequests([]));
  }, []);

  useEffect(() => {
    if (!activeRequestId) return;
    const stream = new EventSource(workflowEventsUrl(activeRequestId));
    const eventTypes = [
      "workflow.started", "agent.started", "agent.completed", "planner.clarification_required",
      "research.products_found", "approval.required", "workflow.completed",
      "workflow.failed", "agent.degraded", "payment.order_created", "payment.completed", "payment.capture_failed",
    ];
    const onEvent = (event: MessageEvent<string>) => {
      const parsed = JSON.parse(event.data) as WorkflowEvent;
      setWorkflowEvents((current) => current.some((item) => item.sequence === parsed.sequence) ? current : [...current, parsed]);
      if (
        parsed.type === "agent.completed" &&
        ["evaluator enrichment", "reporter enrichment"].includes(String(parsed.payload.agent))
      ) {
        window.setTimeout(() => void loadSavedRequest(activeRequestId), 0);
      }
    };
    eventTypes.forEach((eventType) => stream.addEventListener(eventType, onEvent));
    return () => stream.close();
    // The stream belongs to the active request. Enrichment events hydrate the
    // existing view without recreating the EventSource on each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRequestId]);

  useEffect(() => {
    if (!activeRequestId || !isProcessing) return;

    let cancelled = false;
    let pollTimer: number | undefined;
    const terminalStatuses = [
      "AWAITING_APPROVAL",
      "NEEDS_CLARIFICATION",
      "COMPLETED",
      "FAILED",
    ];

    async function synchronizeWorkflow() {
      try {
        const request = await getProcurementRequest(activeRequestId!);
        if (cancelled) return;
        setWorkflowStatus(request.status);

        if (terminalStatuses.includes(request.status)) {
          await loadSavedRequest(request.id);
          return;
        }
      } catch {
        // A brief network interruption should not strand the workspace. The
        // next poll will retry while the backend continues the workflow.
      }

      if (!cancelled) {
        pollTimer = window.setTimeout(synchronizeWorkflow, 750);
      }
    }

    pollTimer = window.setTimeout(synchronizeWorkflow, 500);
    return () => {
      cancelled = true;
      if (pollTimer !== undefined) window.clearTimeout(pollTimer);
    };
    // loadSavedRequest is intentionally reached only when polling finds a
    // terminal state; activeRequestId and isProcessing own this lifecycle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRequestId, isProcessing]);

  function productFromApi(product: ApiProduct, evaluation: ApiEvaluation | undefined, index: number): Product {
    const specifications = product.specifications;
    const category = typeof specifications.product_category === "string" ? specifications.product_category : "computer_monitor";
    const isMonitor = category === "computer_monitor";
    const deviceLabel = category === "computer_keyboard" ? "Keyboard" : category === "computer_mouse" ? "Mouse" : `${specifications.screen_size_inches ?? "Unknown size"}-inch monitor`;
    const connections = Array.isArray(specifications.connections) ? specifications.connections.map(String).map(titleCase) : [];
    const size = specifications.screen_size_inches ? `${specifications.screen_size_inches}-inch` : "Size unknown";
    const resolution = typeof specifications.resolution === "string" ? specifications.resolution : "Resolution unknown";
    const warranty = typeof specifications.warranty === "string" ? specifications.warranty : "Not provided";
    const palette = ["monitor-art-blue", "monitor-art-silver", "monitor-art-dark"];
    return {
      id: product.id,
      name: product.name,
      category,
      detail: `${product.brand ?? "Unknown brand"} · ${deviceLabel}`,
      price: Number(product.price),
      eligible: evaluation?.eligible === true,
      priceNeedsVerification: specifications.price_requires_verification === true,
      badge: evaluation?.eligible && index === 0 ? "Best fit" : undefined,
      imageClass: `monitor-art ${palette[index % palette.length]}`,
      specs: [...(isMonitor ? [size, resolution] : connections), `Warranty · ${warranty}`],
      pros: evaluation?.eligible ? [evaluation.explanation] : [],
      cons: evaluation?.rejection_reasons.length ? evaluation.rejection_reasons : ["No recorded tradeoffs"],
      warranty,
      source:
        product.source === "demo_catalog"
          ? "Synthetic demo catalog"
          : product.source === "channel3"
            ? `Channel3 · ${product.merchant ?? "merchant offer"}`
            : product.source,
      imageUrl: product.image_url ?? undefined,
      productUrl: product.product_url ?? undefined,
    };
  }

  async function loadSavedRequest(id: string) {
    setWorkflowError(null);
    setIsSubmitting(true);
    try {
      const request = await getProcurementRequest(id);
      setActiveRequestId(request.id);
      setSubmittedText(request.original_prompt);
      setWorkflowStatus(request.status);
      setRequestQuantity(Number(request.structured_requirements?.quantity ?? 1));
      setRequestCategory(String(request.structured_requirements?.category ?? "computer_monitor"));
      const missing = request.structured_requirements?.missing_information;
      setClarificationNeeds(
        request.status === "NEEDS_CLARIFICATION" && Array.isArray(missing)
          ? missing.map(String)
          : [],
      );
      const [apiProducts, evaluations, payment] = await Promise.all([
        getRequestProducts(id),
        getRequestEvaluations(id),
        getRequestPayment(id),
      ]);
      const byProductId = new Map(evaluations.map((evaluation) => [evaluation.product_candidate_id, evaluation]));
      const liveProducts = [...apiProducts]
        .sort((left, right) => Number(byProductId.get(right.id)?.score ?? -1) - Number(byProductId.get(left.id)?.score ?? -1))
        .map((product, index) => productFromApi(product, byProductId.get(product.id), index));
      setProducts(liveProducts);
      setResultsReadyForId(id);
      setCompletedPayment(payment?.status === "COMPLETED" ? payment : null);
      setSelectedProductId(
        payment?.product_candidate_id ??
        request.report?.recommended_product_id ??
        liveProducts.find((product) => product.eligible)?.id ??
        "",
      );
      return true;
    } catch {
      setWorkflowError("ARC could not load this saved request. Confirm the backend is running, then try again.");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function confirmReturnedPayment(paymentReturn: PaymentReturn) {
    setPaymentReturnState("confirming");
    setActiveRequestId(paymentReturn.requestId);
    setPaymentMessage(null);
    let confirmed = false;
    try {
      const payment = await captureCheckoutOrder(paymentReturn.requestId, paymentReturn.orderId);
      if (payment.status !== "COMPLETED") throw new Error("Payment is not confirmed");
      confirmed = true;
      setPaymentWasConfirmed(true);
      setCompletedPayment(payment);
      setPaymentReturnState("loading");
      const loaded = await loadSavedRequest(paymentReturn.requestId);
      if (!loaded) throw new Error("Receipt could not be loaded");
      window.history.replaceState({}, "", `/?requestId=${paymentReturn.requestId}`);
      setPaymentReturnState(null);
    } catch {
      setPaymentMessage(confirmed
        ? "Your payment was confirmed, but ARC could not load the receipt. Check again to retrieve your saved payment details."
        : "ARC could not confirm the payment status. It may still have completed. Check again before starting another payment.");
      setPaymentReturnState("error");
    }
  }

  useEffect(() => {
    if (initialRequestLoaded.current) return;
    initialRequestLoaded.current = true;
    const requestId = new URLSearchParams(window.location.search).get("requestId");
    const params = new URLSearchParams(window.location.search);
    const paypalState = params.get("paypal");
    const paypalOrderId = params.get("token");
    if (requestId && paypalState === "return" && paypalOrderId) {
      void confirmReturnedPayment({ requestId, orderId: paypalOrderId });
    } else if (requestId && paypalState === "cancel") {
      setPaymentMessage("PayPal Sandbox checkout was cancelled. No payment was captured.");
      window.history.replaceState({}, "", `/?requestId=${requestId}`);
      void loadSavedRequest(requestId);
    } else if (requestId) void loadSavedRequest(requestId);
    // Loading only happens for the initial URL; it is not a reactive request view.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function resetWorkspace() {
    setSubmittedRequestId(null);
    setResultsReadyForId(null);
    setRevealedRequestId(null);
    setProducts([]);
    setRequestQuantity(1);
    setRequestCategory("computer_monitor");
    setSelectedProductId("");
    setRequestText("");
    setSubmittedText("");
    setWorkflowStatus(null);
    setActiveRequestId(null);
    setWorkflowEvents([]);
    setWorkflowError(null);
    setClarificationNeeds([]);
    setIsSubmitting(false);
    setShowApproval(false);
    setPaymentMessage(null);
    setCompletedPayment(null);
    document.querySelector(".content-scroll")?.scrollTo({ top: 0, behavior: "smooth" });
    window.setTimeout(() => document.getElementById("request-composer")?.focus(), 150);
  }

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedRequest = requestText.trim();
    if (!trimmedRequest) return;
    setSubmittedRequestId(null);
    setResultsReadyForId(null);
    setRevealedRequestId(null);
    const isClarification = Boolean(
      activeRequestId && workflowStatus === "NEEDS_CLARIFICATION",
    );
    if (!isClarification) {
      setProducts([]);
      setSelectedProductId("");
      setWorkflowEvents([]);
      setActiveRequestId(null);
      setClarificationNeeds([]);
      setCompletedPayment(null);
    }
    setSubmittedText(trimmedRequest);
    setWorkflowError(null);
    setIsSubmitting(true);
    setWorkflowStatus("CREATED");
    try {
      const created =
        isClarification && activeRequestId
          ? await submitClarification(activeRequestId, trimmedRequest)
          : await createProcurementRequest(trimmedRequest);
      setActiveRequestId(created.id);
      setSubmittedRequestId(created.id);
      setWorkflowEvents([]);
      const request = await getProcurementRequest(created.id);
      setRequestQuantity(Number(request.structured_requirements?.quantity ?? 1));
      setRequestCategory(String(request.structured_requirements?.category ?? "computer_monitor"));
      setWorkflowStatus(request.status);
      if (request.status === "NEEDS_CLARIFICATION") {
        const missing = request.structured_requirements?.missing_information;
        setClarificationNeeds(Array.isArray(missing) ? missing.map(String) : []);
      } else {
        setClarificationNeeds([]);
      }
      if (request.status === "AWAITING_APPROVAL" || request.status === "COMPLETED") {
        const [apiProducts, evaluations] = await Promise.all([
          getRequestProducts(created.id),
          getRequestEvaluations(created.id),
        ]);
        const byProductId = new Map(evaluations.map((evaluation) => [evaluation.product_candidate_id, evaluation]));
        const sortedProducts = [...apiProducts].sort((left, right) => {
          const leftScore = Number(byProductId.get(left.id)?.score ?? -1);
          const rightScore = Number(byProductId.get(right.id)?.score ?? -1);
          return rightScore - leftScore;
        });
        const liveProducts = sortedProducts.map((product, index) => productFromApi(product, byProductId.get(product.id), index));
        if (liveProducts.length) {
          setProducts(liveProducts);
          setSelectedProductId(request.report?.recommended_product_id ?? liveProducts.find((product) => product.eligible)?.id ?? "");
        }
        setResultsReadyForId(created.id);
      }
      setRequestText("");
    } catch {
      setWorkflowStatus(null);
      setWorkflowError("ARC could not start this request. Confirm the backend is running, then try again.");
    } finally {
      setIsSubmitting(false);
      void getProcurementHistory().then(setRecentRequests).catch(() => undefined);
    }
  }

  async function startPayPalCheckout() {
    if (!activeRequestId || !selectedProduct) return;
    setIsStartingCheckout(true);
    setPaymentMessage(null);
    try {
      const checkout = await createCheckoutOrder(activeRequestId, selectedProduct.id);
      window.location.assign(checkout.approval_url);
    } catch {
      setPaymentMessage("ARC could not start PayPal Sandbox checkout. Confirm the backend was restarted after adding your PayPal credentials.");
      setIsStartingCheckout(false);
    }
  }

  return (
    <div className={`app-shell${paymentReturnState ? " app-shell-payment-return" : ""}`}>
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="ARC home">
          <Image className="brand-icon" src="/icon.png" width={36} height={36} alt="" priority />
          <span className="brand-name">ARC</span>
        </Link>

        <div className="sidebar-workspace-label">WORKSPACE</div>
        <button
          className="new-request-button"
          type="button"
          onClick={resetWorkspace}
          disabled={Boolean(paymentReturnState)}
        >
          <Plus size={17} strokeWidth={2.2} aria-hidden="true" />
          <span>New request</span>
        </button>

        <div className="sidebar-section-heading">
          <span>RECENT</span>
        </div>
        {recentRequests.slice(0, 3).map((recent) => (
          <Link
            className="recent-item"
            href={`/?requestId=${recent.id}`}
            key={recent.id}
            onClick={(event) => {
              event.preventDefault();
              if (paymentReturnState) return;
              window.history.pushState({}, "", `/?requestId=${recent.id}`);
              void loadSavedRequest(recent.id);
            }}
          >
            <span className="recent-dot" />
            <span className="recent-copy">
              <span>{recent.original_prompt}</span>
              <small>{recent.status.replaceAll("_", " ")}</small>
            </span>
          </Link>
        ))}
        {!recentRequests.length && <p className="sidebar-empty">No saved requests yet</p>}

        <Link className="sidebar-link" href="/history">
          <FileClock size={17} strokeWidth={1.8} aria-hidden="true" />
          <span>Procurement history</span>
        </Link>

        <div className="sidebar-bottom">
          <div className="sidebar-divider" />
          <div className="environment-card">
            <span className="environment-indicator" />
            <span className="environment-copy">
              <span>Preview environment</span>
              <small>Catalog provider · API {apiAvailability.replace("-", " ")}</small>
            </span>
            <CircleHelp size={15} aria-hidden="true" />
          </div>
        </div>
      </aside>

      <main className="main-column">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <span className="breadcrumb-current">{paymentReturnState ? "Payment confirmation" : orderIsComplete ? "Payment complete" : "New procurement"}</span>
          </div>
          <div className="topbar-actions">
            <span className="preview-chip">
              <span />
              PREVIEW
            </span>
            <button
              className="theme-toggle"
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
            >
              {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
            </button>
          </div>
        </header>

        <div className="content-scroll">
          <section className="page-heading">
            <div className="heading-copy">
              <h1>{paymentReturnState ? "Your payment" : "Procurement workspace"}</h1>
            </div>
            <div className="live-status">
              <span className={`status-dot status-dot-${apiAvailability}`} />
              <strong>
                {apiAvailability === "checking" && "Checking API"}
                {apiAvailability === "connected" && "API connected"}
                {apiAvailability === "database-unavailable" && "Database offline"}
                {apiAvailability === "unavailable" && "API offline"}
              </strong>
            </div>
          </section>

          {paymentReturnState ? (
            <section className={`payment-return-card${paymentReturnState === "error" ? " payment-return-error" : ""}`} aria-labelledby="payment-return-title" aria-busy={paymentReturnState !== "error"}>
              <div className="payment-return-symbol" aria-hidden="true">
                {paymentReturnState === "error" ? <Info size={32} /> : <LoaderCircle size={36} className="status-spinner" />}
              </div>
              <p className="eyebrow">PAYPAL SANDBOX</p>
              <div role={paymentReturnState === "error" ? "alert" : "status"} aria-live="polite" aria-atomic="true">
                <h2 id="payment-return-title">{paymentReturnState === "error" ? paymentWasConfirmed ? "Payment confirmed. Receipt unavailable." : "We couldn’t confirm your payment yet." : paymentReturnState === "loading" ? "Payment confirmed. Preparing your receipt." : "Confirming your payment"}</h2>
                <p className="payment-return-description">{paymentReturnState === "error" ? paymentMessage : paymentReturnState === "loading" ? "ARC is loading your purchase details and saved payment confirmation." : "Welcome back. ARC is confirming your Sandbox payment with PayPal. Your receipt will appear here automatically."}</p>
              </div>
              <ol className="payment-return-steps" aria-label="Payment confirmation progress">
                <li className="payment-return-step-done"><span><Check size={16} aria-hidden="true" /></span><div><strong>Returned from PayPal</strong><small>Your checkout session is back in ARC</small></div></li>
                <li className={paymentWasConfirmed ? "payment-return-step-done" : "payment-return-step-current"}><span>{paymentWasConfirmed ? <Check size={16} aria-hidden="true" /> : paymentReturnState === "error" ? <Info size={16} aria-hidden="true" /> : <LoaderCircle size={16} className="status-spinner" aria-hidden="true" />}</span><div><strong>Confirm payment</strong><small>{paymentWasConfirmed ? "PayPal confirmed the completed payment" : "Verify the payment status with PayPal"}</small></div></li>
                <li className={paymentReturnState === "loading" ? "payment-return-step-current" : ""}><span>{paymentReturnState === "loading" ? <LoaderCircle size={16} className="status-spinner" aria-hidden="true" /> : <FileClock size={16} aria-hidden="true" />}</span><div><strong>Prepare your receipt</strong><small>Load your purchase and payment details</small></div></li>
              </ol>
              {paymentReturnState === "error" && <div className="payment-return-actions"><button className="modal-primary-button" type="button" onClick={() => { if (initialPaymentReturn) void confirmReturnedPayment(initialPaymentReturn); }}>Check payment again</button><Link href="/history" className="order-history-link"><FileClock size={16} aria-hidden="true" />View payment history</Link></div>}
              <p className="payment-return-footnote"><LockKeyhole size={14} aria-hidden="true" /> Sandbox checkout · no real money is charged.</p>
            </section>
          ) : <>
          <section className="request-card glass-surface" aria-labelledby="sample-request-title">
            <div className="section-title-row">
              <div>
                <h2 id="sample-request-title">Your request</h2>
              </div>
              <span className="sample-label">{submittedText ? "LIVE REQUEST" : "GET STARTED"}</span>
            </div>
            <div className="request-quote">
              <span className="quote-bar" />
              <p>
                {submittedText ||
                  "Describe the monitors, keyboards, or mice your team needs, including quantity and total budget."}
              </p>
            </div>
          </section>

          {(submittedText || workflowError) && (
            <section
              className={`workflow-state-banner workflow-state-${statusTone}`}
              role="status"
            >
              <span className="workflow-state-icon">
                {statusTone === "processing" && (
                  <LoaderCircle size={22} className="status-spinner" aria-hidden="true" />
                )}
                {statusTone === "clarification" && <CircleHelp size={22} aria-hidden="true" />}
                {statusTone === "approval" && <Check size={22} aria-hidden="true" />}
                {statusTone === "error" && <Info size={22} aria-hidden="true" />}
              </span>
              <span className="workflow-state-copy">
                <strong>{statusLabel}</strong>
                <small>
                  {workflowError ??
                    (orderIsComplete
                      ? "Your PayPal Sandbox payment was confirmed and the receipt is available in procurement history."
                      : noEligibleMatches
                      ? "No catalog offers passed your requirements and review checks. Try adjusting the budget or requirements."
                      : workflowStatus === "FAILED"
                      ? "The workflow stopped safely. Check the configured model and catalog-provider credentials, then try again."
                      : statusTone === "clarification"
                      ? `Tell ARC ${clarificationNeeds.length ? clarificationNeeds.join(", ") : "the missing details"} in the box below.`
                      : statusTone === "approval"
                        ? "Review the ranked options and approve the best fit when you are ready."
                        : currentProcessingCopy.detail)}
                </small>
              </span>
            </section>
          )}

          <section className="results-section" aria-labelledby="results-title">
            <div className="results-heading">
              <div>
                <h2 id="results-title">
                  {orderIsComplete
                    ? "Order complete"
                    : displayedProducts.length
                    ? selectedProduct ? "Options to consider" : "No eligible matches"
                    : noEligibleMatches
                      ? "No eligible matches"
                    : showProgress
                      ? "Working on your request"
                      : workflowStatus === "NEEDS_CLARIFICATION"
                        ? "Complete your request"
                        : "Start a procurement request"}
                </h2>
                <p>
                  {orderIsComplete
                    ? "Your payment was confirmed and saved to the ARC workspace"
                    : displayedProducts.length
                    ? selectedProduct ? `Catalog offers evaluated for ${requestQuantity} ${categoryLabel}` : "These catalog results did not pass your requirements or price verification checks."
                    : showProgress
                      ? currentProcessingCopy.detail
                      : workflowStatus === "NEEDS_CLARIFICATION"
                        ? "Add the missing details in the composer below"
                        : "Submit a request to see evaluated recommendations"}
                </p>
              </div>
            </div>

            {displayedProducts.length > 0 && !orderIsComplete && <div className="budget-strip">
              <span><strong>Live results</strong> · recommendations are based on your submitted requirements</span>
            </div>}

            {displayedProducts.length > 0 && selectedProduct && !orderIsComplete && (
              <div className="selection-review-card glass-surface">
                <div className="selection-review-copy">
                  <span className="selection-review-icon"><Check size={17} aria-hidden="true" /></span>
                  <span>
                    <small>SELECTED OPTION</small>
                    <strong>{selectedProduct.name}</strong>
                    <span>{currency.format(selectedProduct.price * requestQuantity)} estimated total for {requestQuantity} · PayPal Sandbox</span>
                  </span>
                </div>
                <button className="approval-review-button" type="button" onClick={() => setShowApproval(true)}>
                  Review &amp; approve
                  <ArrowUpRight size={16} aria-hidden="true" />
                </button>
              </div>
            )}

            <div className="product-list">
              {orderIsComplete && completedPayment && orderedProduct && (
                <article className="order-complete-card glass-surface">
                  <div className="order-complete-heading">
                    <span className="order-complete-mark"><Check size={26} aria-hidden="true" /></span>
                    <div>
                      <p className="eyebrow">PAYPAL SANDBOX · PAYMENT CONFIRMED</p>
                      <h3>Your order is complete.</h3>
                      <p>ARC recorded the approved payment and stored its receipt in procurement history.</p>
                    </div>
                  </div>
                  <div className="order-complete-product">
                    <div
                      className={`${orderedProduct.imageClass}${orderedProduct.imageUrl ? " monitor-art-live" : ""}`}
                      style={orderedProduct.imageUrl ? { backgroundImage: `url(${orderedProduct.imageUrl})` } : undefined}
                      aria-hidden="true"
                    >
                        {!orderedProduct.imageUrl && <ProductPlaceholder category={orderedProduct.category} />}
                    </div>
                    <div className="order-complete-product-copy">
                      <strong>{orderedProduct.name}</strong>
                      <span>Quantity {completedPayment.quantity} · {orderedProduct.detail}</span>
                    </div>
                    <div className="order-complete-total">
                      <small>Total paid</small>
                      <strong>{paymentCurrency.format(Number(completedPayment.amount))}</strong>
                    </div>
                  </div>
                  <div className="order-complete-footer">
                    <span>Capture ID · {completedPayment.paypal_capture_id}</span>
                    <Link className="order-history-link" href="/history">
                      <FileClock size={16} aria-hidden="true" />
                      View receipt in history
                    </Link>
                  </div>
                </article>
              )}
              {!orderIsComplete && displayedProducts.length === 0 && <div className={`empty-results glass-surface${showProgress ? " empty-results-processing" : ""}`}>
                {showCompletedSteps ? <Check size={22} aria-hidden="true" /> : showProgress ? <LoaderCircle size={22} className="status-spinner" aria-hidden="true" /> : workflowStatus === "NEEDS_CLARIFICATION" ? <CircleHelp size={22} aria-hidden="true" /> : <Sparkles size={20} aria-hidden="true" />}
                <div>
                  <strong>{showProgress ? currentProcessingCopy.title : noEligibleMatches ? "No matching offers passed the checks." : workflowStatus === "NEEDS_CLARIFICATION" ? "A quick clarification will help." : "Your workspace is ready."}</strong>
                  <span>{showProgress ? currentProcessingCopy.detail : noEligibleMatches ? "Try adjusting the total budget or product requirements." : workflowStatus === "NEEDS_CLARIFICATION" ? "Use the request box below to provide the missing information." : "Send a request below to start ARC's procurement workflow."}</span>
                </div>
                {showProgress && <div className="workflow-progress" aria-label="Workflow progress">
                  {workflowStages.map((stage, index) => {
                    const isActive = !showCompletedSteps && index === currentStageIndex;
                    const isDone = showCompletedSteps || currentStageIndex > index;
                    return <span className={`workflow-progress-step${isActive ? " workflow-progress-active" : ""}${isDone ? " workflow-progress-done" : ""}`} key={stage.status} aria-current={isActive ? "step" : undefined}>
                      <i>{isDone ? <Check size={11} aria-hidden="true" /> : index + 1}</i>
                      {stage.label}
                    </span>;
                  })}
                </div>}
              </div>}
              {!orderIsComplete && displayedProducts.map((product) => {
                const isSelected = selectedProductId === product.id;
                const total = product.price * requestQuantity;
                return (
                  <article
                    className={`product-card glass-surface${isSelected ? " product-card-selected" : ""}`}
                    key={product.id}
                  >
                    <div className="product-card-top">
                      <div
                        className={`${product.imageClass}${product.imageUrl ? " monitor-art-live" : ""}`}
                        style={product.imageUrl ? { backgroundImage: `url(${product.imageUrl})` } : undefined}
                        aria-hidden="true"
                      >
                        {!product.imageUrl && <ProductPlaceholder category={product.category} />}
                      </div>
                      <div className="product-overview">
                        <div className="product-name-row">
                          <div>
                            <h3>{product.name}</h3>
                          </div>
                          {product.badge && (
                            <span className="recommendation-badge">
                              <Sparkles size={12} aria-hidden="true" />
                              {product.badge}
                            </span>
                          )}
                        </div>
                        <p className="product-detail">{product.detail}</p>
                        <div className="spec-chips">
                          {product.specs.map((spec) => <span key={spec}>{spec}</span>)}
                        </div>
                      </div>
                      <div className="product-price">
                        <span className="price-unit">{currency.format(product.price)} <small>/ unit</small></span>
                        <strong>{currency.format(total)}</strong>
                        <small>for {requestQuantity} · before tax &amp; shipping</small>
                        {product.priceNeedsVerification && <small className="price-review-notice">Unverified low catalog price</small>}
                      </div>
                    </div>

                    <div className="product-card-bottom">
                      <div className="evidence-row">
                        <span className="warranty-copy">
                          <ShieldCheck size={14} aria-hidden="true" />
                          Warranty: {product.warranty}
                        </span>
                        {product.productUrl ? (
                          <a className="source-copy" href={product.productUrl} target="_blank" rel="noreferrer">
                            {product.source}
                          </a>
                        ) : <span className="source-copy">{product.source}</span>}
                      </div>
                      <div className="product-actions">
                        <button
                          className={`select-button${isSelected ? " select-button-active" : ""}`}
                          type="button"
                          aria-pressed={isSelected}
                          disabled={!product.eligible}
                          onClick={() => setSelectedProductId(product.id)}
                        >
                          {!product.eligible ? "Not eligible" : isSelected ? <><Check size={14} aria-hidden="true" /> Selected</> : "Select option"}
                        </button>
                      </div>
                    </div>

                    <details className="evidence-details">
                      <summary>
                        <span className="evidence-summary-copy">
                          <span className="evidence-summary-icon"><Sparkles size={15} aria-hidden="true" /></span>
                          <span><strong>Evidence &amp; tradeoffs</strong><small>See why this option fits your request</small></span>
                        </span>
                        <span className="evidence-toggle">View analysis <ChevronDown size={15} aria-hidden="true" /></span>
                      </summary>
                      <div className="tradeoff-grid">
                        <div>
                          <strong className="pro-heading">What fits</strong>
                          {product.pros.map((pro) => <p key={pro}><Check size={13} aria-hidden="true" />{pro}</p>)}
                        </div>
                        <div>
                          <strong className="con-heading">Consider</strong>
                          {product.cons.map((con) => <p key={con}><Info size={13} aria-hidden="true" />{con}</p>)}
                        </div>
                      </div>
                    </details>
                  </article>
                );
              })}
            </div>
            {displayedProducts.length > 0 && !orderIsComplete && <p className="sample-disclaimer">
              {hasLiveCatalogResults
                ? "Live catalog data from Channel3. Confirm prices and availability with the merchant."
                : "Product details are illustrative, not live listings or purchase offers."}
            </p>}
          </section>

          <section className="composer-wrap">
            <form className="composer glass-surface" onSubmit={submitRequest}>
              <label className="sr-only" htmlFor="request-composer">Describe what your team needs</label>
              <textarea
                id="request-composer"
                value={requestText}
                onChange={(event) => setRequestText(event.target.value)}
                placeholder={workflowStatus === "NEEDS_CLARIFICATION" ? "Add the missing details…" : "Describe the monitors, keyboards, or mice you need…"}
                rows={1}
              />
              <div className="composer-footer">
              <span><LockKeyhole size={13} aria-hidden="true" /> Requests are processed by your local ARC API</span>
                <button className="send-button" type="submit" disabled={!requestText.trim() || isSubmitting} aria-label="Submit procurement request">
                  <Send size={15} aria-hidden="true" />
                </button>
              </div>
            </form>
            <p className="composer-footnote">Workflow results are stored in your local ARC workspace.</p>
          </section>
          {paymentMessage && <p className="payment-message" role="status">{paymentMessage}</p>}
          </>}
        </div>
      </main>

      {!paymentReturnState && <aside className="activity-panel">
        <div className="activity-header">
          <h2>Activity</h2>
          <Activity size={17} className="activity-header-icon" aria-hidden="true" />
        </div>

        <div className={`workflow-status-card workflow-card-${statusTone}`}>
          <div className="workflow-status-top">
            <span className="workflow-icon"><Cpu size={17} aria-hidden="true" /></span>
            <span className="workflow-id">{workflowStatus ?? "NO ACTIVE REQUEST"}</span>
            <span className="workflow-dot" />
          </div>
          <h3>{statusLabel}</h3>
          <p>{workflowStatus ? "This panel reflects the persisted workflow in real time." : "Submit a request to start the live workflow."}</p>
        </div>

        <div className="activity-section agent-timeline-section">
          <div className="activity-section-heading">
            <h3>Agent timeline</h3>
          </div>
          <div className="timeline-scroll">
            {workflowEvents.length === 0 && <div className="timeline-empty"><Clock3 size={15} aria-hidden="true" /><span>No live events</span></div>}
            {workflowEvents.map((event) => <div className="timeline-event" key={event.sequence}>
              <span className="timeline-marker" />
              <span>{event.payload.agent ? `${titleCase(String(event.payload.agent))} · ` : ""}{activityCopy[event.type] ?? titleCase(event.type)}</span>
            </div>)}
          </div>
        </div>

        <div className="activity-section data-section">
          <div className="activity-section-heading">
            <h3>Data sources</h3>
          </div>
          <div className="data-source-row">
            <span className="source-icon"><Monitor size={15} aria-hidden="true" /></span>
            <span className="data-source-copy"><strong>Product catalog</strong><small>{hasLiveCatalogResults ? "Live Channel3 offers" : "Awaiting provider results"}</small></span>
            <span className={`source-state ${hasLiveCatalogResults ? "source-state-connected" : "source-state-demo"}`}>{hasLiveCatalogResults ? "LIVE" : "READY"}</span>
          </div>
          <div className="data-source-row">
            <span className="source-icon source-icon-muted"><Activity size={15} aria-hidden="true" /></span>
            <span className="data-source-copy"><strong>ARC API</strong><small>Health endpoint</small></span>
            <span className={`source-state source-state-${apiAvailability}`}>
              {apiAvailability === "checking" && "CHECKING"}
              {apiAvailability === "connected" && "ONLINE"}
              {apiAvailability === "database-unavailable" && "DEGRADED"}
              {apiAvailability === "unavailable" && "OFFLINE"}
            </span>
          </div>
        </div>

        <div className="right-panel-bottom">
          <div className="privacy-note">
            <ShieldCheck size={15} aria-hidden="true" />
            <span>Purchases always require your explicit approval.</span>
          </div>
          <span className="approval-unavailable">PayPal Sandbox · explicit approval required</span>
        </div>
      </aside>}
      {showApproval && selectedProduct && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setShowApproval(false);
        }}>
          <section className="approval-modal glass-surface" role="dialog" aria-modal="true" aria-labelledby="approval-title">
            <button className="modal-close icon-button" type="button" onClick={() => setShowApproval(false)} aria-label="Close approval preview">
              <X size={18} aria-hidden="true" />
            </button>
            <div className="modal-icon"><LockKeyhole size={20} aria-hidden="true" /></div>
            <p className="eyebrow">PAYPAL SANDBOX</p>
            <h2 id="approval-title">Review before you approve.</h2>
            <p className="modal-description">ARC will create a Sandbox order only after you continue. PayPal handles the approval; ARC captures it only after you approve.</p>
            <div className="approval-summary">
              <div className="approval-product">
                <div className={`${selectedProduct.imageClass}${selectedProduct.imageUrl ? " monitor-art-live" : ""}`} style={selectedProduct.imageUrl ? { backgroundImage: `url(${selectedProduct.imageUrl})` } : undefined} aria-hidden="true">
                  {!selectedProduct.imageUrl && <ProductPlaceholder category={selectedProduct.category} />}
                </div>
                <div><strong>{selectedProduct.name}</strong><span>Quantity {requestQuantity} · {selectedProduct.detail}</span></div>
              </div>
              <div className="approval-line"><span>Unit price</span><strong>{currency.format(selectedProduct.price)}</strong></div>
              <div className="approval-line"><span>Estimated subtotal</span><strong>{currency.format(selectedProduct.price * requestQuantity)}</strong></div>
              <div className="approval-line approval-total"><span>Total · USD</span><strong>{currency.format(selectedProduct.price * requestQuantity)}</strong></div>
              <div className="sandbox-disclosure"><Info size={15} aria-hidden="true" /> This is a PayPal Sandbox payment demonstration. The Channel3 merchant offer remains an external link.</div>
            </div>
            <button className="modal-primary-button" type="button" onClick={startPayPalCheckout} disabled={isStartingCheckout}>
              {isStartingCheckout ? "Creating PayPal order…" : "Continue to PayPal Sandbox"}
            </button>
            <button className="modal-secondary-button" type="button" onClick={() => setShowApproval(false)} disabled={isStartingCheckout}>Cancel</button>
            <p className="modal-footnote"><LockKeyhole size={12} aria-hidden="true" /> No real money moves in the PayPal Sandbox.</p>
          </section>
        </div>
      )}
    </div>
  );
}
