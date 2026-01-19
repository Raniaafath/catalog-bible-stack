import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface Breadcrumb {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: Breadcrumb[];
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn('page-header', className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-sm text-muted-foreground mb-3">
          {breadcrumbs.map((crumb, index) => (
            <span key={index} className="flex items-center gap-1">
              {crumb.href ? (
                <Link
                  to={crumb.href}
                  className="hover:text-foreground transition-colors"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-foreground font-medium">{crumb.label}</span>
              )}
              {index < breadcrumbs.length - 1 && (
                <ChevronRight className="w-4 h-4" />
              )}
            </span>
          ))}
        </nav>
      )}
      
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{title}</h1>
          {description && (
            <p className="page-description">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
