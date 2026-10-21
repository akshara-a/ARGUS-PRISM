"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("ARGUS PRISM Uncaught Client Exception:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md p-6 sm:p-8 rounded-2xl bg-zinc-50 dark:bg-zinc-900/80 border border-zinc-200 dark:border-white/10 shadow-xl text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto shadow-inner">
          <AlertTriangle className="w-6 h-6" />
        </div>

        <div className="space-y-1.5">
          <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
            Audit State Recovery
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
            A temporary client rendering glitch occurred while processing the audit data.
          </p>
        </div>

        {error.message && (
          <div className="p-3 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[11px] font-mono text-zinc-600 dark:text-zinc-400 text-left overflow-x-auto max-h-24">
            {error.message}
          </div>
        )}

        <div className="flex items-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => reset()}
            className="flex-1 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition cursor-pointer flex items-center justify-center gap-2 shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Try Again</span>
          </button>

          <button
            type="button"
            onClick={() => window.location.reload()}
            className="py-2.5 px-4 rounded-xl bg-white dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-white/10 font-medium text-xs transition cursor-pointer flex items-center gap-1.5"
          >
            <Home className="w-3.5 h-3.5 text-zinc-400" />
            <span>Reload</span>
          </button>
        </div>
      </div>
    </div>
  );
}
