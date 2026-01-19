import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, Languages, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getLocales, createTranslationTask } from '@/lib/api';

export default function TranslationNew() {
  const navigate = useNavigate();
  const [locale, setLocale] = useState('');

  const { data: locales, isLoading: localesLoading } = useQuery({
    queryKey: ['locales'],
    queryFn: getLocales,
  });

  const createMutation = useMutation({
    mutationFn: createTranslationTask,
    onSuccess: (data) => {
      navigate(`/translations/${data.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (locale) {
      createMutation.mutate({ locale });
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Translation Task"
        description="Create a translation task for a specific locale"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Translations', href: '/translations' },
          { label: 'New Task' },
        ]}
      />

      <div className="max-w-xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Languages className="w-5 h-5" />
              Translation Settings
            </CardTitle>
            <CardDescription>
              Select the target locale for translation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="locale">Target Locale</Label>
                <Select value={locale} onValueChange={setLocale} disabled={localesLoading}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select locale..." />
                  </SelectTrigger>
                  <SelectContent>
                    {locales?.results?.map((loc) => (
                      <SelectItem key={loc.code} value={loc.code}>
                        {loc.name} ({loc.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/translations')}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={!locale || createMutation.isPending}>
                  {createMutation.isPending && (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  )}
                  Create Task
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
