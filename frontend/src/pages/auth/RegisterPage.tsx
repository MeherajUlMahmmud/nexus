import { Link } from 'react-router-dom';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { APP_ROUTES } from '@/lib/constants';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export default function RegisterPage() {
    return (
        <Card className="w-full max-w-md">
            <CardHeader className="space-y-1">
                <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
                <CardDescription>
                    Enter your information to get started
                </CardDescription>
            </CardHeader>
            <CardContent>
                <RegisterForm />
            </CardContent>
            <CardFooter className="flex flex-col">
                <div className="text-center text-sm text-muted-foreground w-full">
                    Already have an account?{' '}
                    <Link to={APP_ROUTES.LOGIN} className="text-primary hover:underline">
                        Sign in
                    </Link>
                </div>
            </CardFooter>
        </Card>
    );
}
