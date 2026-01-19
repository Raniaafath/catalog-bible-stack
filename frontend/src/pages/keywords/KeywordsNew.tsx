import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, Search, Loader2, Plus, X } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { getLocales, getProductTypes, createPlannerRun } from '@/lib/api';

export default function KeywordsNew() {
  const navigate = useNavigate();
  const [locale, setLocale] = useState('');
  const [productType, setProductType] = useState('');
  const [seedTerms, setSeedTerms] = useState<string[]>([]);
  const [negativeTerms, setNegativeTerms] = useState<string[]>([]);
  const [seedInput, setSeedInput] = useState('');
  const [negativeInput, setNegativeInput] = useState('');

  const { data: locales } = useQuery({
    queryKey: ['locales'],
    queryFn: getLocales,
  });

  const { data: productTypes } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
  });

  const createMutation = useMutation({
    mutationFn: createPlannerRun,
    onSuccess: (data) => {
      navigate(`/keywords/${data.id}`);
    },
  });

  const addSeedTerm = () => {
    if (seedInput.trim() && !seedTerms.includes(seedInput.trim())) {
      setSeedTerms([...seedTerms, seedInput.trim()]);
      setSeedInput('');
    }
  };

  const addNegativeTerm = () => {
    if (negativeInput.trim() && !negativeTerms.includes(negativeInput.trim())) {
      setNegativeTerms([...negativeTerms, negativeInput.trim()]);
      setNegativeInput('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (locale && productType && seedTerms.length > 0) {
      createMutation.mutate({
        locale,
        product_type: productType,
        seed_terms: seedTerms,
        negative_terms: negativeTerms,
      });
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Keyword Run"
        description="Configure and start a keyword planner run"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Keywords', href: '/keywords' },
          { label: 'New Run' },
        ]}
      />

      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="w-5 h-5" />
              Planner Configuration
            </CardTitle>
            <CardDescription>
              Set up the parameters for keyword research.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="locale">Locale</Label>
                  <Select value={locale} onValueChange={setLocale}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select locale..." />
                    </SelectTrigger>
                    <SelectContent>
                      {locales?.results?.map((loc) => (
                        <SelectItem key={loc.code} value={loc.code}>
                          {loc.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="productType">Product Type</Label>
                  <Select value={productType} onValueChange={setProductType}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select type..." />
                    </SelectTrigger>
                    <SelectContent>
                      {productTypes?.results?.map((type) => (
                        <SelectItem key={type.id} value={type.slug}>
                          {type.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Seed Terms</Label>
                <div className="flex gap-2">
                  <Input
                    value={seedInput}
                    onChange={(e) => setSeedInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSeedTerm())}
                    placeholder="Enter a seed keyword..."
                  />
                  <Button type="button" variant="outline" onClick={addSeedTerm}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                {seedTerms.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {seedTerms.map((term) => (
                      <Badge key={term} variant="secondary" className="gap-1">
                        {term}
                        <X
                          className="w-3 h-3 cursor-pointer"
                          onClick={() => setSeedTerms(seedTerms.filter((t) => t !== term))}
                        />
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label>Negative Terms (optional)</Label>
                <div className="flex gap-2">
                  <Input
                    value={negativeInput}
                    onChange={(e) => setNegativeInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addNegativeTerm())}
                    placeholder="Enter terms to exclude..."
                  />
                  <Button type="button" variant="outline" onClick={addNegativeTerm}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                {negativeTerms.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {negativeTerms.map((term) => (
                      <Badge key={term} variant="outline" className="gap-1 text-status-error border-status-error/50">
                        {term}
                        <X
                          className="w-3 h-3 cursor-pointer"
                          onClick={() => setNegativeTerms(negativeTerms.filter((t) => t !== term))}
                        />
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/keywords')}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!locale || !productType || seedTerms.length === 0 || createMutation.isPending}
                >
                  {createMutation.isPending && (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  )}
                  Start Run
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
