import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Package,
  Upload,
  Languages,
  Search,
  Sparkles,
  Download,
  ArrowRight,
  Clock,
  LayoutTemplate,
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/PageHeader';
import { StatCard } from '@/components/StatCard';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  getImports,
  getProducts,
  getTemplates,
  getTranslationTasks,
  getPlannerRuns,
  getGenerationBatches,
  getExportJobs,
  Import,
  TranslationTask,
  PlannerRun,
  GenerationBatch,
  ExportJob,
} from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

type ActivityItem = {
  id: string;
  type: 'import' | 'translation' | 'keyword' | 'generation' | 'export';
  title: string;
  status: string;
  time: string;
};

export default function Dashboard() {
  const navigate = useNavigate();

  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts({ page: 1, page_size: 1 }),
  });

  const { data: importsData, isLoading: importsLoading } = useQuery({
    queryKey: ['imports'],
    queryFn: () => getImports({ page: 1, page_size: 5 }),
  });

  const { data: translationsData, isLoading: translationsLoading } = useQuery({
    queryKey: ['translation-tasks'],
    queryFn: () => getTranslationTasks({ page: 1, page_size: 5 }),
  });

  const { data: keywordsData, isLoading: keywordsLoading } = useQuery({
    queryKey: ['planner-runs'],
    queryFn: () => getPlannerRuns({ page: 1, page_size: 5 }),
  });

  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['generation-batches'],
    queryFn: () => getGenerationBatches({ page: 1, page_size: 5 }),
  });

  const { data: exportsData, isLoading: exportsLoading } = useQuery({
    queryKey: ['export-jobs'],
    queryFn: () => getExportJobs({ page: 1, page_size: 5 }),
  });

  const { data: templatesData } = useQuery({
    queryKey: ['templates-count'],
    queryFn: () => getTemplates({ page: 1, page_size: 1 }),
  });

  // Combine recent activity
  const recentActivity: ActivityItem[] = [
    ...(importsData?.results || []).map((i: Import) => ({
      id: `import-${i.id}`,
      type: 'import' as const,
      title: i.original_filename,
      status: i.status,
      time: i.created_at,
    })),
    ...(translationsData?.results || []).map((t: TranslationTask) => ({
      id: `translation-${t.id}`,
      type: 'translation' as const,
      title: `Translation task (${t.locale})`,
      status: t.status,
      time: t.created_at,
    })),
    ...(keywordsData?.results || []).map((k: PlannerRun) => ({
      id: `keyword-${k.id}`,
      type: 'keyword' as const,
      title: `Keyword run (${k.product_type_code ?? k.locale_code})`,
      status: k.status,
      time: k.created_at,
    })),
    ...(batchesData?.results || []).map((b: GenerationBatch) => ({
      id: `generation-${b.id}`,
      type: 'generation' as const,
      title: b.name,
      status: b.status,
      time: b.created_at,
    })),
    ...(exportsData?.results || []).map((e: ExportJob) => ({
      id: `export-${e.id}`,
      type: 'export' as const,
      title: e.profile,
      status: e.status,
      time: e.created_at,
    })),
  ]
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .slice(0, 10);

  const activityIcons = {
    import: Upload,
    translation: Languages,
    keyword: Search,
    generation: Sparkles,
    export: Download,
  };

  const isLoading =
    productsLoading ||
    importsLoading ||
    translationsLoading ||
    keywordsLoading ||
    batchesLoading ||
    exportsLoading;

  const quickActions = [
    { label: 'New Import', href: '/imports/new', icon: Upload },
    { label: 'Title Templates', href: '/templates', icon: LayoutTemplate },
    { label: 'Keyword Run', href: '/keywords/new', icon: Search },
    { label: 'New Export', href: '/exports/new', icon: Download },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title="Dashboard"
        description="Product pipeline overview and quick actions"
      />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8 stagger-fade-in">
        {productsLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="stat-card">
              <div className="flex items-start justify-between">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-7 w-12" />
                </div>
                <Skeleton className="h-10 w-10 rounded-lg" />
              </div>
            </div>
          ))
        ) : (
          <>
            <StatCard
              title="Products"
              value={productsData?.count ?? 0}
              icon={Package}
              onClick={() => navigate('/products')}
            />
            <StatCard
              title="Imports"
              value={importsData?.count ?? 0}
              icon={Upload}
              onClick={() => navigate('/imports')}
            />
            <StatCard
              title="Translations"
              value={translationsData?.count ?? 0}
              icon={Languages}
              onClick={() => navigate('/translations')}
            />
            <StatCard
              title="Keyword Runs"
              value={keywordsData?.count ?? 0}
              icon={Search}
              onClick={() => navigate('/keywords')}
            />
            <StatCard
              title="Exports"
              value={exportsData?.count ?? 0}
              icon={Download}
              onClick={() => navigate('/exports')}
            />
            <StatCard
              title="Title Templates"
              value={templatesData?.count ?? 0}
              icon={LayoutTemplate}
              onClick={() => navigate('/templates')}
            />
          </>
        )}
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold font-display mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quickActions.map((action) => (
            <Link key={action.href} to={action.href}>
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex items-center gap-3 p-4 rounded-lg border border-border bg-card hover:border-primary/40 hover:bg-primary/5 transition-colors"
              >
                <div className="p-2 rounded-lg bg-primary/10">
                  <action.icon className="w-5 h-5 text-primary" />
                </div>
                <span className="font-medium text-sm">{action.label}</span>
              </motion.div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display">Recent Activity</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/imports">
              View all <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between py-3 px-4 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-9 w-9 rounded-lg" />
                    <div className="space-y-1.5">
                      <Skeleton className="h-3.5 w-40" />
                      <Skeleton className="h-3 w-24" />
                    </div>
                  </div>
                  <Skeleton className="h-6 w-20 rounded-full" />
                </div>
              ))}
            </div>
          ) : recentActivity.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p>No recent activity</p>
              <p className="text-sm mt-1">Start by creating a new import</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentActivity.map((item, index) => {
                const Icon = activityIcons[item.type];
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-muted">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium text-sm">{item.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(item.time), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={item.status as any} size="sm" />
                  </motion.div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
