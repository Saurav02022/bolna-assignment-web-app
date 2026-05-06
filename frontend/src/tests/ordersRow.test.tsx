import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Row } from "@/components/orders/Row";
import { Table, TableBody } from "@/components/ui/table";
import type { OrderResponse } from "@/types/api";

const baseOrder: OrderResponse = {
  id: "ORD-1001",
  customer_name: "Priya Patel",
  phone: "+919572365331",
  product_summary: "Cotton Kurta size L",
  order_value: 1299,
  address_short: "Indiranagar, Bengaluru 560038",
  scheduled_slot: "7 May, 2 PM se 6 PM",
  brand_name: "RetailKart",
  status: "pending_verification",
  last_call_id: null,
  last_call_outcome: null,
  captured_address_landmark: null,
  captured_new_slot: null,
  captured_cancel_reason: null,
  captured_followup_question: null,
  last_transcript_url: null,
  last_recording_url: null,
  last_summary: null,
  created_at: "2026-05-05T10:00:00Z",
  updated_at: "2026-05-05T10:00:00Z",
};

function renderRow(props: Partial<React.ComponentProps<typeof Row>> = {}) {
  const onVerify = vi.fn();
  const onView = vi.fn();
  const onEdit = vi.fn();
  const onDelete = vi.fn();
  render(
    <Table>
      <TableBody>
        <Row
          order={baseOrder}
          isVerifying={false}
          onVerify={onVerify}
          onView={onView}
          onEdit={onEdit}
          onDelete={onDelete}
          {...props}
        />
      </TableBody>
    </Table>,
  );
  return { onVerify, onView, onEdit, onDelete };
}

describe("Row", () => {
  it("renders the order data", () => {
    renderRow();
    expect(screen.getByText("ORD-1001")).toBeInTheDocument();
    expect(screen.getByText("Priya Patel")).toBeInTheDocument();
    expect(screen.getByText(/Cotton Kurta/)).toBeInTheDocument();
    expect(screen.getByText("Pending verification")).toBeInTheDocument();
  });

  it("invokes onVerify with the order id when verify is clicked", async () => {
    const { onVerify } = renderRow();
    await userEvent.click(screen.getByRole("button", { name: /^Verify$/i }));
    expect(onVerify).toHaveBeenCalledWith("ORD-1001");
  });

  it("disables the verify button while a call is in flight", () => {
    renderRow({ isVerifying: true });
    expect(screen.getByRole("button", { name: /^Verify$/i })).toBeDisabled();
  });

  it("disables verify when status is already in a terminal state", () => {
    renderRow({ order: { ...baseOrder, status: "ship_approved" } });
    expect(screen.getByRole("button", { name: /^Verify$/i })).toBeDisabled();
  });

  it("invokes onView when the view button is clicked", async () => {
    const { onView } = renderRow();
    await userEvent.click(screen.getByRole("button", { name: /View details/i }));
    expect(onView).toHaveBeenCalledWith("ORD-1001");
  });
});
