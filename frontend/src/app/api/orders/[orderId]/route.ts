import type { OrderUpdateInput } from "@/types/api";

import { BackendError } from "@/lib/api";
import { fail, ok } from "@/lib/api-response";
import { deleteOrder, getOrder, updateOrder } from "@/lib/orders-server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ orderId: string }> },
) {
  const { orderId } = await context.params;

  try {
    const data = await getOrder(orderId);
    return ok(data);
  } catch (error) {
    if (error instanceof BackendError) {
      return fail(error.code, error.message, { status: error.status });
    }
    return fail("INTERNAL_ERROR", "Failed to fetch order.", { status: 500 });
  }
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ orderId: string }> },
) {
  const { orderId } = await context.params;

  try {
    const body = (await request.json()) as OrderUpdateInput;
    const updated = await updateOrder(orderId, body);
    return ok(updated);
  } catch (error) {
    if (error instanceof BackendError) {
      return fail(error.code, error.message, { status: error.status });
    }
    return fail("INTERNAL_ERROR", "Failed to update order.", { status: 500 });
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ orderId: string }> },
) {
  const { orderId } = await context.params;

  try {
    await deleteOrder(orderId);
    return ok({ deleted: true });
  } catch (error) {
    if (error instanceof BackendError) {
      return fail(error.code, error.message, { status: error.status });
    }
    return fail("INTERNAL_ERROR", "Failed to delete order.", { status: 500 });
  }
}
