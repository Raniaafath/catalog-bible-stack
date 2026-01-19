import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

export interface StatCardProps {
  title: string;
  value: number | string;
  icon?: LucideIcon;
  description?: string;
  trend?: {
    value: number;
    label: string;
    positive?: boolean;
  };
  className?: string;
  onClick?: () => void;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  className,
  onClick,
}: StatCardProps) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'stat-card',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="stat-value mt-1">{value}</p>
          {description && (
            <p className="stat-label">{description}</p>
          )}
          {trend && (
            <div className="flex items-center gap-1 mt-2">
              <span
                className={cn(
                  'text-xs font-medium',
                  trend.positive ? 'text-status-success' : 'text-status-error'
                )}
              >
                {trend.positive ? '+' : ''}{trend.value}%
              </span>
              <span className="text-xs text-muted-foreground">{trend.label}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="p-2.5 rounded-lg bg-primary/10">
            <Icon className="w-5 h-5 text-primary" />
          </div>
        )}
      </div>
    </motion.div>
  );
}
