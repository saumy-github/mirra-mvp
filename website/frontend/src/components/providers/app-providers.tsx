import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig, motion } from "motion/react";
import { useLocation } from "react-router-dom";
import { useState } from "react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <MotionConfig
        reducedMotion="user"
        transition={{ type: "spring", stiffness: 420, damping: 38, mass: 0.8 }}
      >
        <RouteTransition>{children}</RouteTransition>
      </MotionConfig>
    </QueryClientProvider>
  );
}

function RouteTransition({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      key={pathname}
      className="flex min-h-full flex-1 flex-col"
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8, scale: 0.997 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={
        reduceMotion
          ? { duration: 0.14, ease: "easeOut" }
          : { type: "spring", stiffness: 360, damping: 38, mass: 0.85 }
      }
    >
      {children}
    </motion.div>
  );
}
