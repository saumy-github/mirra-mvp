import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAccount } from "@/hooks/use-shopper";

/** Auth pages are for signed-out visitors; a signed-in shopper goes on to `destination`. */
export function useRedirectIfSignedIn(destination: string) {
  const navigate = useNavigate();
  const { data: account, isLoading } = useAccount();
  // Decide once, on arrival. Signing in on this page navigates by itself
  // (signup to setup, login to Studio), so a later account must not redirect.
  const decided = useRef(false);
  useEffect(() => {
    if (decided.current || isLoading) return;
    decided.current = true;
    if (account) navigate(destination, { replace: true });
  }, [account, isLoading, destination, navigate]);
}
