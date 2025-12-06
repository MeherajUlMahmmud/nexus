import { Link } from 'react-router-dom';
import { MessageSquare } from 'lucide-react';
import { APP_ROUTES } from '@/lib/constants';

export function AuthNavbar() {
  return (
    <nav className="border-b border-border bg-card">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link to={APP_ROUTES.HOME} className="flex items-center gap-2">
            <MessageSquare className="size-6 text-primary" />
            <span className="text-xl font-bold">Nexus</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to={APP_ROUTES.LOGIN}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign in
            </Link>
            <Link
              to={APP_ROUTES.REGISTER}
              className="text-sm bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
            >
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
