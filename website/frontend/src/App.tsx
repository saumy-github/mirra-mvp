import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProviders } from "@/components/providers/app-providers";
import { AppRoutes } from "@/router";

export default function App() {
  return (
    <BrowserRouter>
      <AppProviders>
        <AppRoutes />
        <Toaster position="bottom-center" richColors closeButton />
      </AppProviders>
    </BrowserRouter>
  );
}
