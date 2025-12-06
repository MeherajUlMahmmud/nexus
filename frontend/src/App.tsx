import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { ModelProvider } from '@/contexts/ModelContext';
import { SessionProvider } from '@/contexts/SessionContext';
import { APP_ROUTES } from '@/lib/constants';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { AppLayout } from '@/components/layout/AppLayout';
import { Toaster } from '@/components/ui/sonner';
import LoginPage from '@/pages/auth/LoginPage';
import RegisterPage from '@/pages/auth/RegisterPage';
import ChatPage from '@/pages/chat/ChatPage';
import ChatSessionPage from '@/pages/chat/ChatSessionPage';

function App() {
    return (
        <AuthProvider>
            <ModelProvider>
                <SessionProvider>
                    <Routes>
                        <Route element={<AuthLayout />}>
                            <Route path={APP_ROUTES.LOGIN} element={<LoginPage />} />
                            <Route path={APP_ROUTES.REGISTER} element={<RegisterPage />} />
                        </Route>
                        <Route element={<AppLayout />}>
                            <Route path={APP_ROUTES.HOME} element={<ChatPage />} />
                            <Route path="/:sessionId" element={<ChatSessionPage />} />
                        </Route>
                        <Route path="*" element={<Navigate to={APP_ROUTES.HOME} replace />} />
                    </Routes>
                    <Toaster />
                </SessionProvider>
            </ModelProvider>
        </AuthProvider>
    );
}

export default App;
