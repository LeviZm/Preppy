import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { AuthPage } from "./components/auth/AuthPage";
import { Layout } from "./components/layout/Layout";
import { RecipesPage } from "./pages/RecipesPage";
import { MealPlanPage } from "./pages/MealPlanPage";
import { PantryPage } from "./pages/PantryPage";
import { AIPage } from "./pages/AIPage";
import { SettingsPage } from "./pages/SettingsPage";

function ProtectedRoutes() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Layout />;
}

export function App() {
  const { user } = useAuth();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/recipes" replace /> : <AuthPage />} />
        <Route element={<ProtectedRoutes />}>
          <Route index element={<Navigate to="/recipes" replace />} />
          <Route path="/recipes" element={<RecipesPage />} />
          <Route path="/plan" element={<MealPlanPage />} />
          <Route path="/pantry" element={<PantryPage />} />
          <Route path="/ai" element={<AIPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to={user ? "/recipes" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
