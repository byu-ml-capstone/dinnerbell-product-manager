import { Columns3 } from "lucide-react";
import { APP_NAME } from "../../constants";

export function AuthLayout({ title, children }) {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="brand auth-brand">
          <div className="brand-mark">
            <Columns3 size={22} />
          </div>
          <div>
            <h1>{APP_NAME}</h1>
            <p>Sprint planning for the DinnerBell team.</p>
          </div>
        </div>
        <h2>{title}</h2>
        {children}
      </section>
    </main>
  );
}
