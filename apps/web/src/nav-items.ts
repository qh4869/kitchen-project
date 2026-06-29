export type NavItem = {
  to: string;
  label: string;
  end: boolean;
};

export const navItems: NavItem[] = [
  { to: "/", label: "首页", end: true },
  { to: "/entry", label: "记账", end: false },
  { to: "/suppliers", label: "供应商", end: false },
];
