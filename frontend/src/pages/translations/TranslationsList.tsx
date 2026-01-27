import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, RefreshCw, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/DataTable';
import { Progress } from '@/components/ui/progress';
import { getTranslationTasks } from '@/lib/api';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const statusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="w-3 h-3 mr-1" />,
  in_progress: <Loader2 className="w-3 h-3 mr-1 animate-spin" />,
  done: <CheckCircle className="w-3 h-3 mr-1" />,
  failed: <AlertCircle className="w-3 h-3 mr-1" />,
};

const scopeLabels: Record<string, string> = {
  product_attribute_value: 'Product Attributes',
  attribute: 'Attribute Names',
  attribute_value: 'Attribute Values',
  product_type: 'Product Types',
};

const scopeDescriptions: Record<string, string> = {
  product_attribute_value: 'Translates product attribute values (color names, sizes, materials, etc.)',
  attribute: 'Translates attribute names/labels',
  attribute_value: 'Translates enum attribute value options',
  product_type: 'Translates product type names and categories',
};

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export default function TranslationsList() {
  const navigate = useNavigate();

  const { data: tasks, isLoading, refetch } = useQuery({
    queryKey: ['translation-tasks'],
    queryFn: () => getTranslationTasks(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const modelBadgeColors: Record<string, string> = {
    'gpt-4o-mini': 'bg-green-100 text-green-800',
    'gpt-4o': 'bg-blue-100 text-blue-800',
    'gpt-4-turbo': 'bg-purple-100 text-purple-800',
  };

  const columns = [
    {
      key: 'id',
      header: 'ID',
      render: (task: any) => (
        <span className="font-mono font-medium">#{task.id}</span>
      ),
    },
    {
      key: 'scope',
      header: 'Scope',
      render: (task: any) => (
        <div>
          <div className="font-medium">{scopeLabels[task.scope] || task.scope}</div>
          <div className="text-xs text-muted-foreground truncate max-w-[200px]" title={scopeDescriptions[task.scope]}>
            {scopeDescriptions[task.scope]}
          </div>
        </div>
      ),
    },
    {
      key: 'locale',
      header: 'Language',
      render: (task: any) => (
        <span className="font-mono text-sm bg-gray-100 px-2 py-0.5 rounded">{task.locale}</span>
      ),
    },
    {
      key: 'progress',
      header: 'Progress',
      render: (task: any) => {
        const percent = task.progress_percent ?? 0;
        const itemsTotal = task.items_total ?? 0;
        const itemsCompleted = task.items_completed ?? 0;
        
        return (
          <div className="min-w-[120px]">
            <div className="flex items-center justify-between text-xs mb-1">
              <span>{itemsCompleted} / {itemsTotal || '?'}</span>
              <span className="font-medium">{percent}%</span>
            </div>
            <Progress value={percent} className="h-2" />
          </div>
        );
      },
    },
    {
      key: 'model',
      header: 'Model',
      render: (task: any) => (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
            modelBadgeColors[task.model] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {task.model || 'gpt-4o-mini'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (task: any) => (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            statusColors[task.status] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {statusIcons[task.status]}
          {task.status.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'duration',
      header: 'Duration',
      render: (task: any) => (
        <span className="text-sm text-muted-foreground">
          {formatDuration(task.duration_seconds)}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (task: any) => (
        <div className="text-sm">
          <div>{new Date(task.created_at).toLocaleDateString()}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(task.created_at).toLocaleTimeString()}
          </div>
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (task: any) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/translations/${task.id}`)}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title="Translation Tasks"
        description="Manage AI-powered translations for attributes, values, and product types."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Translations' },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => navigate('/translations/new')}>
              <Plus className="w-4 h-4 mr-2" />
              New Translation
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={tasks?.results || []}
        keyExtractor={(task) => task.id.toString()}
        isLoading={isLoading}
        emptyTitle="No translation tasks found"
        emptyDescription="Create your first translation to get started."
      />
    </div>
  );
}
