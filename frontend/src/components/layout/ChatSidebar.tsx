import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { LogOut, Plus, MoreVertical, Trash2, PanelLeftClose, Menu } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { memo, useCallback, useState, useEffect } from "react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useSession } from "@/contexts/SessionContext";
import { APP_ROUTES } from "@/lib/constants";

interface ChatSidebarProps {
    currentSessionId?: number;
    onSessionClick?: (sessionId: number) => void;
}

const SIDEBAR_STORAGE_KEY = 'chat-sidebar-collapsed';

export const ChatSidebar = memo(function ChatSidebar({ currentSessionId, onSessionClick }: ChatSidebarProps) {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { sessions, loading: sessionsLoading, deleteSession } = useSession();
    const [sessionToDelete, setSessionToDelete] = useState<number | null>(null);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [isCollapsed, setIsCollapsed] = useState(() => {
        const stored = localStorage.getItem(SIDEBAR_STORAGE_KEY);
        return stored === 'true';
    });
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    useEffect(() => {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed));
    }, [isCollapsed]);

    const toggleSidebar = useCallback(() => {
        setIsCollapsed(prev => !prev);
    }, []);

    const handleSidebarClick = useCallback(() => {
        if (isCollapsed) {
            setIsCollapsed(false);
        }
    }, [isCollapsed]);

    const handleSessionClick = useCallback((sessionId: number) => {
        if (onSessionClick) {
            onSessionClick(sessionId);
        }
        setMobileMenuOpen(false);
    }, [onSessionClick]);

    const handleDeleteClick = useCallback((e: React.MouseEvent, sessionId: number) => {
        e.stopPropagation();
        setSessionToDelete(sessionId);
        setShowDeleteDialog(true);
    }, []);

    const handleConfirmDelete = useCallback(async () => {
        if (sessionToDelete === null) return;

        try {
            await deleteSession(sessionToDelete);
            toast.success('Session deleted');
            if (currentSessionId === sessionToDelete) {
                navigate(APP_ROUTES.HOME);
            }
        } catch (error) {
            toast.error('Failed to delete session');
        } finally {
            setShowDeleteDialog(false);
            setSessionToDelete(null);
        }
    }, [deleteSession, currentSessionId, navigate, sessionToDelete]);

    const SidebarContent = () => (
        <div className="flex flex-col h-full space-y-3 p-2">
            <div className="flex flex-col space-y-3 py-2 border-b border-border">
                <div className="flex justify-between items-center gap-2">
                    <Link
                        to={APP_ROUTES.HOME}
                        className="flex items-center gap-2 border px-2.5 py-0.5 rounded-md bg-black text-white"
                        title={isCollapsed ? "Home" : undefined}
                        onClick={() => setMobileMenuOpen(false)}
                    >
                        <span className="text-lg font-bold">N</span>
                    </Link>
                    {!isCollapsed && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={toggleSidebar}
                            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                            className="hidden lg:flex"
                        >
                            <PanelLeftClose className="size-6" />
                        </Button>
                    )}
                </div>
                {isCollapsed ? (
                    <Button variant="outline" className="w-full" asChild>
                        <Link to={APP_ROUTES.HOME} className="flex items-center" onClick={() => setMobileMenuOpen(false)}>
                            <Plus className="size-4" />
                        </Link>
                    </Button>
                ) : (
                    <Button variant="outline" className="w-full" asChild>
                        <Link to={APP_ROUTES.HOME} onClick={() => setMobileMenuOpen(false)}>
                            <Plus className="size-4" />
                            New Chat
                        </Link>
                    </Button>
                )}
            </div>
            <div className="flex-1 overflow-hidden min-h-0">
                {!isCollapsed && (
                    <ScrollArea className="h-full">
                        <div className="space-y-1">
                            {sessionsLoading ? (
                                <div className="text-center text-sm text-muted-foreground">
                                    Loading sessions...
                                </div>
                            ) : sessions.length === 0 ? (
                                <div className="text-center text-sm text-muted-foreground">
                                    No chats found
                                </div>
                            ) : (
                                sessions.map((session) => (
                                    <div
                                        key={session.id}
                                        onClick={() => handleSessionClick(session.id)}
                                        className={`group flex items-center gap-2 p-2 rounded-full cursor-pointer transition-colors ${currentSessionId === session.id ? 'bg-accent' : 'hover:bg-accent/50'
                                            }`}
                                        title={isCollapsed ? session.title : undefined}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium truncate">
                                                {
                                                    session.title.length > 25 ? session.title.substring(0, 25) + '...' : session.title
                                                }
                                            </div>
                                        </div>
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    <MoreVertical className="size-3" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                                                <DropdownMenuItem
                                                    className="text-destructive focus:text-destructive"
                                                    onClick={(e) => handleDeleteClick(e, session.id)}
                                                >
                                                    <Trash2 className="size-4 text-destructive" />
                                                    Delete
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                ))
                            )}
                        </div>
                    </ScrollArea>
                )}
            </div>

            <div className="py-2 border-t border-border">
                {!isCollapsed ? (
                    <>
                        <div className="flex items-center gap-2 mb-2">
                            <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <span className="text-sm font-medium">
                                    {user?.name?.charAt(0).toUpperCase()}
                                </span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium truncate">{user?.name}</div>
                                <div className="text-xs text-muted-foreground truncate">
                                    {user?.email}
                                </div>
                            </div>
                        </div>
                        <Button variant="outline" className="w-full" onClick={() => { logout(); setMobileMenuOpen(false); }}>
                            <LogOut className="size-4 rotate-180" />
                            Logout
                        </Button>
                    </>
                ) : (
                    <div className="flex flex-col items-center gap-2">
                        <div
                            className="size-8 rounded-full bg-primary/10 flex items-center justify-center cursor-pointer"
                            title={user?.email || undefined}
                        >
                            <span className="text-sm font-medium">
                                {user?.name?.charAt(0).toUpperCase()}
                            </span>
                        </div>
                        <Button
                            variant="outline"
                            size="icon"
                            onClick={() => { logout(); setMobileMenuOpen(false); }}
                            title="Logout"
                        >
                            <LogOut className="size-4 rotate-180" />
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <>
            {/* Mobile Menu Button */}
            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger asChild>
                    <Button
                        variant="outline"
                        size="icon"
                        className="lg:hidden fixed top-4 left-4 z-50 bg-background shadow-lg"
                    >
                        <Menu className="size-4" />
                    </Button>
                </SheetTrigger>
                <SheetContent side="left" className="p-0 w-64">
                    <div className="flex flex-col h-full">
                        <SidebarContent />
                    </div>
                </SheetContent>
            </Sheet>

            {/* Desktop Sidebar */}
            <div
                className={`hidden lg:flex border-r border-border bg-card flex-col h-full shrink-0 transition-all duration-300 ease-in-out ${isCollapsed ? 'w-16' : 'w-64'
                    }`}
                onClick={handleSidebarClick}
            >
                <SidebarContent />
            </div>

            <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Session</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete this session? This action cannot be undone and all messages in this session will be permanently deleted.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleConfirmDelete}
                            className="bg-destructive hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
});