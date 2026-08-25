import { useCallback } from "react";
import {
  Link as RouterLink,
  NavLink as RouterNavLink,
  useNavigate as useRouterNavigate,
  type LinkProps,
  type NavLinkProps,
  type NavigateFunction,
  type NavigateOptions,
  type To,
} from "react-router-dom";
import { canViewTransition } from "./motion";

export function Link({ viewTransition, ...props }: LinkProps) {
  return <RouterLink viewTransition={viewTransition ?? canViewTransition()} {...props} />;
}

export function NavLink({ viewTransition, ...props }: NavLinkProps) {
  return <RouterNavLink viewTransition={viewTransition ?? canViewTransition()} {...props} />;
}

export function useNavigate(): NavigateFunction {
  const navigate = useRouterNavigate();
  return useCallback(
    ((to: To | number, options?: NavigateOptions) => {
      if (typeof to === "number") {
        navigate(to);
        return;
      }
      navigate(to, {
        ...options,
        viewTransition: options?.viewTransition ?? canViewTransition(),
      });
    }) as NavigateFunction,
    [navigate],
  );
}
