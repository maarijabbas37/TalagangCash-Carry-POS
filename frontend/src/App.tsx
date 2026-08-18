import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { MainLayout } from "./layouts/MainLayout";
import { POS } from "./pages/POS/POS";
import { SalesHistory } from "./pages/SalesHistory/SalesHistory";
import { Login } from "./pages/Login/Login";
import { Products } from "./pages/Products/Products";
import { AuthProvider } from "./hooks/useAuth";
import { ProtectedRoute } from "./routes/ProtectedRoute";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/" element={<POS />} />
                <Route path="/sales-history" element={<SalesHistory />} />
                <Route path="/products" element={<Products />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute allowedRoles={["OWNER"]} />}>
              <Route element={<MainLayout />}>
                <Route
                  path="/users"
                  element={<div className="p-8 text-gray-500">User management — Phase 1 scaffold.</div>}
                />
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
