import type { Metadata } from "next";
import { ArcWorkspace } from "@/components/arc-workspace";

export const metadata: Metadata = { title: "ARC — Procurement workspace" };

export default async function WorkspacePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const initialPaymentReturn =
    params.paypal === "return" &&
    typeof params.requestId === "string" &&
    typeof params.token === "string"
      ? { requestId: params.requestId, orderId: params.token }
      : undefined;
  return <ArcWorkspace initialPaymentReturn={initialPaymentReturn} />;
}
