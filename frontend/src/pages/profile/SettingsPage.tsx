import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Eye, EyeOff, AlertCircle, Trash2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { UserRepository, UserUpdate, PasswordChange } from '@/repositories/user';
import { useNavigate } from 'react-router-dom';
import { APP_ROUTES } from '@/lib/constants';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export default function SettingsPage() {
    const { user, refreshUser, logout } = useAuth();
    const navigate = useNavigate();

    // Profile update state
    const [profileLoading, setProfileLoading] = useState(false);
    const [username, setUsername] = useState(user?.username || '');
    const [email, setEmail] = useState(user?.email || '');
    const [profileErrors, setProfileErrors] = useState<{ username?: string; email?: string }>({});

    // Password change state
    const [passwordLoading, setPasswordLoading] = useState(false);
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [passwordErrors, setPasswordErrors] = useState<{
        current_password?: string;
        new_password?: string;
        confirm_password?: string;
    }>({});

    // Delete account state
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [deletePassword, setDeletePassword] = useState('');
    const [showDeletePassword, setShowDeletePassword] = useState(false);

    const validateProfile = (): boolean => {
        const errors: { username?: string; email?: string } = {};

        if (username.trim().length < 3) {
            errors.username = 'Username must be at least 3 characters';
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            errors.email = 'Please enter a valid email address';
        }

        setProfileErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const validatePassword = (): boolean => {
        const errors: {
            current_password?: string;
            new_password?: string;
            confirm_password?: string;
        } = {};

        if (!currentPassword) {
            errors.current_password = 'Current password is required';
        }

        if (newPassword.length < 8) {
            errors.new_password = 'New password must be at least 8 characters';
        }

        if (newPassword !== confirmPassword) {
            errors.confirm_password = 'Passwords do not match';
        }

        setPasswordErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleProfileUpdate = async () => {
        if (!validateProfile()) {
            return;
        }

        setProfileLoading(true);
        try {
            const updateData: UserUpdate = {};
            if (username !== user?.username) {
                updateData.username = username.trim();
            }
            if (email !== user?.email) {
                updateData.email = email.trim();
            }

            if (Object.keys(updateData).length === 0) {
                toast.info('No changes to save');
                setProfileLoading(false);
                return;
            }

            const response = await UserRepository.updateProfile(updateData);
            if (response && response.status === 'SUCCESS') {
                toast.success('Profile updated successfully');
                await refreshUser();
            } else {
                toast.error(response?.message || 'Failed to update profile');
            }
        } catch (error: any) {
            console.error('Profile update error:', error);
            const errorMessage =
                error?.response?.data?.message ||
                error?.message ||
                'Failed to update profile. Please try again.';
            toast.error(errorMessage);
        } finally {
            setProfileLoading(false);
        }
    };

    const handlePasswordChange = async () => {
        if (!validatePassword()) {
            return;
        }

        setPasswordLoading(true);
        try {
            const passwordChange: PasswordChange = {
                current_password: currentPassword,
                new_password: newPassword,
            };

            const response = await UserRepository.changePassword(passwordChange);
            if (response && response.status === 'SUCCESS') {
                toast.success('Password changed successfully');
                setCurrentPassword('');
                setNewPassword('');
                setConfirmPassword('');
                setPasswordErrors({});
            } else {
                toast.error(response?.message || 'Failed to change password');
            }
        } catch (error: any) {
            console.error('Password change error:', error);
            const errorMessage =
                error?.response?.data?.message ||
                error?.message ||
                'Failed to change password. Please try again.';
            toast.error(errorMessage);
        } finally {
            setPasswordLoading(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (!deletePassword) {
            toast.error('Please enter your password to confirm');
            return;
        }

        setDeleteLoading(true);
        try {
            const response = await UserRepository.deleteAccount(deletePassword);
            if (response && response.status === 'SUCCESS') {
                toast.success('Account deleted successfully');
                logout();
                navigate(APP_ROUTES.LOGIN);
            } else {
                toast.error(response?.message || 'Failed to delete account');
            }
        } catch (error: any) {
            console.error('Account deletion error:', error);
            const errorMessage =
                error?.response?.data?.message ||
                error?.message ||
                'Failed to delete account. Please try again.';
            toast.error(errorMessage);
        } finally {
            setDeleteLoading(false);
            setShowDeleteDialog(false);
            setDeletePassword('');
        }
    };

    if (!user) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background">
            <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
                <div className="mb-6">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(APP_ROUTES.PROFILE)}
                        className="mb-4"
                    >
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back
                    </Button>
                    <h1 className="text-3xl font-bold">Settings</h1>
                    <p className="text-muted-foreground mt-1">Manage your account settings and preferences</p>
                </div>

                <Tabs defaultValue="profile" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="profile">Profile</TabsTrigger>
                        <TabsTrigger value="security">Security</TabsTrigger>
                    </TabsList>

                    <TabsContent value="profile" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Profile Information</CardTitle>
                                <CardDescription>Update your profile information</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="username">Username</Label>
                                    <Input
                                        id="username"
                                        value={username}
                                        onChange={(e) => {
                                            setUsername(e.target.value);
                                            if (profileErrors.username) {
                                                setProfileErrors({ ...profileErrors, username: undefined });
                                            }
                                        }}
                                        disabled={profileLoading}
                                        className={profileErrors.username ? 'border-destructive' : ''}
                                    />
                                    {profileErrors.username && (
                                        <p className="text-sm text-destructive flex items-center gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {profileErrors.username}
                                        </p>
                                    )}
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="email">Email</Label>
                                    <Input
                                        id="email"
                                        type="email"
                                        value={email}
                                        onChange={(e) => {
                                            setEmail(e.target.value);
                                            if (profileErrors.email) {
                                                setProfileErrors({ ...profileErrors, email: undefined });
                                            }
                                        }}
                                        disabled={profileLoading}
                                        className={profileErrors.email ? 'border-destructive' : ''}
                                    />
                                    {profileErrors.email && (
                                        <p className="text-sm text-destructive flex items-center gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {profileErrors.email}
                                        </p>
                                    )}
                                </div>
                                <Button onClick={handleProfileUpdate} disabled={profileLoading}>
                                    {profileLoading ? 'Saving...' : 'Save Changes'}
                                </Button>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="security" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Change Password</CardTitle>
                                <CardDescription>Update your password to keep your account secure</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="current-password">Current Password</Label>
                                    <div className="relative">
                                        <Input
                                            id="current-password"
                                            type={showCurrentPassword ? 'text' : 'password'}
                                            value={currentPassword}
                                            onChange={(e) => {
                                                setCurrentPassword(e.target.value);
                                                if (passwordErrors.current_password) {
                                                    setPasswordErrors({
                                                        ...passwordErrors,
                                                        current_password: undefined,
                                                    });
                                                }
                                            }}
                                            disabled={passwordLoading}
                                            className={
                                                passwordErrors.current_password ? 'border-destructive pr-10' : 'pr-10'
                                            }
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                            disabled={passwordLoading}
                                        >
                                            {showCurrentPassword ? (
                                                <EyeOff className="h-4 w-4" />
                                            ) : (
                                                <Eye className="h-4 w-4" />
                                            )}
                                        </button>
                                    </div>
                                    {passwordErrors.current_password && (
                                        <p className="text-sm text-destructive flex items-center gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {passwordErrors.current_password}
                                        </p>
                                    )}
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="new-password">New Password</Label>
                                    <div className="relative">
                                        <Input
                                            id="new-password"
                                            type={showNewPassword ? 'text' : 'password'}
                                            value={newPassword}
                                            onChange={(e) => {
                                                setNewPassword(e.target.value);
                                                if (passwordErrors.new_password) {
                                                    setPasswordErrors({
                                                        ...passwordErrors,
                                                        new_password: undefined,
                                                    });
                                                }
                                            }}
                                            disabled={passwordLoading}
                                            className={passwordErrors.new_password ? 'border-destructive pr-10' : 'pr-10'}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowNewPassword(!showNewPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                            disabled={passwordLoading}
                                        >
                                            {showNewPassword ? (
                                                <EyeOff className="h-4 w-4" />
                                            ) : (
                                                <Eye className="h-4 w-4" />
                                            )}
                                        </button>
                                    </div>
                                    {passwordErrors.new_password && (
                                        <p className="text-sm text-destructive flex items-center gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {passwordErrors.new_password}
                                        </p>
                                    )}
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="confirm-password">Confirm New Password</Label>
                                    <div className="relative">
                                        <Input
                                            id="confirm-password"
                                            type={showConfirmPassword ? 'text' : 'password'}
                                            value={confirmPassword}
                                            onChange={(e) => {
                                                setConfirmPassword(e.target.value);
                                                if (passwordErrors.confirm_password) {
                                                    setPasswordErrors({
                                                        ...passwordErrors,
                                                        confirm_password: undefined,
                                                    });
                                                }
                                            }}
                                            disabled={passwordLoading}
                                            className={
                                                passwordErrors.confirm_password ? 'border-destructive pr-10' : 'pr-10'
                                            }
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                            disabled={passwordLoading}
                                        >
                                            {showConfirmPassword ? (
                                                <EyeOff className="h-4 w-4" />
                                            ) : (
                                                <Eye className="h-4 w-4" />
                                            )}
                                        </button>
                                    </div>
                                    {passwordErrors.confirm_password && (
                                        <p className="text-sm text-destructive flex items-center gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {passwordErrors.confirm_password}
                                        </p>
                                    )}
                                </div>
                                <Button onClick={handlePasswordChange} disabled={passwordLoading}>
                                    {passwordLoading ? 'Changing Password...' : 'Change Password'}
                                </Button>
                            </CardContent>
                        </Card>

                        <Card className="border-destructive">
                            <CardHeader>
                                <CardTitle className="text-destructive">Danger Zone</CardTitle>
                                <CardDescription>Permanently delete your account</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <p className="text-sm text-muted-foreground">
                                    Once you delete your account, there is no going back. Please be certain.
                                </p>
                                <Button
                                    variant="destructive"
                                    onClick={() => setShowDeleteDialog(true)}
                                    disabled={deleteLoading}
                                >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete Account
                                </Button>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>

                <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This action cannot be undone. This will permanently delete your account and remove all
                                your data from our servers.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <div className="space-y-2 py-4">
                            <Label htmlFor="delete-password">Enter your password to confirm</Label>
                            <div className="relative">
                                <Input
                                    id="delete-password"
                                    type={showDeletePassword ? 'text' : 'password'}
                                    value={deletePassword}
                                    onChange={(e) => setDeletePassword(e.target.value)}
                                    disabled={deleteLoading}
                                    placeholder="Enter your password"
                                    className="pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowDeletePassword(!showDeletePassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                    disabled={deleteLoading}
                                >
                                    {showDeletePassword ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </button>
                            </div>
                        </div>
                        <AlertDialogFooter>
                            <AlertDialogCancel disabled={deleteLoading}>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={handleDeleteAccount}
                                disabled={deleteLoading || !deletePassword}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                                {deleteLoading ? 'Deleting...' : 'Delete Account'}
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            </div>
        </div>
    );
}
