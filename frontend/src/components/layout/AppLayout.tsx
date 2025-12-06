import { Outlet } from 'react-router-dom';
import { AuthGuard } from '@/components/auth/AuthGuard';

export function AppLayout() {
  return (
    <AuthGuard requireAuth={true}>
      <div className="flex min-h-screen flex-col bg-background">
        <Outlet />
      </div>
    </AuthGuard>
  );
}
