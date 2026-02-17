import { useState } from 'react';
import { Settings as SettingsIcon } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import MarketplacesTab from './MarketplacesTab';
import TitleRulesTab from './TitleRulesTab';
import LocalesTab from './LocalesTab';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('marketplaces');

  return (
    <div className="page-container">
      <PageHeader
        title="Settings"
        description="Manage marketplaces, title rules, and locales."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Settings' },
        ]}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="marketplaces">
            <SettingsIcon className="w-4 h-4 mr-2" />
            Marketplaces
          </TabsTrigger>
          <TabsTrigger value="title-rules">Title Rules</TabsTrigger>
          <TabsTrigger value="locales">Locales</TabsTrigger>
        </TabsList>

        <TabsContent value="marketplaces">
          <MarketplacesTab />
        </TabsContent>

        <TabsContent value="title-rules">
          <TitleRulesTab />
        </TabsContent>

        <TabsContent value="locales">
          <LocalesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
