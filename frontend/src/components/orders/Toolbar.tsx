import { Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  totalCount: number;
  isRefreshing: boolean;
  onRefreshAll: () => void;
  onNewOrder: () => void;
};

export function Toolbar({ totalCount, isRefreshing, onRefreshAll, onNewOrder }: Props) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Orders</h1>
        <p className="text-sm text-muted-foreground">
          {totalCount} {totalCount === 1 ? "order" : "orders"} pending pre-dispatch verification.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Button type="button" size="sm" onClick={onNewOrder}>
          <Plus aria-hidden />
          New order
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRefreshAll}
          disabled={isRefreshing}
          aria-label="Refresh orders"
        >
          <RefreshCw className={isRefreshing ? "animate-spin" : undefined} aria-hidden />
          {isRefreshing ? "Refreshing" : "Refresh"}
        </Button>
      </div>
    </div>
  );
}
