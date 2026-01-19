import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Globe, Loader2, CheckCircle2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { getTranslationTask } from '@/lib/api';

export default function TranslationDetail() {
  const { id } = useParams<{ id: string }>();
  const taskId = Number(id);

  const { data: task, isLoading } = useQuery({
    queryKey: ['translation-task', taskId],
    queryFn: () => getTranslationTask(taskId),
    enabled: !!taskId,
    refetchInterval: (data) => 
      data?.state.data?.status === 'in_progress' ? 5000 : false,
  });

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const progress = task?.product_count 
    ? Math.round((task.translated_count / task.product_count) * 100) 
    : 0;

  return (
    <div className="page-container">
      <PageHeader
        title={`Translation: ${task?.locale.toUpperCase() || 'Task'}`}
        description="Translation task progress and details"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Translations', href: '/translations' },
          { label: task?.locale.toUpperCase() || `Task #${id}` },
        ]}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <div className="mt-1">
                  <StatusBadge status={task?.status || 'pending'} size="lg" />
                </div>
              </div>
              <Globe className="w-8 h-8 text-primary opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Products</p>
            <p className="text-2xl font-bold font-display">
              {task?.product_count.toLocaleString() ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Translated</p>
            <p className="text-2xl font-bold font-display">
              {task?.translated_count.toLocaleString() ?? 0}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Translation Progress</span>
              <span className="font-medium">{progress}%</span>
            </div>
            <Progress value={progress} className="h-3" />
            
            {task?.status === 'completed' && (
              <div className="flex items-center gap-2 text-status-success mt-4">
                <CheckCircle2 className="w-5 h-5" />
                <span className="font-medium">Translation complete</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
