import type { OrderCreateInput } from "@/types/api";

import { fail, ok } from "@/lib/api-response";
import { BackendError } from "@/lib/api";
import { createOrder, listOrders } from "@/lib/orders-server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const data = await listOrders();
    return ok(data);
  } catch (error) {
    if (error instanceof BackendError) {
      return fail(error.code, error.message, { status: error.status });
    }
    return fail("INTERNAL_ERROR", "Failed to list orders.", { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as OrderCreateInput;
    const created = await createOrder(body);
    return ok(created, { status: 201 });
  } catch (error) {
    if (error instanceof BackendError) {
      return fail(error.code, error.message, { status: error.status });
    }
    return fail("INTERNAL_ERROR", "Failed to create order.", { status: 500 });
  }
}
