import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, Download, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getExportProfiles, createExport } from '@/lib/api';

export default function ExportsNew() {
  const navigate = useNavigate();
  const [profileId, setProfileId] = useState('');

  const { data: profiles, isLoading: profilesLoading } = useQuery({
    queryKey: ['export-profiles'],
    queryFn: getExportProfiles,
  });

  const createMutation = useMutation({
    mutationFn: createExport,
    onSuccess: () => {
      navigate('/exports');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (profileId) {
      createMutation.mutate({ profile_id: Number(profileId) });
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Export"
        description="Create a new export job"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Exports', href: '/exports' },
          { label: 'New Export' },
        ]}
      />

      <div className="max-w-xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="w-5 h-5" />
              Export Settings
            </CardTitle>
            <CardDescription>
              Select an export profile to create a new export job.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="profile">Export Profile</Label>
                <Select value={profileId} onValueChange={setProfileId} disabled={profilesLoading}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select profile..." />
                  </SelectTrigger>
                  <SelectContent>
                    {profiles?.results?.map((profile) => (
                      <SelectItem key={profile.id} value={profile.id.toString()}>
                        {profile.name} ({profile.channel} • {profile.format})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/exports')}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={!profileId || createMutation.isPending}>
                  {createMutation.isPending && (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  )}
                  Create Export
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
