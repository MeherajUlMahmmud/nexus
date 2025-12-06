import { Outlet } from 'react-router-dom';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { AuthNavbar } from '@/components/layout/AuthNavbar';

export function AuthLayout() {
  return (
    <AuthGuard requireAuth={false}>
      <div className="flex min-h-screen flex-col bg-background">
        <AuthNavbar />
        <div className="flex flex-1 items-center justify-center p-4">
          <Outlet />
        </div>
      </div>
    </AuthGuard>
  );
}
