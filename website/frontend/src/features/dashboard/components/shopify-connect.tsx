import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { merchantApi } from "../data/merchant-api";
import { refreshWorkspace } from "../data/live-session";
import { Badge, Banner, Card, Field, KeyValue } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * The real Shopify link for a backend workspace (POST /merchant/{id}/shopify/connect).
 *
 * Until the Mirra Shopify app exists, a store owner connects with a custom-app
 * Admin API access token (Shopify admin → Settings → Apps → Develop apps, scope
 * `read_products`). Connecting also reconciles every product that was entered
 * by hand from a pasted URL, so nothing has to be re-entered.
 */
export function ShopifyConnectCard({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();
  const [storeDomain, setStoreDomain] = useState("");
  const [accessToken, setAccessToken] = useState("");

  const workspace = useQuery({
    queryKey: ["merchant-workspace", tenantId],
    queryFn: () => merchantApi.getWorkspace(tenantId),
  });

  const connect = useMutation({
    mutationFn: () =>
      merchantApi.connectShopify(tenantId, {
        storeDomain: storeDomain.trim(),
        accessToken: accessToken.trim(),
        scopes: ["read_products"],
      }),
    onSuccess: (ws) => {
      refreshWorkspace(ws);
      setAccessToken("");
      qc.setQueryData(["merchant-workspace", tenantId], ws);
      qc.invalidateQueries({ queryKey: ["merchant-products", tenantId] });
    },
  });

  const reconcile = useMutation({
    mutationFn: () => merchantApi.reconcile(tenantId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["merchant-products", tenantId] }),
  });

  const shopify = workspace.data?.shopify;
  // The backend's own role decides (owner/admin hold settings.edit there);
  // the dashboard's demo role map has no exact equivalent for admin.
  const canManage = workspace.data?.role === "owner" || workspace.data?.role === "admin";

  return (
    <Card title="Shopify store">
      {workspace.isLoading && <p className="text-sm text-muted">Loading…</p>}
      {workspace.error && <Banner tone="danger">Could not load the store connection.</Banner>}
      {shopify && (
        <KeyValue
          rows={[
            [
              "Status",
              shopify.connected ? (
                <Badge key="s" tone="success">
                  Connected
                </Badge>
              ) : (
                <Badge key="s" tone="danger">
                  Not connected
                </Badge>
              ),
            ],
            ["Store", shopify.storeDomain || "—"],
            [
              "Connected",
              shopify.connectedAt ? new Date(shopify.connectedAt).toLocaleString() : "—",
            ],
            ...(shopify.lastSyncError
              ? [["Last sync error", shopify.lastSyncError] as [string, string]]
              : []),
          ]}
        />
      )}

      {canManage && (
        <form
          className="mt-5 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            connect.mutate();
          }}
        >
          <Field label="Store domain" hint="yourbrand.myshopify.com">
            <input
              className={inputClass}
              value={storeDomain}
              onChange={(e) => setStoreDomain(e.target.value)}
            />
          </Field>
          <Field
            label="Admin API access token"
            hint="From a custom app in your Shopify admin with the read_products scope. Stored server-side, never shown again."
          >
            <input
              className={inputClass}
              type="password"
              autoComplete="off"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
            />
          </Field>
          {connect.error && (
            <Banner tone="danger">
              {connect.error instanceof Error ? connect.error.message : "Connecting failed."}
            </Banner>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              className={buttonClass("primary")}
              disabled={connect.isPending || !storeDomain.trim() || !accessToken.trim()}
            >
              {connect.isPending
                ? "Connecting…"
                : shopify?.connected
                  ? "Update connection"
                  : "Connect store"}
            </button>
            {shopify?.connected && (
              <button
                type="button"
                className={buttonClass("secondary")}
                disabled={reconcile.isPending}
                onClick={() => reconcile.mutate()}
              >
                {reconcile.isPending ? "Syncing…" : "Re-link hand-entered products"}
              </button>
            )}
          </div>
          {reconcile.data && (
            <Banner tone="info">
              Linked {reconcile.data.linked.length} product(s) to Shopify;{" "}
              {reconcile.data.unmatched.length} had no matching handle in the store.
            </Banner>
          )}
        </form>
      )}
    </Card>
  );
}
