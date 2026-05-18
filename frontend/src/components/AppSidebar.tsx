import { LayoutGrid, Package, TrendingUp, BookOpen, Truck, DollarSign, Megaphone, Bell } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";

const navItems = [
  { title: "Dashboard", url: "/", icon: LayoutGrid },
  { title: "Inventory", url: "/inventory", icon: Package },
  { title: "Forecasting", url: "/forecasting", icon: TrendingUp },
  { title: "Menu & Recipes", url: "/menu", icon: BookOpen },
  { title: "Suppliers", url: "/suppliers", icon: Truck },
  { title: "Financials", url: "/financials", icon: DollarSign },
  { title: "Marketing", url: "/marketing", icon: Megaphone },
  { title: "Alerts", url: "/alerts", icon: Bell },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  return (
    <Sidebar collapsible="icon" className="border-r-0">
      <div className="px-5 pt-6 pb-4">
        {!collapsed ? (
          <>
            <h1 className="text-2xl font-logo font-bold text-sidebar-accent-foreground tracking-tight">Pantry</h1>
            <p className="text-[10px] tracking-[0.2em] uppercase text-sidebar-muted mt-0.5">Restaurant Intelligence</p>
          </>
        ) : (
          <h1 className="text-xl font-logo font-bold text-sidebar-accent-foreground text-center">P</h1>
        )}
      </div>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive = item.url === "/" ? location.pathname === "/" : location.pathname.startsWith(item.url);
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <NavLink to={item.url} end={item.url === "/"} className="relative flex items-center gap-3 px-3 py-2 rounded-md text-sidebar-foreground hover:bg-sidebar-accent transition-colors" activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium">
                        <item.icon className="h-4 w-4 shrink-0" />
                        {!collapsed && <span className="text-sm">{item.title}</span>}
                        {item.title === "Alerts" && !collapsed && (
                          <span className="ml-auto bg-destructive text-destructive-foreground text-[10px] font-semibold rounded-full px-1.5 py-0.5 leading-none">4</span>
                        )}
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      {!collapsed && (
        <SidebarFooter className="px-5 pb-5">
          <div className="border-t border-sidebar-border pt-4">
            <p className="text-xs font-medium text-sidebar-accent-foreground">Perilla Korean Steakhouse</p>
            <p className="text-[11px] text-sidebar-muted">Chef Andrew Lim</p>
          </div>
        </SidebarFooter>
      )}
    </Sidebar>
  );
}
