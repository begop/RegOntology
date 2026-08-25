import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

interface AppContextValue {
  asOf: string;
  setAsOf: (value: string) => void;
  theme: "light" | "dark";
  toggleTheme: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

function getInitialDate(): string {
  return new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [asOf, setAsOfState] = useState(() => localStorage.getItem("regontology.asOf") ?? getInitialDate());
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    localStorage.getItem("regontology.theme") === "dark" ? "dark" : "light",
  );

  const value = useMemo<AppContextValue>(
    () => ({
      asOf,
      setAsOf: (next) => {
        setAsOfState(next);
        localStorage.setItem("regontology.asOf", next);
      },
      theme,
      toggleTheme: () => {
        setTheme((current) => {
          const next = current === "light" ? "dark" : "light";
          document.documentElement.dataset.theme = next;
          localStorage.setItem("regontology.theme", next);
          return next;
        });
      },
    }),
    [asOf, theme],
  );

  document.documentElement.dataset.theme = theme;
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppContext must be used within AppProvider");
  return context;
}
