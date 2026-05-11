import { Outlet } from "react-router-dom";
import { TopNav } from "./TopNav";

export function AppShell() {
  return (
    <div className="min-h-screen bg-ink-50 text-ink-800">
      <TopNav />
      <main className="mx-auto w-full max-w-[1280px] px-6 py-8 lg:px-10 lg:py-12 animate-fade-in">
        <Outlet />
      </main>
    </div>
  );
}
