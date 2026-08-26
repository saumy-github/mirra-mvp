import { z } from "zod";
import { MirraHttpClient } from "@/integrations/mirra-api/client";

export type JoinRole = "founder" | "ecommerce" | "product" | "engineering" | "other";

export type MonthlyOrders = "under-1k" | "1k-10k" | "10k-50k" | "50k-plus";

export interface JoinApplicationInput {
  name: string;
  email: string;
  company: string;
  website?: string;
  role: JoinRole;
  monthlyOrders?: MonthlyOrders;
  goals: string;
}

const joinApplicationResponse = z.object({
  ok: z.literal(true),
  applicationId: z.string().min(1),
  confirmationEmailSent: z.boolean(),
});

export type JoinApplicationResponse = z.infer<typeof joinApplicationResponse>;

const joinClient = new MirraHttpClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
});

export function submitJoinApplication(input: JoinApplicationInput) {
  return joinClient.post("/join", joinApplicationResponse, input);
}
