import type { Metadata } from "next";
import { ArcWorkspace } from "@/components/arc-workspace";
import { ArcLanding } from "@/components/arc-landing";

export const metadata: Metadata = {
  title: "ARC — From intent to transaction",
  description: "Describe what your team needs, compare evidence-backed options, and approve a PayPal Sandbox payment.",
};

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  if (!params.requestId && !params.paypal) {
    return <ArcLanding />;
  }
  const initialPaymentReturn =
    params.paypal === "return" &&
    typeof params.requestId === "string" &&
    typeof params.token === "string"
      ? { requestId: params.requestId, orderId: params.token }
      : undefined;
  return <ArcWorkspace initialPaymentReturn={initialPaymentReturn} />;
}
